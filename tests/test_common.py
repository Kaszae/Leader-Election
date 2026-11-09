"""Tests, die für jeden Algorithmus gelten müssen."""

import pytest

from leader_election.algorithms import ALGORITHMS
from tests.helpers import believed_leaders, make

ALGOS = sorted(ALGORITHMS)


@pytest.mark.parametrize("algo", ALGOS)
@pytest.mark.parametrize("initiator", [1, 2, 3, 4, 5])
def test_hoechste_nummer_wird_chef(algo, initiator):
    sim = make(algo)
    sim.start_election(initiator)
    assert sim.run()
    assert sim.leaders() == [5]
    assert believed_leaders(sim) == {5}
    assert sim.stats.max_leaders == 1
    assert len(sim.stats.elections) == 1


@pytest.mark.parametrize("algo", ALGOS)
def test_chef_faellt_aus(algo):
    sim = make(algo)
    sim.start_election(1)
    sim.run()
    sim.kill(5)
    sim.start_election(2)
    sim.run()
    assert sim.leaders() == [4]
    assert believed_leaders(sim) == {4}
    assert sim.stats.max_leaders == 1
    last = sim.stats.elections[-1]
    assert last.leaders == [4]
    assert last.leader_lost_at is not None


@pytest.mark.parametrize("algo", ALGOS)
def test_zwei_gleichzeitige_wahlen(algo):
    sim = make(algo)
    sim.start_election(1)
    sim.start_election(2)
    sim.run()
    assert sim.leaders() == [5]
    assert believed_leaders(sim) == {5}


@pytest.mark.parametrize("algo", ALGOS)
def test_alter_chef_kommt_zurueck(algo):
    sim = make(algo)
    sim.start_election(1)
    sim.run()
    sim.kill(5)
    sim.start_election(1)
    sim.run()
    sim.revive(5)
    sim.run()
    assert sim.leaders() == [5]
    assert believed_leaders(sim) == {5}


@pytest.mark.parametrize("algo", ALGOS)
def test_netzwerktrennung_gibt_zwei_chefs(algo):
    sim = make(algo)
    sim.start_election(1)
    sim.run()
    sim.partition([{1, 2, 3}, {4, 5}])
    sim.start_election(1)
    sim.run()
    assert sorted(sim.leaders()) == [3, 5]
    assert sim.stats.max_leaders == 2
    assert sim.stats.elections[-1].leaders == [3, 5]

    sim.heal()
    sim.start_election(1)
    sim.run()
    assert sim.leaders() == [5]
    assert believed_leaders(sim) == {5}


@pytest.mark.parametrize("algo", ALGOS)
def test_ein_einzelner_knoten_wird_chef(algo):
    sim = make(algo)
    for i in (2, 3, 4, 5):
        sim.kill(i)
    sim.start_election(1)
    sim.run()
    assert sim.leaders() == [1]


@pytest.mark.parametrize("algo", ALGOS)
def test_ausfallerkennung_startet_wahl_von_selbst(algo):
    sim = make(algo)
    sim.start_election(1)
    sim.run()
    sim.set_detect(True)
    sim.run(3000)  # ein paar Heartbeats laufen
    assert sim.stats.heartbeats > 0
    sim.kill(5)
    assert sim.run()  # niemand startet per Hand eine Wahl
    assert sim.leaders() == [4]
    assert believed_leaders(sim) == {4}


@pytest.mark.parametrize("algo", ALGOS)
def test_gleicher_seed_gleicher_ablauf(algo):
    def play(seed):
        sim = make(algo, seed=seed)
        sim.start_election(2)
        sim.run()
        sim.kill(5)
        sim.start_election(1)
        sim.run()
        return sim.lines

    assert play(7) == play(7)
    assert play(7) != play(8)
