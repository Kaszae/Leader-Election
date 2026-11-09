"""Basisklasse für alle Knoten. Jeder Algorithmus erbt davon."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .message import Message

if TYPE_CHECKING:  # nur für Typ-Hinweise, verhindert zirkuläre Imports
    from .simulator import Simulator

FOLLOWER = "FOLLOWER"
LEADER = "LEADER"


class Node:
    """Ein Knoten im verteilten System.

    Ein Knoten kennt die Nummern aller Knoten, kann Nachrichten schicken und
    Timer stellen. Er sieht nie direkt in andere Knoten hinein, sondern
    erfährt alles nur über Nachrichten.

    Ein Algorithmus (Bully, Ring, eigene Variante ...) überschreibt:
      - start_election()          Wahl beginnen
      - on_message(msg)           auf eine Nachricht reagieren
      - on_timer(name, data)      auf einen abgelaufenen Timer reagieren
    und kann optional on_recover() und on_other_leader() anpassen.
    """

    name = "basis"

    def __init__(self, node_id: int, all_ids: list[int], sim: Simulator):
        self.id = node_id
        self.all_ids = sorted(all_ids)
        self.sim = sim
        self.alive = True
        self.timeout = 300  # ms, wie lange auf eine Antwort gewartet wird
        self.reset()

    # --- Zustand -----------------------------------------------------------

    def reset(self) -> None:
        """Flüchtiger Zustand. Geht bei einem Absturz verloren."""
        self.state = FOLLOWER
        self.leader: int | None = None

    @property
    def others(self) -> list[int]:
        return [i for i in self.all_ids if i != self.id]

    @property
    def is_leader(self) -> bool:
        return self.alive and self.state == LEADER

    def describe_state(self) -> str:
        return self.state

    # --- Werkzeuge für Algorithmen ----------------------------------------

    def log(self, text: str) -> None:
        self.sim.log(f"Knoten {self.id}: {text}")

    def send(self, dst: int, kind: str, **data: Any) -> Message:
        return self.sim.send(self.id, dst, kind, data)

    def set_timer(self, name: str, delay: int, background: bool = False, **data: Any) -> None:
        """Stellt einen Timer. Ein Timer gleichen Namens wird ersetzt."""
        self.sim.set_timer(self.id, name, delay, data, background)

    def cancel_timer(self, name: str) -> None:
        self.sim.cancel_timer(self.id, name)

    def become_leader(self) -> None:
        was_leader = self.state == LEADER
        self.state = LEADER
        self.leader = self.id
        self.log("bleibt Chef" if was_leader else "ist jetzt Chef")
        if self.sim.detect:
            self.set_timer("hb_send", self.sim.hb_interval, background=True)

    def accept_leader(self, leader: int) -> None:
        self.state = FOLLOWER
        self.leader = leader
        if self.sim.detect:
            self.watch_leader()

    # --- Wird vom Simulator aufgerufen ------------------------------------

    def receive(self, msg: Message) -> None:
        if msg.kind == "HEARTBEAT":
            self._on_heartbeat(msg.src)
        else:
            self.on_message(msg)

    def fire_timer(self, name: str, data: dict[str, Any]) -> None:
        if name == "hb_send":
            self._send_heartbeats()
        elif name == "hb_watch":
            self._on_heartbeat_missing()
        else:
            self.on_timer(name, data)

    # --- Ausfallerkennung über Heartbeats (nur wenn sim.detect an ist) ----
    #
    # Der Chef schickt regelmäßig HEARTBEAT an alle. Bleibt der Heartbeat bei
    # einem Knoten zu lange aus, vermutet er, dass der Chef ausgefallen ist,
    # und startet eine Wahl. Der Knoten kann sich dabei irren (falscher
    # Verdacht), wenn der Chef nur langsam ist.

    def watch_leader(self) -> None:
        # etwas Zufall, damit nicht alle Knoten im selben Moment misstrauisch werden
        delay = self.sim.hb_timeout + self.sim.rng.randint(0, self.sim.hb_interval)
        self.set_timer("hb_watch", delay, background=True)

    def _send_heartbeats(self) -> None:
        if not self.is_leader or not self.sim.detect:
            return
        for other in self.others:
            self.send(other, "HEARTBEAT")
        self.set_timer("hb_send", self.sim.hb_interval, background=True)

    def _on_heartbeat(self, src: int) -> None:
        if self.is_leader:
            self.on_other_leader(src)
        elif src == self.leader:
            self.watch_leader()

    def _on_heartbeat_missing(self) -> None:
        if self.state == FOLLOWER and self.leader is not None:
            self.log(f"hört nichts mehr von Chef {self.leader} und vermutet einen Ausfall")
            self.leader = None
            self.start_election()

    # --- Von Algorithmen zu überschreiben ---------------------------------

    def start_election(self) -> None:
        raise NotImplementedError

    def on_message(self, msg: Message) -> None:
        raise NotImplementedError

    def on_timer(self, name: str, data: dict[str, Any]) -> None:
        pass

    def on_crash(self) -> None:
        """Wird beim Absturz aufgerufen (Timer sind schon gelöscht)."""

    def on_recover(self) -> None:
        """Nach dem Neustart weiß der Knoten nicht, wer Chef ist: neue Wahl."""
        self.start_election()

    def on_other_leader(self, other: int) -> None:
        """Ein Chef bekommt einen Heartbeat von einem anderen Chef.

        Das passiert z. B., wenn eine Netzwerktrennung aufgehoben wird.
        Standard: Hat der andere die höhere Nummer, gibt dieser Knoten auf.
        Sonst startet er eine Wahl, damit sich die höhere Nummer durchsetzt.
        """
        if other > self.id:
            self.accept_leader(other)
        else:
            self.start_election()
