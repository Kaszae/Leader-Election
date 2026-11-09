from tests.helpers import believed_leaders, make


def test_log_format():
    sim = make("bully")
    sim.start_election(2)
    sim.run()
    assert any("[2 -> 4] ELECTION" in line for line in sim.lines)
    assert any("[5 -> 1] COORDINATOR" in line for line in sim.lines)


def test_niedrigster_startet_kostet_mehr_als_hoechster():
    """Best Case gegen Worst Case: Kosten hängen davon ab, wer startet."""
    def cost(initiator):
        sim = make("bully")
        sim.start_election(initiator)
        sim.run()
        return sim.stats.total_messages

    assert cost(5) == 4  # nur COORDINATOR an alle anderen
    assert cost(1) > 3 * cost(5)


def test_falscher_verdacht_erzeugt_kurz_zwei_chefs():
    sim = make("bully")
    sim.start_election(1)
    sim.run()
    sim.set_delay(3, 4, 800)
    sim.set_delay(3, 5, 800)
    sim.start_election(3)
    sim.run()
    assert sim.stats.max_leaders == 2  # Knoten 3 hielt sich kurz für den Chef
    assert sim.leaders() == [5]  # am Ende setzt sich 5 wieder durch
    assert believed_leaders(sim) == {5}


def test_nachrichten_eines_toten_knotens_kommen_noch_an():
    """Knoten 5 stirbt direkt nach seiner Antwort. Sein COORDINATOR ist schon
    unterwegs, also folgt Knoten 4 einem toten Chef. Ohne Ausfallerkennung
    bleibt das so, mit Ausfallerkennung wird es repariert."""
    sim = make("bully")
    sim.start_election(1)
    sim.run()
    sim.start_election(4)
    sim.step()  # [4 -> 5] ELECTION kommt an, 5 schickt OK und COORDINATOR
    sim.kill(5)
    sim.run()
    assert sim.nodes[4].leader == 5
    assert sim.leaders() == []

    sim.set_detect(True)
    assert sim.run()
    assert sim.leaders() == [4]
    assert believed_leaders(sim) == {4}
