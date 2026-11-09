"""Bully-Algorithmus nach Garcia-Molina (1982).

Idee: Die höchste lebende Nummer wird Chef.

1. Wer eine Wahl startet, schickt ELECTION an alle Knoten mit höherer Nummer.
2. Wer ELECTION von einem niedrigeren Knoten bekommt, antwortet mit OK und
   startet selbst eine Wahl (er "drängt" den kleineren beiseite).
3. Kommt innerhalb des Timeouts kein OK, gibt es keinen lebenden höheren
   Knoten: Der Knoten wird Chef und schickt COORDINATOR an alle.
4. Kam ein OK, wartet der Knoten auf COORDINATOR. Kommt keiner, startet er
   die Wahl neu.

Annahme: synchrones Netz, d. h. Nachrichten brauchen höchstens eine bekannte
Zeit. Stimmt das nicht (Verzögerung > Timeout), entstehen falsche Chefs.
"""

from __future__ import annotations

from typing import Any

from ..message import Message
from ..node import FOLLOWER, LEADER, Node

ELECTION = "ELECTION"  # Zustand: wartet auf OK von höheren Knoten
WAITING = "WAITING"  # Zustand: hat OK bekommen, wartet auf COORDINATOR


class BullyNode(Node):
    name = "bully"

    def start_election(self) -> None:
        if not self.alive or self.state in (ELECTION, WAITING):
            return  # läuft schon
        self.sim.election_started(self.id)
        higher = [i for i in self.others if i > self.id]
        self.log("startet eine Wahl")
        if not higher:
            self.announce()
            return
        self.state = ELECTION
        for other in higher:
            self.send(other, "ELECTION")
        self.set_timer("wait_ok", self.timeout)

    def announce(self) -> None:
        """Wird Chef und teilt das allen mit."""
        self.cancel_timer("wait_ok")
        self.cancel_timer("wait_coordinator")
        self.become_leader()
        for other in self.others:
            self.send(other, "COORDINATOR")

    def on_message(self, msg: Message) -> None:
        if msg.kind == "ELECTION":
            self.send(msg.src, "OK")
            # Auch ein amtierender Chef hält eine neue Wahl ab. Ist er der
            # höchste, schickt er sofort wieder COORDINATOR an alle. Das ist
            # teuer, aber genau so beschreibt es der Original-Algorithmus.
            self.start_election()

        elif msg.kind == "OK":
            if self.state == ELECTION:
                self.cancel_timer("wait_ok")
                self.state = WAITING
                # großzügig warten: der höhere Knoten führt ja selbst noch eine Wahl
                self.set_timer("wait_coordinator", 3 * self.timeout)

        elif msg.kind == "COORDINATOR":
            if msg.src < self.id:
                self.log(f"Knoten {msg.src} will Chef sein, hat aber eine kleinere Nummer")
                if self.state == LEADER:
                    self.announce()
                else:
                    self.start_election()
            else:
                self.cancel_timer("wait_ok")
                self.cancel_timer("wait_coordinator")
                self.accept_leader(msg.src)

    def on_timer(self, name: str, data: dict[str, Any]) -> None:
        if name == "wait_ok" and self.state == ELECTION:
            self.log("bekommt kein OK von höheren Knoten")
            self.announce()
        elif name == "wait_coordinator" and self.state == WAITING:
            self.log("bekommt kein COORDINATOR und startet neu")
            self.state = FOLLOWER
            self.start_election()
