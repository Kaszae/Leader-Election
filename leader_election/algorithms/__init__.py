"""Alle verfügbaren Algorithmen. Eine eigene Variante einfach hier eintragen."""

from .bully import BullyNode
from .ring import RingNode

ALGORITHMS = {
    "bully": BullyNode,
    "ring": RingNode,
}
