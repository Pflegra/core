# Changelog

## v1.5.5 (20.06.2026)

### Neu

- Eigene Termine unter `/termine/`
- Optionale Personenzuordnung und Notiz
- Ganztägige Termine oder Zeitfenster mit `uhrzeit_von` und `uhrzeit_bis`
- Einmalige, tägliche, wöchentliche, monatliche und jährliche Wiederholung
- Integration in den bestehenden Pflege-Kalender

### Technisch

- DB Schema v23 mit neuer Tabelle `eigene_termine`
- Terminserien werden nur für den sichtbaren Monat berechnet und nicht einzeln gespeichert
- Alle Terminabfragen und Änderungen sind nach `owner_id` getrennt

---

## v1.5.4 (18.06.2026)

### Neu

- Pflege-Kalender `/kalender/`
  - Monatsansicht mit Navigation (vor/zurück, Heute)
  - Aggregiert eigene Fristen, Pflegeberatung, automatische Fristen, Dokumente und Tagebucheinträge
  - Personenfilter
  - Klickbare Einträge führen direkt zum jeweiligen Modul
  - Keine neue Datenbanktabelle, reine Aggregationsansicht über bestehende Daten

### Sicherheit

- Fix: `versicherte.person_name` war global `UNIQUE` statt `UNIQUE(person_name, owner_id)`. Dadurch konnten zwei Nutzer keine Person mit demselben Namen anlegen.
- Fix: `versicherter_loeschen` filterte nicht nach `owner_id` (potenzielle Cross-Tenant-Lücke)
- `SCHEMA_VERSION`-Konstante korrigiert (war 16, tatsächliche Migrationen reichten bis 21/22)

### Technisch

- DB Schema v22 (Migration der `versicherte`-Tabelle, kein Datenverlust)
- Neuer Service `kalender_service.py`
- Neuer Router `/kalender/`

---

## v1.5.3 (17.06.2026)

### Neu

- **Pflegetagebuch Chronik** — neue Chat-ähnliche Ansicht des Pflegetagebuchs
  - Schnelleingabe direkt in der Chronik (tippen + Strg+Enter)
  - Chronologische Darstellung mit Datum-Trennern
  - Tags, Stimmung und Kategorie sichtbar

### Verbessert

- Demo-Daten erweitert: Kontakte, Fristen, mehr Tagebucheinträge
- Eigene Fristen erscheinen jetzt auch in der Aufgaben-Übersicht
- Vollständige Übersetzung aller neuen Module (Navbar, Dashboard, Fristen, Kontakte, Chronik, Aufgaben)

---

## v1.5.2 (17.06.2026)

### Neu

- **Fristen & Termine** pro versicherter Person
  - Kategorien: Termin, Dokument/Ausweis, Antrag/Frist, Arzt/Therapie, Behörde/Amt, Sonstiges
  - Ampelfarben nach Dringlichkeit (rot/orange/gelb/grün)
  - Als erledigt markierbar
  - Button „📅 Fristen" direkt auf der Versicherten-Karte
- Dashboard zeigt eigene Fristen im Aufgaben-Banner und auf der Personenkarte

### Verbessert

- Navigation komplett umstrukturiert
  - Gruppen: Pflege, Personen, Organisation, Auswertungen, Verwaltung
  - „Pflegeeinsätze" statt „Einträge"
  - „🏠 Übersicht" als erster sichtbarer Punkt

### Technisch

- Neue Tabelle `eigene_fristen` (DB Schema v21)
- Neuer Router `/fristen/`

---

## v1.5.1 (16.06.2026)

### Neu

- Kontaktverwaltung pro versicherter Person
  - Kontakttypen: Hausarzt, Pflegekasse, Pflegedienst, Beratungsstelle, Sonstiger Kontakt
  - Felder: Name, Ansprechpartner, Telefon, E-Mail, Adresse, Kundennummer, Notiz
  - Direkter Aufruf per `tel:` und `mailto:` Links
  - Button „Kontakte" direkt auf der Versicherten-Karte im Dashboard
- Auto-Backup-Fix: Backup-Scheduler wird jetzt beim Containerstart automatisch gestartet
- Windows EXE: Logging-Fix für den Betrieb ohne Terminal

### Technisch

- Neue Tabelle `kontakte` (DB Schema v20)
- Neuer Router `/kontakte/`

---

## v1.5.0 (15.06.2026)

### Neu

- E-Mail-Benachrichtigungen für Fristen und Pflegeberatungen
- Web-Push-Benachrichtigungen (PWA, Beta)
- SMTP-Konfiguration für Administratoren
- Verlauf aller gesendeten Erinnerungen unter `/erinnerungen/verlauf`
- Pro Nutzer aktivierbar: E-Mail und/oder Push
- Vorlaufzeiten konfigurierbar: Pflegeberatung, Entlastungsbetrag, allgemeine Fristen
- Versandzeit einstellbar (Stunde)

### Technisch

- Neue Tabellen `erinnerungen_config`, `push_subscriptions`, `erinnerungen_log` (DB Schema v19)
- Neuer Router `/erinnerungen/`
- Neuer Service `erinnerungen_service.py`

---

## v1.4.1 (14.06.2026)

### Verbessert

- Dashboard komplett auf Versicherte fokussiert
- Statistik-Kacheln entfernt
- Aufgaben-Banner oben, gelb/orange/rot je nach Dringlichkeit
- Nächste Aufgabe direkt auf der Versicherten-Karte
- Letzte Aktivitäten in menschlicher Sprache
- Einzelperson wird automatisch zentriert
- PG-Badge, Aufgaben-Badge und Nächste-Aufgabe-Box klickbar

---

## v1.4.0 (13.06.2026)

### Neu

- Offene Aufgaben unter `/aufgaben/` mit Ampelfarben (rot/orange/gelb/grün)
- Zeitachse unter `/zeitachse/`: chronologische Übersicht aller Ereignisse
  - Quellen: Pflegeberatung, Pflegegradverlauf, Dokumente, Entlastungsbuchungen, Gutachten
  - Filter nach Person und Jahr
  - Klickbar zu jeweiligem Modul
- Dokumente- und Zeitachse-Button direkt auf der Versicherten-Karte
- Dashboard-Chip „Offene Aufgaben" mit Farbmarkierung

### Technisch

- Neuer Service `aufgaben_service.py`
- Neuer Service `fristen_service.py`
- Neue Router `/aufgaben/` und `/zeitachse/`

---

## v1.3.3 (12.06.2026)

### Neu

- Dokumentenarchiv pro versicherter Person
  - Kategorien: Gutachten, Pflegekasse, Pflegeberatung, Widerspruch, Arztbericht, Antrag, Sonstiges
  - Upload, Download, Löschen
- Dashboard überarbeitet: Versicherte prominent oben, Pflegeberatungs-Kachel, Nächste-Aktion-Banner
- Fristen als Info-Tooltip

### Technisch

- Neue Tabelle `dokumente` (DB Schema v18)
- Neuer Router `/dokumente/`

---

## v1.3.2 (11.06.2026)

### Neu

- Pflegeberatung nach § 37.3 SGB XI
  - Dokumentation von Beratungsterminen mit Nachweis-Upload
  - Automatische Fristberechnung (halbjährlich, ab 2026 für PG 2–5)
  - Anbieter-Dropdown: Pflegedienst, Pflegeberatung, Sonstige
  - Nachweis-Download und Löschen

### Technisch

- Neue Tabelle `pflegeberatung` (DB Schema v17)
- Neuer Router `/pflegeberatung/`

---

## v1.3.1 (10.06.2026)

### Neu

- Login mit `next`-Parameter: Redirect nach Login zur ursprünglichen Seite
- Route `/gutachten/neueste` für direkten Aufruf des letzten Gutachtens
- Feedback-Button in der App
- Dashboard: Gutachten-Kachel, Labels „Versicherte" und „Std. Pflege"

### Verbessert

- Demo-Account und Website aktualisiert
- Gutachten-Screenshot auf der Website prominent platziert

---

## v1.3.0 (09.06.2026)

### Neu

- PWA-Unterstützung: Manifest mit Shortcuts, Service Worker, Offline-Fallback
- PWA-Installationsbanner mit 7-Tage-Ausblendung
- Touch-UI: Pflegegrad-Buttons optimiert für mobile Geräte
- Dropdown-Pfeil für mobile Menüs

---

## v1.2.1 (08.06.2026)

### Sicherheit

- Backup und Wiederherstellung sind jetzt vollständig auf Administratoren beschränkt
- Der Menüpunkt für Backups wird nur noch Administratoren angezeigt

### Neu

- Nutzungsstatistik im Bereich „Admin & Systemstatus"
  - Logins heute und diese Woche
  - Fehlgeschlagene Anmeldungen
  - Anzahl der Gutachten-Analysen
  - Aktive und registrierte Benutzer
- Gutachten-Analysen werden jetzt zusätzlich im Audit-Log erfasst

## v1.2.0 (07.06.2026)

### Neu

- Gutachten-Analyse für MD- und MDK-Gutachten
- PDF-Dateien können direkt hochgeladen und ausgewertet werden
- Erkennung von Pflegegrad, Gesamtpunkten und den Bewertungen aller sechs Module
- Erkennung von Gutachtentyp, Datum und Diagnosen
- Unterstützung für gescannte PDFs durch OCR (Tesseract)
- Anzeige der Analysequalität für die erkannten Daten
- Analyseergebnisse werden benutzerbezogen gespeichert und können jederzeit erneut aufgerufen werden
- Maximale Dateigröße für Uploads: 50 MB

## v1.1.0 (05.06.2026)

### Neu

- Benutzervertretung: Administratoren können sich temporär als anderer Benutzer anmelden
- Audit-Log für Anmeldungen, Benutzerverwaltung und Benutzervertretung
- Windows-Version überarbeitet
  - Kein Konsolenfenster mehr
  - Tray-Symbol integriert
  - Schutz vor mehrfach gestarteten Instanzen
- Unterstützung für eine lokale `.env`-Datei zur Konfiguration des Datenverzeichnisses

### Behoben

- Fehler bei der Benutzervertretung behoben, wodurch Daten teilweise dem falschen Benutzer zugeordnet werden konnten

## v1.0.0 (04.06.2026)

Erste stabile Version von Pflegra.

### Enthaltene Funktionen

- Verwaltung von Verhinderungs- und Kurzzeitpflege
- Budgetverwaltung mit Jahresübersicht und Prognose
- Pflegegradrechner nach § 15 SGB XI
- Leistungsfinder für Pflegeleistungen
- Verwaltung des Entlastungsbetrags
- PDF-Exporte für Nachweise, Berichte und Schreiben
- Verwaltung von Ersatzpflegekräften
- Mehrbenutzerbetrieb mit Rollen und Datentrennung
- Integriertes Demo-System
- Deutsche und englische Oberfläche
- Automatische Backups
- Fernzugriff über Tailscale
- Docker-Unterstützung für amd64 und arm64
- Windows-Schnellstart
