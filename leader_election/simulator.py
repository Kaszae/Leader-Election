"""Der Simulator: virtuelle Uhr, Ereignis-Warteschlange und Messwerte.

Statt echter Zeit und Threads gibt es eine virtuelle Uhr. Jede Nachricht und
jeder Timer ist ein Ereignis mit Zeitstempel in einer Warteschlange. Der
Simulator nimmt immer das früheste Ereignis heraus, stellt die Uhr auf dessen
Zeit und führt es aus. Dadurch:
  - ist jeder Lauf mit demselben Seed exakt gleich,
  - lässt sich alles Schritt für Schritt abspielen,
  - laufen viele Wahlen (Benchmark) in Sekunden durch.
"""

from __future__ import annotations

import heapq
import itertools
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Callable

from .algorithms import ALGORITHMS
from .message import Message
from .network import Network
from .node import FOLLOWER, LEADER, Node

# Nachrichtentypen, die nur im Hintergrund laufen (zählen nicht zu Wahlen)
BACKGROUND_KINDS = {"HEARTBEAT"}


@dataclass(order=True)
class Event:
    time: int
    seq: int
    kind: str = field(compare=False)  # "msg" oder "timer"
    node_id: int = field(compare=False)  # Empfänger bzw. Besitzer des Timers
    msg: Message | None = field(default=None, compare=False)
    timer: str | None = field(default=None, compare=False)
    timer_data: dict[str, Any] = field(default_factory=dict, compare=False)
    background: bool = field(default=False, compare=False)
    cancelled: bool = field(default=False, compare=False)

    def describe(self) -> str:
        if self.msg is not None:
            return str(self.msg)
        return f"Timer '{self.timer}' von Knoten {self.node_id}"


@dataclass
class Election:
    """Eine Wahl, von ihrem Start bis alle sich einig sind."""

    start: int
    initiator: int
    messages_at_start: int
    leader_lost_at: int | None = None
    agreed_at: int | None = None
    duration: int | None = None
    messages: int | None = None
    leaders: list[int] = field(default_factory=list)


@dataclass
class Stats:
    messages: Counter = field(default_factory=Counter)  # nach Typ, ohne Heartbeats
    heartbeats: int = 0
    dropped: int = 0
    max_leaders: int = 0
    elections: list[Election] = field(default_factory=list)

    @property
    def total_messages(self) -> int:
        return sum(self.messages.values())


class Simulator:
    def __init__(
        self,
        algorithm: str = "bully",
        n: int = 5,
        seed: int = 0,
        output: Callable[[str], None] | None = print,
        base_delay: int = 100,
        jitter: int = 10,
        timeout: int | None = None,
    ):
        if algorithm not in ALGORITHMS:
            raise ValueError(f"Unbekannter Algorithmus '{algorithm}'. Möglich: {', '.join(ALGORITHMS)}")
        if n < 1:
            raise ValueError("Es braucht mindestens einen Knoten.")
        self.algorithm = algorithm
        self.seed = seed
        self.rng = random.Random(seed)
        self.network = Network(self.rng, base_delay, jitter)
        self.output = output
        self.hidden_kinds = {"HEARTBEAT", "ACK"}  # im Log ausgeblendet, aber gezählt

        # Ausfallerkennung über Heartbeats (aus = Wahlen nur per Befehl)
        self.detect = False
        self.hb_interval = 500
        self.hb_timeout = 1500

        self.time = 0
        self._queue: list[Event] = []
        self._seq = itertools.count()
        self._msg_ids = itertools.count(1)
        self._timers: dict[tuple[int, str], Event] = {}

        self.stats = Stats()
        self.election: Election | None = None  # laufende Wahl
        self._leader_lost_at: int | None = None

        ids = list(range(1, n + 1))
        node_cls = ALGORITHMS[algorithm]
        self.nodes: dict[int, Node] = {i: node_cls(i, ids, self) for i in ids}
        if timeout is not None:
            self.set_timeout(timeout)

    # ======================================================================
    # Logausgabe
    # ======================================================================

    def log(self, text: str) -> None:
        if self.output is not None:
            self.output(f"[t={self.time:>6}] {text}")

    # ======================================================================
    # Schnittstelle für Knoten
    # ======================================================================

    def send(self, src: int, dst: int, kind: str, data: dict[str, Any]) -> Message:
        if dst not in self.nodes:
            raise ValueError(f"Knoten {dst} gibt es nicht.")
        msg = Message(next(self._msg_ids), src, dst, kind, dict(data))
        background = kind in BACKGROUND_KINDS
        if background:
            self.stats.heartbeats += 1
        else:
            self.stats.messages[kind] += 1
        when = self.time + self.network.delay(src, dst)
        self._push(Event(when, next(self._seq), "msg", dst, msg=msg, background=background))
        return msg

    def set_timer(self, node_id: int, name: str, delay: int, data: dict[str, Any], background: bool) -> None:
        self.cancel_timer(node_id, name)
        event = Event(self.time + delay, next(self._seq), "timer", node_id,
                      timer=name, timer_data=dict(data), background=background)
        self._timers[(node_id, name)] = event
        self._push(event)

    def cancel_timer(self, node_id: int, name: str) -> None:
        event = self._timers.pop((node_id, name), None)
        if event is not None:
            event.cancelled = True

    def cancel_all_timers(self, node_id: int) -> None:
        for key in [k for k in self._timers if k[0] == node_id]:
            self.cancel_timer(*key)

    def election_started(self, node_id: int) -> None:
        """Ein Knoten meldet, dass er eine Wahl beginnt (für die Messwerte)."""
        if self.election is None:
            self.election = Election(
                start=self.time,
                initiator=node_id,
                messages_at_start=self.stats.total_messages,
                leader_lost_at=self._leader_lost_at,
            )

    # ======================================================================
    # Befehle von außen (CLI, Tests, Benchmark)
    # ======================================================================

    def node(self, node_id: int) -> Node:
        if node_id not in self.nodes:
            raise ValueError(f"Knoten {node_id} gibt es nicht (1 bis {len(self.nodes)}).")
        return self.nodes[node_id]

    def start_election(self, node_id: int) -> None:
        node = self.node(node_id)
        if not node.alive:
            raise ValueError(f"Knoten {node_id} ist ausgefallen und kann keine Wahl starten.")
        node.start_election()
        self._after_event()

    def kill(self, node_id: int) -> None:
        node = self.node(node_id)
        if not node.alive:
            raise ValueError(f"Knoten {node_id} ist schon ausgefallen.")
        if node.is_leader:
            self._leader_lost_at = self.time
        node.alive = False
        self.cancel_all_timers(node_id)
        self.log(f"!!! Knoten {node_id} fällt aus")
        node.on_crash()
        self._after_event()

    def revive(self, node_id: int) -> None:
        node = self.node(node_id)
        if node.alive:
            raise ValueError(f"Knoten {node_id} läuft bereits.")
        node.alive = True
        node.reset()
        self.log(f"!!! Knoten {node_id} startet neu")
        node.on_recover()
        self._after_event()

    def set_delay(self, a: int, b: int, ms: int) -> None:
        self.node(a), self.node(b)
        self.network.set_delay(a, b, ms)

    def partition(self, groups: list[set[int]]) -> None:
        self.network.partition(groups, list(self.nodes))
        self.log(f"!!! {self.network.describe()}")

    def heal(self) -> None:
        self.network.heal()
        self.log("!!! Netzwerktrennung aufgehoben")

    def set_timeout(self, ms: int) -> None:
        for node in self.nodes.values():
            node.timeout = ms

    def set_detect(self, on: bool) -> None:
        self.detect = on
        for node in self.nodes.values():
            if not node.alive:
                continue
            if not on:
                self.cancel_timer(node.id, "hb_send")
                self.cancel_timer(node.id, "hb_watch")
            elif node.is_leader:
                node.set_timer("hb_send", self.hb_interval, background=True)
            elif node.leader is not None:
                node.watch_leader()

    def reset_stats(self) -> None:
        self.stats = Stats()
        self.election = None
        self._leader_lost_at = None

    # ======================================================================
    # Ablauf
    # ======================================================================

    def step(self) -> Event | None:
        """Führt genau ein Ereignis aus (auch Hintergrund-Ereignisse)."""
        event = self._pop()
        if event is None:
            return None
        self.time = event.time
        if event.kind == "msg":
            self._deliver(event)
        else:
            self._fire(event)
        self._after_event()
        return event

    def step_visible(self) -> Event | None:
        """Führt Ereignisse aus, bis ein Vordergrund-Ereignis dran war."""
        while True:
            event = self.step()
            if event is None or not event.background:
                return event

    def run(self, duration: int | None = None, max_time: int = 30_000) -> bool:
        """Lässt die Simulation laufen.

        Mit `duration`: genau so viele ms virtuelle Zeit.
        Ohne: bis keine Wahl-Nachrichten mehr unterwegs sind (und, bei
        eingeschalteter Ausfallerkennung, bis sich alle einig sind).
        Gibt False zurück, wenn nach `max_time` ms noch keine Ruhe war.
        """
        if duration is not None:
            end = self.time + duration
            while self._queue and self._peek_time() <= end:
                self.step()
            self.time = end
            return True

        start = self.time
        while True:
            if not self.pending() and (not self.detect or self.agreement() is not None):
                return True
            if self.time - start > max_time:
                self.log(f"(angehalten nach {max_time} ms ohne Ruhe)")
                return False
            if self.step() is None:
                return True

    def pending(self, include_background: bool = False) -> list[Event]:
        events = [e for e in self._queue if not e.cancelled and (include_background or not e.background)]
        return sorted(events)

    # ======================================================================
    # Auswertung
    # ======================================================================

    def leaders(self) -> list[int]:
        return [n.id for n in self.nodes.values() if n.is_leader]

    def agreement(self) -> dict[int, int] | None:
        """Sind sich alle einig? Liefert {Gruppe: Chef} oder None.

        Bei einer Netzwerktrennung wird jede Gruppe einzeln geprüft. Einig
        heißt: Kein lebender Knoten der Gruppe steckt noch in einer Wahl, alle
        halten denselben lebenden Knoten derselben Gruppe für den Chef, und
        der hält sich selbst dafür.
        """
        groups = self.network.groups or [set(self.nodes)]
        result = {}
        for index, group in enumerate(groups):
            alive = [self.nodes[i] for i in sorted(group) if self.nodes[i].alive]
            if not alive:
                continue
            if any(n.describe_state() not in (FOLLOWER, LEADER) for n in alive):
                return None  # jemand wählt gerade noch
            believed = {n.leader for n in alive}
            if len(believed) != 1:
                return None
            leader = believed.pop()
            if leader is None or leader not in group or not self.nodes[leader].is_leader:
                return None
            result[index] = leader
        return result or None

    # ======================================================================
    # Intern
    # ======================================================================

    def _push(self, event: Event) -> None:
        heapq.heappush(self._queue, event)

    def _pop(self) -> Event | None:
        while self._queue:
            event = heapq.heappop(self._queue)
            if not event.cancelled:
                return event
        return None

    def _peek_time(self) -> int:
        while self._queue and self._queue[0].cancelled:
            heapq.heappop(self._queue)
        return self._queue[0].time if self._queue else self.time

    def _deliver(self, event: Event) -> None:
        msg = event.msg
        assert msg is not None
        quiet = msg.kind in self.hidden_kinds
        node = self.nodes[msg.dst]
        if not self.network.can_reach(msg.src, msg.dst):
            self.stats.dropped += 1
            if not quiet:
                self.log(f"{msg}   (verloren: Netzwerktrennung)")
            return
        if not node.alive:
            self.stats.dropped += 1
            if not quiet:
                self.log(f"{msg}   (verloren: Knoten {msg.dst} ist ausgefallen)")
            return
        if not quiet:
            self.log(str(msg))
        node.receive(msg)

    def _fire(self, event: Event) -> None:
        key = (event.node_id, event.timer)
        if self._timers.get(key) is event:
            del self._timers[key]
        node = self.nodes[event.node_id]
        if node.alive:
            node.fire_timer(event.timer, event.timer_data)

    def _after_event(self) -> None:
        self.stats.max_leaders = max(self.stats.max_leaders, len(self.leaders()))
        election = self.election
        if election is None:
            return
        agreed = self.agreement()
        if agreed is None:
            election.agreed_at = None
            return
        if election.agreed_at is None:
            election.agreed_at = self.time
        if self.pending():
            return  # es sind noch Wahl-Nachrichten unterwegs
        election.duration = election.agreed_at - election.start
        election.messages = self.stats.total_messages - election.messages_at_start
        election.leaders = sorted(set(agreed.values()))
        self.stats.elections.append(election)
        self.election = None
        self._leader_lost_at = None

        if len(election.leaders) == 1:
            who = f"Chef ist Knoten {election.leaders[0]}"
        else:
            who = "MEHRERE Chefs: " + ", ".join(str(i) for i in election.leaders)
        text = f"=== Einigung: {who} (Wahl dauerte {election.duration} ms, {election.messages} Nachrichten"
        if election.leader_lost_at is not None:
            text += f", {election.agreed_at - election.leader_lost_at} ms ohne Chef"
        self.log(text + ")")
