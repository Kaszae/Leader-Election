import pytest

from leader_election.cli import LeaderCLI, parse_groups


def run(cli, *lines):
    for line in lines:
        cli.onecmd(line)


def test_partition_eingabe():
    assert parse_groups("1,2,3 | 4,5") == [{1, 2, 3}, {4, 5}]
    assert parse_groups("1 2|3") == [{1, 2}, {3}]
    with pytest.raises(ValueError):
        parse_groups("1,2,3")


def test_alle_befehle_laufen(capsys):
    cli = LeaderCLI()
    run(cli, "help", "init 5 ring 3", "start 1", "kill 5", "start 2", "revive 5",
        "delay 1 2 300", "delay 100", "timeout 400", "partition 1,2 | 3,4,5", "start 1",
        "heal", "detect on", "run 2000", "detect off", "show ACK", "hide ACK",
        "status", "stats", "reset", "mode step", "start 3", "step", "step 3", "queue", "run")
    out = capsys.readouterr().out
    assert "Fehler" not in out
    assert "Einigung" in out
    assert cli.sim.algorithm == "ring"


def test_fehler_werden_freundlich_gemeldet(capsys):
    cli = LeaderCLI()
    run(cli, "start 9", "kill abc", "init 3 paxos", "partition 1,1 | 1", "mode schnell")
    out = capsys.readouterr().out
    assert out.count("Fehler") == 5


def test_enter_wiederholt_step(capsys):
    cli = LeaderCLI()
    run(cli, "mode step", "start 1", "step")
    time_after_first = cli.sim.time
    cli.onecmd("step")
    cli.lastcmd = "step"
    cli.emptyline()
    assert cli.sim.time > time_after_first
