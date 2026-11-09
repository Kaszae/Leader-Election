# Leader-Election

Simulation von Leader-Election-Algorithmen für das Modul Verteilte Systeme.
Mehrere Knoten wählen einen Chef (Leader). Fällt der Chef aus oder zerfällt
das Netz, sieht man im Log Nachricht für Nachricht, wie die Knoten reagieren.

Bisher dabei: **Bully** (Garcia-Molina 1982) und **Ring** (Chang-Roberts 1979).

## Starten

Nur Python 3.10 oder neuer, keine weiteren Pakete nötig.

```
python main.py                    # 5 Knoten, Bully
python main.py --algo ring --nodes 7
python main.py --script szenarien/01_chef_faellt_aus.txt
```

Beispiel:

```
(bully) > start 2
[t=     0] Knoten 2: startet eine Wahl
[t=   100] [2 -> 5] ELECTION
...
[t=   425] === Einigung: Chef ist Knoten 5 (Wahl dauerte 316 ms, 30 Nachrichten)
(bully) > kill 5
(bully) > start 1
```

## Befehle

| Befehl | Was passiert |
| --- | --- |
| `init 5 bully` | 5 Knoten neu anlegen (Algorithmus `bully` oder `ring`, optional Seed) |
| `start 2` | Knoten 2 startet eine Wahl |
| `kill 5` / `revive 5` | Knoten 5 fällt aus / startet neu (und startet dann eine Wahl) |
| `delay 3 4 500` | Verbindung 3 <-> 4 braucht 500 ms (`delay 100` setzt alle zurück) |
| `partition 1,2,3 \| 4,5` | Netzwerktrennung, `heal` hebt sie auf |
| `timeout 300` | wie lange ein Knoten auf eine Antwort wartet |
| `detect on` | automatische Ausfallerkennung: der Chef schickt Heartbeats, bleiben sie aus, startet jemand eine Wahl |
| `mode step` | nichts läuft von selbst, `step` stellt eine Nachricht zu, Enter wiederholt `step` |
| `mode auto` | nach jedem Befehl läuft die Simulation, bis Ruhe ist (Standard) |
| `run` / `run 2000` | bis zur Ruhe laufen / genau 2000 ms laufen |
| `queue` | zeigt, was gerade unterwegs ist |
| `status` | Zustand aller Knoten und des Netzes |
| `stats` | Messwerte: Nachrichten, Dauer jeder Wahl, höchste Anzahl gleichzeitiger Chefs |
| `show ACK` / `hide ACK` | Nachrichtentyp im Log zeigen oder verstecken (HEARTBEAT und ACK sind versteckt, werden aber gezählt) |

## Wie die Simulation funktioniert

- **Virtuelle Zeit statt echter Zeit.** Jede Nachricht und jeder Timer ist ein
  Ereignis mit Zeitstempel in einer Warteschlange. Der Simulator nimmt immer
  das früheste Ereignis. Dadurch ist jeder Lauf mit demselben Seed gleich,
  der Schritt-Modus ist einfach und ein Benchmark mit vielen Wahlen dauert
  nur Sekunden.
- **Netzwerk:** Jede Nachricht braucht 100 ms plus 0 bis 10 ms Zufall.
  Nachrichten an ausgefallene Knoten oder über eine Netzwerktrennung gehen
  verloren und erscheinen im Log mit `(verloren: ...)`.
- **Knoten** sehen nie direkt in andere Knoten hinein, sie erfahren alles nur
  über Nachrichten und Timeouts.
- **Messwerte:** Sobald sich nach einer Wahl alle einig sind, steht im Log eine
  Zeile `=== Einigung`. Bei einer Netzwerktrennung wird jede Gruppe einzeln
  geprüft, dann steht dort z. B. `MEHRERE Chefs: 3, 5`.

## Aufbau

```
main.py                      Startpunkt
leader_election/
  message.py                 Nachricht (von, an, Typ, Daten)
  network.py                 Verzögerung und Netzwerktrennung
  node.py                    Basisklasse Knoten, inkl. Heartbeat-Ausfallerkennung
  simulator.py               Uhr, Warteschlange, Messwerte
  cli.py                     Kommandozeile
  algorithms/
    bully.py
    ring.py
szenarien/                   Befehlsdateien für --script
tests/                       pytest-Tests
```

## Eigene Variante hinzufügen

1. Neue Datei in `leader_election/algorithms/`, Klasse erbt von `Node`.
2. `start_election()`, `on_message(msg)` und `on_timer(name, data)` schreiben.
   Werkzeuge: `self.send(ziel, "TYP", schluessel=wert)`,
   `self.set_timer("name", ms)`, `self.become_leader()`,
   `self.accept_leader(id)`, `self.log("text")`.
3. In `leader_election/algorithms/__init__.py` in `ALGORITHMS` eintragen.
   Danach geht `init 5 meinname` und alle Tests in `tests/test_common.py`
   laufen automatisch auch für die neue Variante.

## Tests

```
pip install -r requirements-dev.txt
python -m pytest
```

## Hinweise zu den Algorithmen

- **Bully** folgt dem Original: Auch ein amtierender Chef, der ein ELECTION
  bekommt, hält eine neue Wahl ab und schickt COORDINATOR an alle. Das macht
  den Unterschied zwischen bestem Fall (der höchste startet, n-1 Nachrichten)
  und schlechtestem Fall (der niedrigste startet, etwa n² Nachrichten) sichtbar.
- **Ring** braucht für Ausfälle eine Erweiterung: Jede Weitergabe wird mit ACK
  bestätigt. Fehlt das ACK, wird der Nachfolger übersprungen. Stirbt der
  Kandidat selbst, trägt sich der Knoten vor ihm stattdessen ein. Eine
  Nachricht, die zu lange kreist, wird verworfen, und ein Teilnehmer, der zu
  lange kein Ergebnis bekommt, startet die Wahl neu.
