"""Das simulierte Netzwerk: Verzögerungen und Netzwerktrennungen."""

from __future__ import annotations

import random


class Network:
    """Entscheidet, wie lange eine Nachricht braucht und ob sie ankommen kann.

    - Jede Verbindung hat eine Grundverzögerung (Standard 100 ms).
    - Dazu kommt ein kleiner Zufallsanteil (`jitter`), damit nicht alles
      exakt gleichzeitig passiert. Der Zufall ist über den Seed wiederholbar.
    - Einzelne Verbindungen können langsamer gemacht werden (`set_delay`).
    - Bei einer Netzwerktrennung (`partition`) können nur Knoten derselben
      Gruppe miteinander reden.
    """

    def __init__(self, rng: random.Random, base_delay: int = 100, jitter: int = 10):
        self.rng = rng
        self.base_delay = base_delay
        self.jitter = jitter
        self.link_delays: dict[frozenset[int], int] = {}
        self.groups: list[set[int]] | None = None

    # --- Verzögerung -------------------------------------------------------

    def set_delay(self, a: int, b: int, ms: int) -> None:
        """Setzt die Verzögerung der Verbindung a <-> b (beide Richtungen)."""
        self.link_delays[frozenset((a, b))] = ms

    def set_all_delays(self, ms: int) -> None:
        """Setzt die Grundverzögerung neu und löscht alle Einzelwerte."""
        self.base_delay = ms
        self.link_delays.clear()

    def delay(self, src: int, dst: int) -> int:
        base = self.link_delays.get(frozenset((src, dst)), self.base_delay)
        if self.jitter:
            base += self.rng.randint(0, self.jitter)
        return base

    # --- Netzwerktrennung --------------------------------------------------

    def partition(self, groups: list[set[int]], all_ids: list[int]) -> None:
        """Teilt das Netz in Gruppen. Nicht genannte Knoten sind ganz allein."""
        seen: set[int] = set()
        for group in groups:
            if seen & group:
                raise ValueError("Ein Knoten darf nur in einer Gruppe stehen.")
            unknown = group - set(all_ids)
            if unknown:
                raise ValueError(f"Unbekannte Knoten: {sorted(unknown)}")
            seen |= group
        rest = [{i} for i in all_ids if i not in seen]
        self.groups = [set(g) for g in groups if g] + rest

    def heal(self) -> None:
        self.groups = None

    def can_reach(self, a: int, b: int) -> bool:
        if self.groups is None:
            return True
        return self.group_index(a) == self.group_index(b)

    def group_index(self, node_id: int) -> int:
        if self.groups is None:
            return 0
        for i, group in enumerate(self.groups):
            if node_id in group:
                return i
        raise KeyError(node_id)

    def describe(self) -> str:
        text = f"Verzögerung {self.base_delay} ms (+0..{self.jitter} ms Zufall)"
        for link, ms in sorted(self.link_delays.items(), key=lambda kv: sorted(kv[0])):
            a, b = sorted(link)
            text += f", {a}<->{b}: {ms} ms"
        if self.groups is None:
            text += ". Keine Netzwerktrennung."
        else:
            parts = [",".join(str(i) for i in sorted(g)) for g in self.groups]
            text += ". Netzwerktrennung: " + " | ".join(parts)
        return text
