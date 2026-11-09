from leader_election import Simulator


def make(algo: str, n: int = 5, seed: int = 0, **kwargs) -> Simulator:
    """Simulator ohne Bildschirmausgabe, das Log landet in sim.lines."""
    lines: list[str] = []
    sim = Simulator(algo, n, seed=seed, output=lines.append, **kwargs)
    sim.lines = lines  # type: ignore[attr-defined]
    return sim


def believed_leaders(sim: Simulator) -> set:
    return {n.leader for n in sim.nodes.values() if n.alive}
