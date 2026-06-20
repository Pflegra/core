# Pflegra Mobile-First UX-Konzept

**Status:** Verbindliche UX-Leitlinie für neue Funktionen und den schrittweisen Umbau bestehender Oberflächen  
**Stand:** 20.06.2026  
**Bewertete Basis:** Pflegra v1.5.6, vorhandene Templates und responsive Regeln

## Ausgangslage

Pflegra ist bereits grundsätzlich responsiv. Die Navigation wechselt auf kleinen Bildschirmen in ein mobiles Menü, Formreihen werden teilweise einspaltig und Standardbuttons erhalten mobil eine Mindesthöhe von 44 Pixeln. Mehrere neuere Bereiche, etwa eigene Termine, Fristen, Dokumente und Tagebuch, nutzen bereits Karten statt breiter Tabellen.

Die Oberfläche ist dennoch überwiegend vom Desktop her gedacht. Besonders Monatskalender, Pflegeeinträge, lange Formulare und dichte Detailansichten übertragen Desktopstrukturen auf kleine Bildschirme. Horizontales Scrollen, kleine Nebenaktionen und lange Seiten erschweren die Nutzung unterwegs.

Die Bewertung in diesem Dokument ist eine Quellcode- und Template-Prüfung. Sie ersetzt keine Tests mit pflegenden Angehörigen auf realen Geräten.

## Mobile-First Prinzip

Neue Funktionen werden künftig zuerst für Smartphone und Tablet entworfen und geprüft. Desktop ist eine Erweiterung dieser Grundlage, nicht mehr deren Ausgangspunkt.

Verbindliche Reihenfolge:

1. Aufgabe und wichtigsten Nutzungsmoment bestimmen.
2. Smartphone-Ablauf für 360 bis 430 Pixel Breite entwerfen.
3. Touch-Bedienung, Informationshierarchie und Fehlerfälle prüfen.
4. Tablet-Ansicht für 768 bis 1024 Pixel ergänzen.
5. Erst danach Platz und Zusatzinformationen für Desktop nutzen.

Eine Funktion gilt erst als fertig, wenn ihr Hauptablauf ohne horizontales Scrollen, präzise Fingertipps oder unnötige Zwischenschritte auf einem Smartphone möglich ist.

## Zielgruppe

Pflegra richtet sich besonders an pflegende Angehörige. Diese arbeiten häufig unter Zeitdruck, mit nur einer freien Hand, unter wechselnden Licht- und Netzbedingungen und mit begrenzter Aufmerksamkeit. Die Oberfläche muss deshalb verständlich sein, ohne dass Abläufe erlernt oder Informationen im Kopf behalten werden müssen.

Weitere relevante Gruppen sind:

- Familienmitglieder, die einzelne Aufgaben übernehmen
- Pflegepersonen mit wenig technischer Erfahrung
- Nutzerinnen und Nutzer mit Seh-, Motorik- oder Konzentrationseinschränkungen
- Personen, die Pflegra abwechselnd auf Smartphone, Tablet und Desktop verwenden

## Mobile Nutzungsszenarien

- Beim Arzt einen Termin oder eine Frist sofort erfassen
- In einer Wartesituation Aufgaben und nächste Termine prüfen
- Nach einem Telefonat eine kurze Notiz ins Tagebuch schreiben
- Während der Pflege einen Pflegeeintrag mit wenigen Eingaben anlegen
- Einen Bescheid direkt vom Smartphone fotografieren oder hochladen
- In Schule, Therapie oder Beratungsstelle ein Dokument wiederfinden
- Abends auf dem Sofa Kalender, Chronik oder offene Aufgaben überblicken
- Auf dem Tablet längere Gutachten und Verläufe prüfen

## Bewertungsmaßstab

- **Gut:** Der Hauptablauf ist mobil realistisch und ohne grundlegenden Umbau nutzbar.
- **Bedingt:** Der Ablauf funktioniert, benötigt aber gezielte mobile Verbesserungen.
- **Kritisch:** Die Desktopstruktur behindert den mobilen Hauptablauf deutlich.

Geprüft werden Nutzbarkeit, Touch-Ziele, Informationsmenge, Tabellen, Scrollaufwand, mobile Eingabe und Bedienfallen.

## Bewertung aktueller Module

### Dashboard - bedingt

- **Nutzbarkeit:** Personenkarten werden mobil einspaltig; wichtige Informationen sind grundsätzlich erreichbar.
- **Touch-Ziele:** Standardaktionen sind ausreichend groß. Die vielen kleinen Schnellaktionen konkurrieren jedoch miteinander.
- **Informationsmenge:** Pflegegrad, Budget, Aufgaben, Termine, zahlreiche Links und letzte Aktivitäten erzeugen eine lange Karte und eine lange Gesamtseite.
- **Tabellen:** Keine zentrale Tabellenhürde.
- **Scrollaufwand:** Bei mehreren Versicherten und Aktivitäten hoch.
- **Unterwegs:** Überblick ist realistisch, die nächste relevante Aktion ist aber nicht immer eindeutig.
- **Bedienfallen:** Zu viele gleich gewichtete Aktionen; wichtige und seltene Funktionen sehen ähnlich aus.
- **Priorität:** Hoch. Pro Person zuerst Status und zwei bis vier häufige Aktionen zeigen, weitere Aktionen nachrangig zugänglich machen.

### Kalender - kritisch

- **Nutzbarkeit:** Der Monatskalender besitzt eine Mindestbreite von 640 Pixeln und wird mobil horizontal gescrollt.
- **Touch-Ziele:** Ereignisse sind mit sehr kleiner Schrift und engem Innenabstand schwer zuverlässig zu treffen.
- **Informationsmenge:** Sieben Spalten, Legende und mehrere Ereignisarten sind auf einem Smartphone zu dicht.
- **Tabellen:** Die Monatsansicht ist eine breite Tabelle und damit die größte mobile Hürde.
- **Scrollaufwand:** Horizontal und vertikal; der Zusammenhang zwischen Datum und Ereignis kann verloren gehen.
- **Unterwegs:** Schnelles Prüfen des heutigen oder nächsten Termins ist unnötig aufwendig.
- **Bedienfallen:** Abgeschnittene Titel und „weitere“-Hinweise verbergen relevante Inhalte.
- **Priorität:** Sehr hoch. Mobil eine Termin- beziehungsweise Agendaansicht als primäre Darstellung verwenden; die Monatsmatrix bleibt für Tablet und Desktop verfügbar.

### Eigene Termine - gut mit Verbesserungsbedarf

- **Nutzbarkeit:** Die Liste verwendet Karten und ist mobil gut erfassbar.
- **Touch-Ziele:** Hauptaktion ist groß genug; Bearbeiten und Löschen verwenden kleine Sekundärbuttons.
- **Informationsmenge:** Titel, Person, Datum, Zeit und Wiederholung sind sinnvoll gebündelt. Lange Notizen können Karten verlängern.
- **Tabellen:** Keine.
- **Scrollaufwand:** Bei vielen wiederkehrenden Terminen mittel bis hoch; Filterung ist vorhanden.
- **Unterwegs:** Eintragen ist realistisch und fachlich passend.
- **Bedienfallen:** Datum/Wiederholung und Von/Bis stehen über Inline-Grids nebeneinander, die nicht ausdrücklich mobil einspaltig werden. Löschen ist als Symbol wenig selbsterklärend.
- **Priorität:** Hoch. Formular mobil einspaltig, Aktionen mindestens 44 Pixel und Primäraktion am Formularende eindeutig halten.

### Fristen - gut mit Verbesserungsbedarf

- **Nutzbarkeit:** Karten, Ampelfarbe und Fälligkeit unterstützen den schnellen Überblick.
- **Touch-Ziele:** Erledigen, Bearbeiten und Löschen sind kleine, eng stehende Nebenaktionen.
- **Informationsmenge:** Wesentliche Angaben sind sichtbar; Notizen können die Liste verlängern.
- **Tabellen:** Keine.
- **Scrollaufwand:** Angemessen, solange erledigte Fristen standardmäßig ausgeblendet bleiben.
- **Unterwegs:** Prüfen und Erfassen sind realistisch.
- **Bedienfallen:** Reine Symbolaktionen sind verwechslungsanfällig; Datum und Kategorie stehen im Formular in einem festen Zweispalten-Grid.
- **Priorität:** Hoch. Kartenaktionen vergrößern, destruktive Aktion absetzen und Formular mobil einspaltig darstellen.

### Aufgaben - bedingt

- **Nutzbarkeit:** Die Aufgabenliste ist kompakt, farblich priorisiert und ohne Tabelle aufgebaut.
- **Touch-Ziele:** Der Pfeil zur Zielseite ist eine kleine Sekundäraktion und erklärt sein Ziel nur durch Kontext.
- **Informationsmenge:** Titel, Person, Fälligkeit und Hinweis sind angemessen.
- **Tabellen:** Keine.
- **Scrollaufwand:** Bei vielen automatisch erzeugten Aufgaben hoch; Filter oder Gruppierung fehlen in der Ansicht.
- **Unterwegs:** Prüfen ist gut möglich, Bearbeitung erfolgt jedoch indirekt auf der jeweiligen Quellseite.
- **Bedienfallen:** Farbe und Emoji dürfen nicht die einzigen Bedeutungsträger sein; der Zielpfeil ist wenig beschreibend.
- **Priorität:** Mittel bis hoch. Lesbare Statusbezeichnung und klar beschriftete Zielaktion vorsehen.

### Pflegeeinträge - kritisch

- **Nutzbarkeit:** Die Liste bleibt eine Datentabelle. Mobil werden mehrere Spalten ausgeblendet, der verbleibende Inhalt bleibt dicht.
- **Touch-Ziele:** Icon-Aktionen werden mobil vergrößert; Checkboxen und Tabelleninteraktion bleiben anspruchsvoll.
- **Informationsmenge:** Sortierung, Filter, Suche, Mehrfachauswahl und viele Spalten überfrachten die mobile Ansicht.
- **Tabellen:** Ja. Zusätzlich liegt die Tabelle in einem eigenen, auf 60 Prozent der Viewport-Höhe begrenzten Scrollbereich.
- **Scrollaufwand:** Verschachteltes Scrollen und horizontale Restbreite können Orientierung kosten.
- **Unterwegs:** Neuer Eintrag ist möglich, das Formular ist jedoch lang. Optionale Ersatzpflegeangaben sind bereits einklappbar.
- **Bedienfallen:** Tabellenkopf, Bulk-Auswahl und Seiten-Scroll konkurrieren; wichtige ausgeblendete Werte sind mobil nicht direkt sichtbar.
- **Priorität:** Sehr hoch. Mobile Kartenliste mit Datum, Person, Dauer und Hauptaktion; Detaildaten bei Bedarf öffnen. Schnelleingabe vor Verwaltungsfunktionen priorisieren.

### Tagebuch und Chronik - gut

- **Nutzbarkeit:** Karten und chronologische Darstellung passen gut zum Smartphone.
- **Touch-Ziele:** Standardaktionen sind brauchbar; kleine Bearbeiten-/Löschen-Symbole und Stimmungsoptionen sollten geprüft werden.
- **Informationsmenge:** Einträge sind natürlich lesbar, lange Texte führen erwartbar zu Scrollen.
- **Tabellen:** Keine.
- **Scrollaufwand:** Fachlich angemessen; Filter und klare Datumsgruppen unterstützen Orientierung.
- **Unterwegs:** Die Schnelleingabe in der Chronik ist ein gutes Mobile-First-Muster.
- **Bedienfallen:** Die Aktionssymbole sind knapp beschriftet; das vollständige Formular kann gegenüber der Schnelleingabe schwerer wirken.
- **Priorität:** Mittel. Schnelleingabe als Referenzmuster erhalten, Touch-Ziele und Aktionsbeschriftungen vereinheitlichen.

### Dokumente - gut mit Verbesserungsbedarf

- **Nutzbarkeit:** Dokumente werden als Karten beziehungsweise Galerie dargestellt; Filter umbrechen.
- **Touch-Ziele:** Download und Löschen nutzen kleine Sekundärbuttons.
- **Informationsmenge:** Metadaten sind überschaubar; lange Titel werden gekürzt.
- **Tabellen:** Keine zentrale Tabellenhürde.
- **Scrollaufwand:** Bei großen Archiven hoch; Personen- und Kategoriefilter helfen.
- **Unterwegs:** Upload über die Dateiauswahl ist realistisch. Auswahl, Titelvergabe und Kategorie sollten in einem kurzen Ablauf bleiben.
- **Bedienfallen:** Gekürzte Titel können ähnliche Dokumente ununterscheidbar machen; Löschen liegt nah bei Download.
- **Priorität:** Hoch. Dokumentaktion als große Zeile oder Aktionsmenü, vollständigen Titel zugänglich halten und Uploadformular mobil klar staffeln.

### Gutachtenanalyse - bedingt

- **Nutzbarkeit:** Uploadfelder umbrechen und Ergebniskennzahlen nutzen responsive Karten. Detailauswertungen bleiben inhaltlich dicht.
- **Touch-Ziele:** Hauptaktion ist ausreichend, kleine Anzeigen- und Löschen-Aktionen sind knapp.
- **Informationsmenge:** Analyseergebnisse enthalten viele Werte und Erläuterungen; auf Smartphones fehlt eine klare Reihenfolge aus Ergebnis, Auffälligkeiten und Details.
- **Tabellen:** Keine zentrale breite Tabelle, aber viele dichte Ergebnisblöcke.
- **Scrollaufwand:** Hoch und fachlich teilweise unvermeidbar.
- **Unterwegs:** PDF hochladen ist möglich; sorgfältige Auswertung eignet sich eher für Tablet oder Desktop.
- **Bedienfallen:** Lange Verarbeitung braucht eindeutigen Status; wichtige Abweichungen dürfen nicht zwischen Detailwerten untergehen.
- **Priorität:** Mittel. Mobile Zusammenfassung zuerst, Details anschließend; Upload und Analysezustand klar und robust darstellen.

### Einstellungen - kritisch für Bearbeitung, ausreichend zum Nachsehen

- **Nutzbarkeit:** Ein langes Formular bündelt Pflegedienst, Absender, Finanzen, Pfade, Passwort und Systeminformationen.
- **Touch-Ziele:** Standardfelder sind mobil ausreichend groß.
- **Informationsmenge:** Sehr hoch; seltene technische Angaben stehen im selben Ablauf wie persönliche Einstellungen.
- **Tabellen:** Systeminformationen verwenden eine Tabelle, die wegen zweier Spalten noch handhabbar ist.
- **Scrollaufwand:** Sehr hoch; Speichern liegt erst nach vielen Feldern.
- **Unterwegs:** Kleine Änderungen sind möglich, aber fehleranfällig und schwer zu kontrollieren.
- **Bedienfallen:** Ein globaler Speichervorgang für mehrere Themen; technische Pfade können versehentlich verändert werden.
- **Priorität:** Mittel. Einstellungen in klar benannte Abschnitte gliedern und pro Abschnitt Änderung und Speicherung nachvollziehbar machen.

## Verbindliche Mobile-UX-Regeln

### Layout und Informationshierarchie

1. Kein horizontaler Seiten-Scroll im Hauptablauf.
2. Breite Tabellen werden mobil zu Karten, Listen oder einer fokussierten Detailansicht.
3. Inhalte werden nach Aufgabe priorisiert: Status, nächste Aktion, Details.
4. Sekundäre Metadaten dürfen eingeklappt werden, zentrale Daten nicht.
5. Smartphone nutzt grundsätzlich eine Spalte. Zwei Spalten sind nur für sehr kurze, logisch gekoppelte Felder zulässig, wenn 360 Pixel getestet sind.
6. Tablet erhält eigene Zwischenlayouts; es ist weder großes Smartphone noch kleiner Desktop.

### Aktionen und Touch

1. Interaktive Ziele sind mindestens 44 mal 44 Pixel groß.
2. Zwischen destruktiven und häufigen Aktionen liegt ausreichend Abstand.
3. Primäre Aktionen sind als Text beschriftet; Symbole allein sind nur für allgemein eindeutige Funktionen zulässig.
4. Pro Ansicht gibt es eine klar erkennbare Primäraktion.
5. Die Primäraktion steht oben und bei langen Formularen zusätzlich deutlich am Ende. Sticky-Aktionen sind nur zulässig, wenn sie keine Inhalte oder Systemnavigation verdecken.
6. Hover darf nie Voraussetzung für Information oder Bedienung sein.

### Formulare und schnelle Eingabe

1. Zuerst werden nur Pflichtfelder und häufige Angaben gezeigt.
2. Optionale Fachdetails werden sinnvoll gruppiert und bei Bedarf aufgeklappt.
3. Eingabetypen passen zum Inhalt: Datum, Zeit, Zahl, E-Mail und Datei verwenden passende native Controls.
4. Eingabefelder verwenden mobil mindestens 16 Pixel Schriftgröße, damit iOS nicht automatisch zoomt.
5. Vorauswahlen aus Person, Datum und Kontext werden genutzt, wenn sie eindeutig sind.
6. Validierungsfehler stehen direkt am Feld und zusätzlich verständlich am Formularanfang.
7. Nach dem Speichern wird Ergebnis und nächster sinnvoller Schritt klar bestätigt.
8. Schnelle Eingabe hat Vorrang vor vollständiger Detailpflege; Details bleiben nachträglich bearbeitbar.

### Navigation und Orientierung

1. Häufige mobile Ziele sind mit höchstens zwei Interaktionen erreichbar.
2. Menüs haben keine unnötig tiefen oder mehrfach verschachtelten Dropdowns.
3. Seitentitel, ausgewählte Person und aktueller Zeitraum bleiben eindeutig.
4. Zurück-Navigation darf keine eingegebenen Daten überraschend verwerfen.
5. Lange Listen behalten Filterzustand und sinnvolle Rückkehrposition, soweit technisch verlässlich möglich.
6. Kalender wird mobil als eigener Nutzungskontext gestaltet, nicht nur verkleinert.

### Listen, Karten und Tabellen

1. Eine mobile Karte zeigt höchstens die wichtigsten drei bis fünf Informationen direkt.
2. Die gesamte Karte darf zur Detailansicht führen, sofern darin keine konkurrierenden Aktionen liegen.
3. Filter starten kompakt und zeigen aktive Filter sichtbar an.
4. Tabellen bleiben nur erhalten, wenn Spaltenvergleich die Kernaufgabe ist. Dann braucht es eine bewusst reduzierte mobile Variante.
5. Verschachtelte vertikale Scrollbereiche werden vermieden.
6. Leere Zustände erklären kurz, was als Nächstes möglich ist.

### Rückmeldung und Barrierefreiheit

1. Status wird nie ausschließlich durch Farbe vermittelt.
2. Fokusreihenfolge, sichtbarer Tastaturfokus und semantische Beschriftungen bleiben erhalten.
3. Text und Bedienelemente erfüllen mindestens WCAG 2.2 AA als Zielstandard.
4. Lade-, Upload- und Analysezustände sind sichtbar und verständlich.
5. Fehlermeldungen sagen, was passiert ist und wie die Person fortfahren kann.
6. Bewegungen und Layoutänderungen dürfen keine unerwarteten Sprünge auslösen.

## Priorisierte Maßnahmenliste

### P0 - gemeinsame Grundlage

- Mobile Definition of Done in Beitrags- und Reviewprozess aufnehmen
- Prüfraster für 360, 390, 430, 768 und 1024 Pixel festlegen
- Touch-Ziele aller kleinen Buttons, Icon-Aktionen, Checkboxen und Menüelemente erfassen
- Wiederverwendbare Muster für mobile Karten, Aktionszeilen, Filter und Formularaktionen definieren
- Keine neuen breiten Tabellen oder festen Zweispalten-Grids ohne mobile Alternative zulassen

### P1 - wichtigste Unterwegs-Abläufe

- Kalender mobil als Agenda mit Heute/Nächste Tage denken
- Pflegeeinträge mobil als Kartenliste statt Tabelle konzipieren
- Formulare für Termine, Fristen und Pflegeeinträge konsequent einspaltig machen
- Primäraktionen auf Dashboard, Kalender und Listen klar priorisieren
- Kleine Bearbeiten-, Erledigen-, Download- und Löschen-Aktionen auf 44 Pixel anheben

### P2 - Informationsdichte und Langseiten

- Dashboard-Aktionen nach Häufigkeit ordnen und seltene Aktionen nachrangig zeigen
- Aufgaben mit verständlicher Zielaktion und textlichem Status versehen
- Dokumentkarten für lange Titel und sichere Aktionsabstände optimieren
- Gutachten mobil in Zusammenfassung und Details gliedern
- Einstellungen in fachliche Abschnitte teilen und Speichern verständlicher machen

### P3 - Qualitätssicherung

- Tests auf iPhone Safari und Android Chrome in Portrait und Landscape
- Tablet-Tests auf iPadOS Safari und Android Chrome
- Bedienung mit 200 Prozent Textvergrößerung und externer Tastatur prüfen
- Hauptabläufe mit pflegenden Angehörigen beobachten
- Mobile Regressionen in Release-Checkliste aufnehmen

## Vorschlag für den v1.6.x Mobile-First Umbau

### v1.6.0 - Fundament und Kernabläufe

- Gemeinsame mobile Komponenten und Abnahmekriterien festlegen
- Kalender-Agenda für Smartphone konzipieren und umsetzen
- Pflegeeintragsliste mobil auf Karten umstellen
- Touch-Ziele und einspaltige Formulare für Termine, Fristen und Pflegeeinträge vereinheitlichen
- Dashboard auf Status und häufigste Aktionen fokussieren

### v1.6.1 - Unterwegs erfassen und organisieren

- Aufgaben, Fristen und Termine als einheitliche mobile Kartenfamilie ausarbeiten
- Dokumentupload und Dokumentaktionen für Smartphone optimieren
- Tagebuch-Schnelleingabe als Muster für weitere kurze Eingaben nutzen
- Filter und Rückkehrverhalten langer Listen vereinheitlichen

### v1.6.2 - Tiefe Inhalte und Tablet

- Gutachtenanalyse mit mobiler Zusammenfassung und gestaffelten Details überarbeiten
- Einstellungen in verständliche Abschnitte gliedern
- Tablet-Layouts für Kalender, Dokumente, Chronik und Gutachten gezielt ausarbeiten
- Barrierefreiheits- und Gerätetests über alle Kernmodule abschließen

Die Versionszuordnung beschreibt eine empfohlene Reihenfolge. Vor jeder Umsetzung werden Umfang und Akzeptanzkriterien separat freigegeben.

## Abnahmekriterien für neue Funktionen

Eine neue oder wesentlich geänderte Funktion erfüllt die Mobile-First-Leitlinie, wenn:

- der Hauptablauf bei 360 Pixel Breite ohne horizontalen Seiten-Scroll funktioniert,
- alle wesentlichen Touch-Ziele mindestens 44 mal 44 Pixel groß sind,
- die Primäraktion ohne Suche erkennbar ist,
- Formulare auf dem Smartphone logisch und möglichst einspaltig aufgebaut sind,
- keine Information ausschließlich über Farbe, Hover oder Symbol vermittelt wird,
- Smartphone und Tablet mit realistischen Datenmengen geprüft wurden,
- iPhone Safari und Android Chrome den Hauptablauf ohne Bedienfalle ermöglichen,
- Desktop-Funktionen und Tastaturbedienung erhalten bleiben.

## Nicht-Ziele dieses Dokuments

- Kein vollständiger App-Umbau in einem Release
- Keine Änderung von Datenmodell oder Fachlogik
- Keine neuen Fachfunktionen
- Keine Festlegung eines visuellen Redesigns
- Keine Ablösung der Desktop-Oberfläche

Dieses Dokument legt die UX-Richtung und Prüfmaßstäbe fest. Konkrete Implementierungen benötigen weiterhin einen klar abgegrenzten Auftrag.
