"""Nachrichten, die zwischen den Knoten verschickt werden."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Message:
    """Eine Nachricht von Knoten `src` an Knoten `dst`.

    `kind` ist der Nachrichtentyp, z. B. ELECTION, OK oder COORDINATOR.
    In `data` stehen zusätzliche Angaben. Schlüssel, die mit "_" beginnen,
    sind nur für die Technik da und erscheinen nicht im Log.
    """

    msg_id: int
    src: int
    dst: int
    kind: str
    data: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        text = f"[{self.src} -> {self.dst}] {self.kind}"
        shown = {k: v for k, v in self.data.items() if not k.startswith("_")}
        if shown:
            text += " " + " ".join(f"{k}={v}" for k, v in shown.items())
        return text
