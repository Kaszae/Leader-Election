### Tag-Legende

- #TODO_M – M muss das noch erledigen
- #Frage_M – M fragt N
- #Antwort_M – M antwortet N (Fragensteller kann Frage und Antwort löschen)
	#Frage_M Was ist deine Lieblinsfarbe?
	#Antwort_N Blau
- #Note_M – M Randnotiz
- #FIXME_M – M muss Fehler beheben

___

## Roadmap und Deadlines bis zur Abgabe am 14.01.2027

#Frage_M Wollen wir früher mit dem Projekt fertig sein? Sagen wir Sonntag den 03.01.27?

- [ ] **22.11** Simulation mit CLI, Bully und Ring laufen
- [ ] **13.12** Eigene Variante und Benchmark-Modus fertig
- [ ] **20.12** Folien mit Quellen und Drehbuch fertig
- [ ] **07.01** Videoaufgenommen und geschnitten, Code mit README gepusht
- [ ] **14.01** Video in der HTW-Mediathek hochladen und URL and Professorin senden

## Arbeitsaufteilung

#Frage_M Würdest du die Aufgaben anders setzen wollen? Falls Nein, hast du für eines der beiden Aufgaben eine Präferenz?

- **Person 1:** Simulationsgerüst mit CLI und Logausgabe, dazu Bully und Ring implementieren.
- **Person 2:** Eigene Variante entwerfen und umsetzen, Entwurfstagebuch führen und den Benchmark-Modus mit der Vergleichstabelle bauen.
- **Beide:** Szenarien testen, Drehbuch schreiben, Video aufnehmen und schneiden.

Tipp: Führt von Anfang an ein kurzes Tagebuch (Datum, Idee, was nicht geklappt hat). Daraus entsteht Teil 6 des Videos fast von selbst.


___

## Die Grundidee in einfachen Worten

Mehrere Rechner (Knoten) arbeiten zusammen. Einer davon ist der Chef (Leader), der z. B. Aufgaben verteilt. Fällt der Chef aus, müssen sich die anderen auf einen neuen einigen, und zwar so, dass **am Ende genau einer** Chef ist. Das Schwierige: Nachrichten können verspätet ankommen oder verloren gehen, und ein Knoten weiß nie sicher, ob ein anderer tot ist oder nur langsam.

- **Bully:** Jeder Knoten hat eine Nummer. Die höchste lebende Nummer gewinnt. Wer merkt, dass der Chef weg ist, fragt alle Höheren. Antwortet keiner, wird er selbst Chef. Einfach, aber viele Nachrichten.
- **Ring (Chang-Roberts):** Die Knoten sitzen im Kreis. Eine Wahl-Nachricht wandert herum, jeder trägt sich ein, wenn seine Nummer größer ist. Kommt die Nachricht beim größten wieder an, ist er Chef. Wenige Nachrichten, aber langsam, und ein kaputter Knoten unterbricht den Ring.
- **Raft (nur der Wahl-Teil):** Kandidaten brauchen die Stimmen einer **Mehrheit**. Dazu gibt es eine Wahlperiode (Term), die hochgezählt wird. Dadurch kann es nie zwei gültige Chefs gleichzeitig geben, auch wenn das Netz in zwei Teile zerfällt.

## Einordnung in das Modul

Leader Election gehört zum Kapitel „Nebenläufigkeit, Koordination und Synchronisation“. Dort ist es ein klassisches Koordinationsproblem, ähnlich wie gegenseitiger Ausschluss.

- **Systemmodelle:** Bully setzt ein synchrones Modell voraus, also bekannte Höchstzeiten für Nachrichten. Raft kommt mit einem asynchronen Modell aus. Beide gehen von Crash-Fehlern aus.
- **Architekturen:** Ein Leader macht aus einem gleichberechtigten System (P2P) zeitweise ein System mit Zentrale (ähnlich Client/Server). Leaderlose Systeme wie Cassandra sind das Gegenbeispiel.
- **Interprozesskommunikation und Gruppenkommunikation:** Die Algorithmen bestehen nur aus Nachrichten an einzelne Knoten oder an die ganze Gruppe. Das zeigt eure Simulation direkt im Log.

## Drei konkrete Projektvarianten

#Frage_M Hast du hier eine Präferenz? Ich wäre für B und ich hatte im Kopf du auch?

### A) Der faire Vergleich

Bully, Ring und Raft-Wahl in derselben Simulation mit 5 bis 7 Knoten. Ihr schickt alle drei durch dieselben Szenarien und messt dasselbe. Sicher und gut zu erklären, aber ohne eigenen Beitrag etwas brav.

### B) Eigene Variante gegen die Klassiker (Empfehlung)

Ihr nehmt Bully als Basis und ändert **eine** Sache. Zwei gute Kandidaten:

1. **„Bully mit Mehrheit“:** Ein Knoten wird nur Chef, wenn eine Mehrheit der Knoten ihn bestätigt, und jede Wahl bekommt eine fortlaufende Wahlnummer. Das verhindert zwei Chefs bei einer Netzwerktrennung. Ehrlicher Hinweis: Damit erfindet ihr ein Stück von Raft nach. Das ist völlig in Ordnung und sogar eine schöne Pointe im Video („wir sind selbst darauf gekommen, warum Raft so gebaut ist“).
2. **„Bully nach Fitness“:** Statt der höchsten Nummer gewinnt der Knoten mit der besten Eignung (wenig Last, gute Verbindung). Klingt praktisch, bringt aber neue Probleme: Die Werte ändern sich ständig, und die Knoten können sich uneinig sein. Genau diese Probleme kann man gut zeigen.

Variante 1 ist die stärkere Wahl, weil sie ein echtes Problem von Bully löst.

### C) Fokus „Was kann schiefgehen?“

Kein neuer Algorithmus, sondern ein Fehler-Labor: Ihr zeigt gezielt Situationen, in denen Bully und Ring falsche Ergebnisse liefern (zwei Chefs, endlose Wahlen, hängender Ring) und erklärt, wie Raft das löst. Sehr lehrreich, aber weniger „eigenes Projekt“.

___

## Die Simulation

#Frage_M Ich wäre mit Python fine, es sei denn du möchtest eine andere Sprache nutzen

- **Technik:** Python, alles in einem Programm. Jeder Knoten ist ein Objekt, Nachrichten laufen über eine simulierte Warteschlange mit einstellbarer Verzögerung. Das ist viel einfacher als echte Netzwerkverbindungen und lässt sich wiederholbar abspielen.
- **Visualisierung:** Knoten als Kreise, Nachrichten als wandernde Punkte, der Chef farbig markiert (z. B. mit pygame oder einer kleinen Webseite). Das ist das Herzstück fürs Video.
- **Szenarien:**
    1. Der Chef fällt einfach aus.
    2. Zwei Knoten starten gleichzeitig eine Wahl.
    3. Nachrichten kommen stark verspätet an.
    4. Netzwerktrennung: Das Netz zerfällt in zwei Gruppen (z. B. 3 und 2 Knoten).
    5. Der alte Chef kommt nach der Wahl zurück.
- **Messgrößen:**

| Messgröße                           | Was sie zeigt                                     |
| ----------------------------------- | ------------------------------------------------- |
| Anzahl Nachrichten                  | Wie „teuer“ eine Wahl ist                         |
| Zeit bis zum neuen Chef             | Wie lange das System ohne Chef ist                |
| Höchste Anzahl gleichzeitiger Chefs | Ob der Algorithmus sicher ist (soll immer 1 sein) |

## Was wir programmieren und zeigen können

Eine Kommandozeile (CLI) reicht völlig aus. Diese sieben Bausteine lassen sich einzeln bauen und im Video vorführen:

1. **Interaktive Steuerung:** Befehle wie `start 5`, `kill 5`, `revive 5`, `delay 3 4 500` oder `partition 1,2,3 | 4,5`. Jede Nachricht erscheint als Logzeile, etwa `[2 -> 4] ELECTION`. So löst ihr live Ausfälle aus und zeigt, wie das System reagiert.
2. **Schritt-Modus:** Pro Enter-Taste wird genau eine Nachricht zugestellt. Damit lässt sich im Video jeder Schritt in Ruhe erklären.
3. **Echte Prozesse:** Jeder Knoten läuft in einem eigenen Terminalfenster und spricht über Sockets auf localhost. Wenn ihr den Leader mit Strg+C beendet und die anderen neu wählen, wirkt das im Video sehr greifbar.
4. **Benchmark-Modus:** 1000 zufällige Wahlen pro Algorithmus. Am Ende steht eine Tabelle mit Nachrichten, Dauer und der Anzahl der Fälle mit zwei Leadern.
5. **Best Case gegen Worst Case:** Bemerkt der höchste Knoten den Ausfall, braucht Bully nur etwa n Nachrichten. Bemerkt ihn der niedrigste, sind es etwa n² Nachrichten. Das zeigt, wie stark die Kosten schwanken.
6. **Flackernder Knoten:** Knoten 5 stürzt immer wieder ab und startet neu. Bei Bully reißt er jedes Mal die Leitung wieder an sich, und es gibt ständig neue Wahlen.
7. **Falscher Verdacht:** Der Leader ist nur langsam statt tot. Ist der Timeout zu kurz, wählen die anderen einen neuen Leader, obwohl der alte noch lebt.

Die Beispiele 5 bis 7 zeigen genau die Schwächen von Bully und passen deshalb gut als Vorlauf für eure eigene Variante.

## Wann ist Bully sinnvoll?

Bully passt am besten zu kleinen, stabilen Gruppen in einem zuverlässigen Netzwerk.

| Bully passt gut, wenn …                                                                                                 | Bully passt schlecht, wenn …                                               |
| ----------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| die Gruppe klein ist und alle Knoten sich kennen                                                                        | es viele Knoten gibt (bis zu n² Nachrichten pro Wahl)                      |
| das Netzwerk zuverlässig ist und man weiß, wie lange eine Nachricht höchstens braucht (dann funktionieren die Timeouts) | Nachrichten oft verspätet ankommen und Timeouts falschen Alarm auslösen    |
| Knoten selten und komplett ausfallen                                                                                    | das Netz in Teile zerfällt (dann gibt es zwei Leader)                      |
| die höchste ID auch wirklich der beste Leader ist, z. B. der stärkste Rechner                                           | ein Knoten mit hoher ID oft ausfällt und wiederkommt (ständig neue Wahlen) |

## Praxisbeispiele

- **Elasticsearch (bis Version 6):** Wählte den Master mit einem Bully-ähnlichen Verfahren („Zen Discovery“). Das führte zu Split Brain, darum gibt es seit Version 7 eine mehrheitsbasierte Wahl.
- **MongoDB (vor Version 3.2):** Die Wahl in Replica Sets bevorzugte Knoten nach Priorität, ähnlich wie Bully. Neuere Versionen nutzen ein Raft-ähnliches Protokoll.
- **etcd, Kubernetes, Consul:** Nutzen heute Raft.
- **Cassandra (z. B. bei Netflix):** Gegenbeispiel ganz ohne Leader. Jeder Knoten darf schreiben, Konflikte werden später aufgelöst.

Diese Angaben stammen aus dem Gedächtnis. Bitte prüft sie vor dem Video an der offiziellen Dokumentation oder dem Blog des jeweiligen Projekts und zitiert diese Quelle.

## Grober Ablauf des Videos (ca. 20 Minuten, Grenze sind 30)

1. **Einstieg (1 Min):** Alltagsbeispiel, etwa eine Lerngruppe, deren Organisator plötzlich nicht mehr antwortet. Wer übernimmt?
2. **Grundlagen (2,5 Min):** Knoten, Nachricht, Ausfall, Timeout, synchrones und asynchrones Modell. Mit Quellen auf der Folie.
3. **Einordnung ins Modul (1,5 Min):** Leader Election als Koordinationsproblem, Bezug zu Systemmodellen und Architekturen.
4. **Bully erklärt und live gezeigt (3 Min):** Erst an einer Skizze, dann in der CLI.
5. **Ring erklärt und live gezeigt (2,5 Min):** Gleiches Szenario, Unterschied bei Nachrichten und Dauer zeigen.
6. **Das Problem (2 Min):** Netzwerktrennung und falscher Verdacht live. Bei Bully entstehen zwei Leader. Das ist der Wendepunkt des Videos.
7. **Unsere Variante (3 Min):** Wie ihr auf die Idee gekommen seid, ein Fehlversuch, die Verbesserung.
8. **Der Vergleich (1,5 Min):** Tabelle aus dem Benchmark-Modus.
9. **Praxis (2 Min):** Elasticsearch und MongoDB als Bully-ähnliche Beispiele, Raft in etcd und Kubernetes, Cassandra ohne Leader.
10. **Fazit (0,5 Min):** Drei Sätze zum Mitnehmen und der Link zum Code.

## Quellen zum Zitieren

Ihr erstellt eure eigene Präsentation. „Mit Zitation“ heißt nur: Wo ihr Wissen, Definitionen oder Bilder aus einer Quelle übernehmt, gebt ihr sie an. Diese Quellen eignen sich dafür, bitte prüft die Angaben vor dem Zitieren selbst.

- H. Garcia-Molina: _Elections in a Distributed Computing System_. IEEE Transactions on Computers, 1982. Originalarbeit zu Bully.
- E. Chang, R. Roberts: _An Improved Algorithm for Decentralized Extrema-Finding in Circular Configurations of Processes_. Communications of the ACM, 1979. Originalarbeit zum Ring-Algorithmus.
- D. Ongaro, J. Ousterhout: _In Search of an Understandable Consensus Algorithm_. USENIX ATC, 2014. Die Raft-Arbeit, dazu [raft.github.io](https://raft.github.io).
- A. Tanenbaum, M. van Steen: _Distributed Systems_, Kapitel zur Koordination. Frei verfügbar auf [distributed-systems.net](https://www.distributed-systems.net).
- G. Coulouris u. a.: _Verteilte Systeme_, Kapitel zu Koordination und Wahl.
- Das Vorlesungsskript des Moduls, für die Einordnung.