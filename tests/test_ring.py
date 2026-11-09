from tests.helpers import believed_leaders, make


def test_log_format():
    sim = make("ring")
    sim.start_election(2)
    sim.run()
    assert any("[2 -> 3] ELECTION kandidat=2" in line for line in sim.lines)
    assert any("[5 -> 1] ELECTED chef=5" in line for line in sim.lines)


def test_ohne_ausfall_genau_zwei_runden():
    sim = make("ring")
    sim.start_election(5)
    sim.run()
    # ELECTION einmal herum (5 Schritte) + ELECTED einmal herum (5), jeweils mit ACK
    assert sim.stats.messages["ELECTION"] == 5
    assert sim.stats.messages["ELECTED"] == 5
    assert sim.stats.messages["ACK"] == 10


def test_ausgefallene_knoten_werden_uebersprungen():
    sim = make("ring")
    sim.kill(3)
    sim.kill(4)
    sim.start_election(1)
    sim.run()
    assert sim.leaders() == [5]
    assert any("überspringt ihn" in line for line in sim.lines)


def test_kandidat_stirbt_waehrend_der_wahl():
    sim = make("ring")
    sim.start_election(1)
    sim.run(450)  # ELECTION mit Kandidat 5 ist gerade unterwegs
    sim.kill(5)
    assert sim.run()
    assert sim.leaders() == [4]
    assert believed_leaders(sim) == {4}
