"""Interaktive Kommandozeile für die Simulation."""

from __future__ import annotations

import argparse
import cmd
import sys

from .algorithms import ALGORITHMS
from .simulator import Simulator

HELP = """\
Befehle (Knoten haben die Nummern 1 bis n):

  init N [ALGO] [SEED]   N Knoten neu anlegen, ALGO = {algos} (z. B. init 5 bully)
  start ID               Knoten ID startet eine Wahl
  kill ID                Knoten ID fällt aus
  revive ID              Knoten ID startet neu (und startet dabei eine Wahl)
  delay A B MS           Verbindung A <-> B braucht MS Millisekunden
  delay MS               alle Verbindungen auf MS Millisekunden setzen
  partition 1,2,3 | 4,5  Netz in Gruppen teilen, nur innerhalb einer Gruppe geht etwas durch
  heal                   Netzwerktrennung aufheben
  timeout MS             wie lange Knoten auf eine Antwort warten (Standard 300)
  detect on|off          automatische Ausfallerkennung über Heartbeats

  mode auto|step         auto: nach jedem Befehl bis zur Ruhe laufen
                         step: nichts passiert, bis du step oder run eingibst
  step [N]               N Nachrichten zustellen (leere Eingabe = nochmal step)
  run [MS]               bis zur Ruhe laufen, oder genau MS Millisekunden
  queue                  zeigt, welche Nachrichten gerade unterwegs sind

  status                 Zustand aller Knoten
  stats                  Messwerte: Nachrichten, Dauer, Anzahl Chefs
  reset                  Messwerte auf null setzen
  show TYP / hide TYP    Nachrichtentyp im Log zeigen/verstecken (z. B. show ACK)
  quit                   beenden
"""


def parse_int(text: str, what: str = "Zahl") -> int:
    try:
        return int(text)
    except ValueError:
        raise ValueError(f"'{text}' ist keine gültige {what}.") from None


def parse_groups(text: str) -> list[set[int]]:
    groups = []
    for part in text.split("|"):
        ids = {parse_int(x.strip(), "Knotennummer") for x in part.replace(" ", ",").split(",") if x.strip()}
        if ids:
            groups.append(ids)
    if len(groups) < 2:
        raise ValueError("Bitte mindestens zwei Gruppen angeben, z. B.: partition 1,2,3 | 4,5")
    return groups


class LeaderCLI(cmd.Cmd):
    def __init__(self, sim: Simulator | None = None):
        super().__init__()
        self.sim = sim or Simulator("bully", 5)
        self.mode = "auto"
        self._update_prompt()

    # --- Rahmen ------------------------------------------------------------

    def _update_prompt(self) -> None:
        tag = f"{self.sim.algorithm}" + (", step" if self.mode == "step" else "")
        self.prompt = f"({tag}) > "

    def onecmd(self, line: str) -> bool:
        try:
            return super().onecmd(line)
        except ValueError as error:
            print(f"Fehler: {error}")
            return False

    def emptyline(self) -> bool:
        # Leere Eingabe wiederholt nur "step", damit man sich mit Enter durchklicken kann.
        if self.lastcmd.startswith("step"):
            return self.onecmd(self.lastcmd)
        return False

    def default(self, line: str) -> None:
        print(f"Unbekannter Befehl: {line.split()[0]}. 'help' zeigt alle Befehle.")

    def do_help(self, arg: str) -> None:
        print(HELP.format(algos="|".join(ALGORITHMS)))

    def _auto(self) -> None:
        if self.mode == "auto":
            self.sim.run()

    def _ids(self, arg: str, count: int) -> list[int]:
        parts = arg.split()
        if len(parts) != count:
            raise ValueError("Falsche Anzahl an Angaben. 'help' zeigt die Befehle.")
        return [parse_int(p, "Knotennummer") for p in parts]

    # --- Aufbau ------------------------------------------------------------

    def do_init(self, arg: str) -> None:
        parts = arg.split()
        n = parse_int(parts[0], "Anzahl") if parts else len(self.sim.nodes)
        algo = parts[1] if len(parts) > 1 else self.sim.algorithm
        seed = parse_int(parts[2], "Seed") if len(parts) > 2 else 0
        self.sim = Simulator(algo, n, seed=seed)
        self._update_prompt()
        print(f"{n} Knoten mit Algorithmus '{algo}' angelegt (Seed {seed}). Noch kein Chef gewählt.")

    # --- Ereignisse --------------------------------------------------------

    def do_start(self, arg: str) -> None:
        (node_id,) = self._ids(arg, 1)
        self.sim.start_election(node_id)
        self._auto()

    def do_kill(self, arg: str) -> None:
        (node_id,) = self._ids(arg, 1)
        self.sim.kill(node_id)
        self._auto()

    def do_revive(self, arg: str) -> None:
        (node_id,) = self._ids(arg, 1)
        self.sim.revive(node_id)
        self._auto()

    def do_delay(self, arg: str) -> None:
        parts = arg.split()
        if len(parts) == 1:
            self.sim.network.set_all_delays(parse_int(parts[0], "Verzögerung"))
        elif len(parts) == 3:
            a, b, ms = (parse_int(p) for p in parts)
            self.sim.set_delay(a, b, ms)
        else:
            raise ValueError("Benutzung: delay A B MS  oder  delay MS")
        print(self.sim.network.describe())

    def do_partition(self, arg: str) -> None:
        self.sim.partition(parse_groups(arg))
        self._auto()

    def do_heal(self, arg: str) -> None:
        self.sim.heal()
        self._auto()

    def do_timeout(self, arg: str) -> None:
        (ms,) = self._ids(arg, 1)
        self.sim.set_timeout(ms)
        print(f"Timeout aller Knoten: {ms} ms")

    def do_detect(self, arg: str) -> None:
        if arg.strip() not in ("on", "off"):
            raise ValueError("Benutzung: detect on  oder  detect off")
        self.sim.set_detect(arg.strip() == "on")
        state = "an" if self.sim.detect else "aus"
        print(f"Ausfallerkennung {state} (Heartbeat alle {self.sim.hb_interval} ms, "
              f"Verdacht nach {self.sim.hb_timeout} ms Stille)")
        self._auto()

    # --- Ablauf ------------------------------------------------------------

    def do_mode(self, arg: str) -> None:
        if arg.strip() not in ("auto", "step"):
            raise ValueError("Benutzung: mode auto  oder  mode step")
        self.mode = arg.strip()
        self._update_prompt()

    def do_step(self, arg: str) -> None:
        count = parse_int(arg, "Anzahl") if arg.strip() else 1
        for _ in range(count):
            if self.sim.step_visible() is None:
                print("Nichts mehr unterwegs.")
                break

    def do_run(self, arg: str) -> None:
        if arg.strip():
            self.sim.run(parse_int(arg, "Dauer"))
        else:
            self.sim.run()

    def do_queue(self, arg: str) -> None:
        events = self.sim.pending()
        if not events:
            print("Nichts unterwegs.")
        for event in events:
            print(f"  t={event.time:>6}  {event.describe()}")

    # --- Anzeige -----------------------------------------------------------

    def do_status(self, arg: str) -> None:
        print(f"Zeit: {self.sim.time} ms, Algorithmus: {self.sim.algorithm}")
        print("  Knoten  lebt   Zustand     hält für Chef")
        for node in self.sim.nodes.values():
            alive = "ja" if node.alive else "nein"
            state = node.describe_state() if node.alive else "-"
            leader = node.leader if node.alive and node.leader is not None else "-"
            print(f"  {node.id:>6}  {alive:<5}  {state:<10}  {leader}")
        print(f"  Chefs gerade: {self.sim.leaders() or 'keiner'}")
        print(f"  Netz: {self.sim.network.describe()}")
        print(f"  Ausfallerkennung: {'an' if self.sim.detect else 'aus'}, Timeout {next(iter(self.sim.nodes.values())).timeout} ms")

    def do_stats(self, arg: str) -> None:
        stats = self.sim.stats
        by_kind = ", ".join(f"{k} {v}" for k, v in sorted(stats.messages.items())) or "keine"
        print(f"Nachrichten gesamt: {stats.total_messages} ({by_kind})")
        print(f"Heartbeats: {stats.heartbeats}, verlorene Nachrichten: {stats.dropped}")
        print(f"Höchste Anzahl gleichzeitiger Chefs: {stats.max_leaders}")
        if not stats.elections:
            print("Noch keine abgeschlossene Wahl.")
        for i, e in enumerate(stats.elections, 1):
            line = (f"  Wahl {i}: Start t={e.start} durch Knoten {e.initiator}, "
                    f"{e.duration} ms, {e.messages} Nachrichten, Chef {e.leaders}")
            if e.leader_lost_at is not None:
                line += f", {e.agreed_at - e.leader_lost_at} ms ohne Chef"
            print(line)
        if self.sim.election is not None:
            print(f"  Eine Wahl läuft noch (seit t={self.sim.election.start}).")

    def do_reset(self, arg: str) -> None:
        self.sim.reset_stats()
        print("Messwerte zurückgesetzt.")

    def do_show(self, arg: str) -> None:
        self.sim.hidden_kinds.discard(arg.strip().upper())
        print(f"Ausgeblendet: {sorted(self.sim.hidden_kinds) or 'nichts'}")

    def do_hide(self, arg: str) -> None:
        self.sim.hidden_kinds.add(arg.strip().upper())
        print(f"Ausgeblendet: {sorted(self.sim.hidden_kinds)}")

    def do_quit(self, arg: str) -> bool:
        return True

    do_exit = do_quit

    def do_EOF(self, arg: str) -> bool:
        print()
        return True


def run_script(cli: LeaderCLI, path: str) -> None:
    """Spielt eine Datei mit Befehlen ab (eine Zeile pro Befehl, # = Kommentar)."""
    with open(path, encoding="utf-8") as file:
        for raw in file:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):
                print(line)
                continue
            print(f"{cli.prompt}{line}")
            if cli.onecmd(line):
                break


def main(argv: list[str] | None = None) -> None:
    # Windows-Konsole: nicht abstürzen, falls ein Zeichen nicht darstellbar ist
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(description="Leader-Election-Simulation")
    parser.add_argument("--algo", default="bully", choices=sorted(ALGORITHMS))
    parser.add_argument("--nodes", type=int, default=5)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--script", help="Datei mit Befehlen abspielen, danach interaktiv weiter")
    parser.add_argument("--batch", action="store_true", help="nach dem Skript beenden")
    args = parser.parse_args(argv)

    cli = LeaderCLI(Simulator(args.algo, args.nodes, seed=args.seed))
    print(f"Leader-Election-Simulation: {args.nodes} Knoten, Algorithmus '{args.algo}'. "
          f"'help' zeigt alle Befehle.")
    if args.script:
        run_script(cli, args.script)
        if args.batch:
            return
    cli.cmdloop()
