"""Ring-Algorithmus nach Chang und Roberts (1979).

Die Knoten sitzen nach Nummer sortiert im Kreis (1 -> 2 -> ... -> n -> 1).
Nachrichten gehen immer nur an den Nachfolger.

1. Wer eine Wahl startet, schickt ELECTION(kandidat=eigene Nummer) los und
   ist ab dann "Teilnehmer".
2. Wer ELECTION(k) bekommt:
   - k größer als die eigene Nummer: weiterreichen.
   - k kleiner und noch kein Teilnehmer: eigene Nummer eintragen, weiter.
   - k kleiner und schon Teilnehmer: verwerfen (es läuft schon eine
     Nachricht mit größerer Nummer herum).
   - k gleich der eigenen Nummer: Die Nachricht ist einmal herum, der Knoten
     hat die höchste Nummer und ist Chef. Er schickt ELECTED(chef) herum.
3. ELECTED wird einmal herumgereicht, jeder merkt sich den Chef.

Erweiterung für Ausfälle (wie bei Tanenbaum/van Steen beschrieben): Jede
Weitergabe muss der Nachfolger mit ACK bestätigen. Kommt kein ACK, gilt der
Nachfolger als ausgefallen und der übernächste wird versucht. Das kostet
Nachrichten und Zeit, zeigt aber genau die Schwäche des Rings: Ein kaputter
Knoten hält alles auf.
"""

from __future__ import annotations

from typing import Any

from ..message import Message
from ..node import FOLLOWER, LEADER, Node


class RingNode(Node):
    name = "ring"

    def reset(self) -> None:
        super().reset()
        self.participant = False
        # noch nicht bestätigte Weitergaben: msg_id -> (Ziel, Typ, Daten, Hops, übersprungen)
        self._pending: dict[int, tuple[int, str, dict[str, Any], int, list[int]]] = {}

    def describe_state(self) -> str:
        if self.participant and self.state != LEADER:
            return "ELECTION"
        return self.state

    def successor_of(self, node_id: int) -> int:
        index = self.all_ids.index(node_id)
        return self.all_ids[(index + 1) % len(self.all_ids)]

    @property
    def election_timeout(self) -> int:
        """Wie lange ein Teilnehmer höchstens auf das Ergebnis wartet."""
        per_hop = self.timeout + 2 * self.sim.network.base_delay
        return 3 * len(self.all_ids) * per_hop

    # --- Wahl --------------------------------------------------------------

    def start_election(self) -> None:
        if not self.alive or self.participant:
            return
        self.sim.election_started(self.id)
        self.log("startet eine Wahl")
        self._join()
        self._forward("ELECTION", {"kandidat": self.id}, hops=0)

    def _join(self) -> None:
        self.participant = True
        self.set_timer("election_timeout", self.election_timeout)

    def _finish(self) -> None:
        self.participant = False
        self.cancel_timer("election_timeout")

    def on_message(self, msg: Message) -> None:
        if msg.kind == "ACK":
            mid = msg.data["_of"]
            self._pending.pop(mid, None)
            self.cancel_timer(f"ack:{mid}")
            return

        self.send(msg.src, "ACK", _of=msg.msg_id)
        # Sicherung: ELECTION braucht höchstens 2n Schritte, ELECTED n Schritte.
        # Kreist eine Nachricht länger (z. B. wegen falscher Ausfall-Vermutung), wird sie verworfen.
        hops = msg.data.get("_hops", 0) + 1
        if hops > 2 * len(self.all_ids):
            self.log(f"verwirft {msg.kind}, die Nachricht kreist zu lange")
            return

        if msg.kind == "ELECTION":
            self._on_election(msg.data["kandidat"], hops)
        elif msg.kind == "ELECTED":
            self._on_elected(msg.data["chef"], hops)

    def _on_election(self, candidate: int, hops: int) -> None:
        if candidate == self.id:
            self._finish()
            self.become_leader()
            self._forward("ELECTED", {"chef": self.id}, hops=0)
        elif candidate > self.id:
            self._join()
            self._forward("ELECTION", {"kandidat": candidate}, hops)
        elif not self.participant:
            self._join()
            self._forward("ELECTION", {"kandidat": self.id}, hops)
        else:
            self.log(f"verwirft ELECTION mit Kandidat {candidate} (eigene Nummer ist größer)")

    def _on_elected(self, leader: int, hops: int) -> None:
        self._finish()
        if leader == self.id:
            return  # ELECTED ist einmal herum, fertig
        self.accept_leader(leader)
        self._forward("ELECTED", {"chef": leader}, hops)

    # --- Zuverlässige Weitergabe an den Nachfolger -------------------------

    def _forward(self, kind: str, data: dict[str, Any], hops: int) -> None:
        self._send_to(self.successor_of(self.id), kind, data, hops, [])

    def _send_to(self, target: int, kind: str, data: dict[str, Any], hops: int, skipped: list[int]) -> None:
        if target == self.id:
            self.log("erreicht keinen anderen Knoten im Ring")
            if kind == "ELECTION":
                self._finish()
                self.become_leader()
            return
        msg = self.send(target, kind, _hops=hops, **data)
        self._pending[msg.msg_id] = (target, kind, data, hops, skipped)
        self.set_timer(f"ack:{msg.msg_id}", self.timeout, mid=msg.msg_id)

    def on_timer(self, name: str, data: dict[str, Any]) -> None:
        if name == "election_timeout":
            if self.participant:
                self.log("wartet zu lange auf das Wahlergebnis und startet neu")
                self.participant = False
                self.start_election()
            return

        if not name.startswith("ack:"):
            return
        entry = self._pending.pop(data["mid"], None)
        if entry is None:
            return
        target, kind, msg_data, hops, skipped = entry
        skipped = skipped + [target]
        self.log(f"bekommt kein ACK von {target} und überspringt ihn")

        if kind == "ELECTION" and msg_data["kandidat"] in skipped:
            # der Kandidat selbst ist ausgefallen, die Nachricht käme nie zu ihm zurück
            self.log(f"Kandidat {msg_data['kandidat']} ist ausgefallen, trägt sich selbst ein")
            msg_data = {"kandidat": self.id}
        elif kind == "ELECTED" and msg_data["chef"] in skipped:
            self.log(f"der gewählte Chef {msg_data['chef']} ist ausgefallen, neue Wahl")
            self.state = FOLLOWER
            self.leader = None
            self.start_election()
            return

        self._send_to(self.successor_of(target), kind, msg_data, hops, skipped)
