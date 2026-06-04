# Changelog

All notable changes to Pflegra are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v47z2] – 2026-06-01

### Changed
- Dashboard: PG-Karte optisch aufgewertet
  - Pflegegrad als Hauptinformation (groß, farbig), nicht als Überschrift
  - Punkte und Datum klar getrennt
  - Drei Buttons: Leistungen anzeigen (primary), Neu berechnen, Verlauf
- Dashboard: Leistungsvorschau-Block neben PG-Karte
  - Top-4 monatliche Leistungen direkt vom letzten gespeicherten Pflegegrad
  - Direktlink in Leistungsfinder vorausgefüllt
- Dashboard: Hinweis-Box Layout verbessert (Leistung + Person getrennt)

---

## [v47z1] – 2026-05-31

### Added
- Pflegegradrechner: Weiterführen-Block nach Berechnung
  - Grüne Box mit kontextabhängigen Folge-Links
  - 💶 Leistungsfinder direkt mit berechnetem PG vorausgefüllt (?pg=X)
  - Budgetplanung, Entlastungsbetrag, Pflegeeintrag anlegen
- Leistungsfinder: übernimmt ?pg=X aus URL automatisch und berechnet sofort
- Dashboard: Pflegegrad-Box (letzter Verlaufs-Eintrag) + Hinweis auf nicht genutzte Leistungen

---

## [v47z0] – 2026-05-31

### Added
- Leistungsfinder (`/leistungsfinder/`)
  - Eingaben: Pflegegrad (0–5), Setting (häuslich/stationär), Leistungsart (Pflegegeld/Sachleistung/Kombination)
  - Ausgabe: monatliche, jährliche und einmalige Leistungen mit Betrag, Paragraph, Erklärung
  - Kombinationshinweise (VP+KZP gemeinsamer Topf, Tagespflege-Zusatz, anteiliges Pflegegeld)
  - Gesamtsummen monatlich + jährlich
  - Auto-Berechnung beim Laden, Live-Update bei Auswahländerung
  - Direktlinks zu Pflegegradrechner, Budgetplanung, Entlastungsbetrag
  - `leistungsfinder.py` — `berechne_leistungen()` mit `LeistungsfinderErgebnis`
  - i18n DE/EN, Navbar-Eintrag 💶

---

## [v46z8] – 2026-05-31

### Fixed
- PDF-Download: kein leerer zweiter Tab mehr — fetch+blob statt form target="_blank"
- Verlauf speichern: Antworten werden zentral in `window._pgAktuelleFD` gehalten, kein doppeltes hidden-inputs-Befüllen

### Added
- Pflegegrad-Verlauf (`/pflegegrad/verlauf`)
  - DB-Schema v14: Tabelle `pflegegrad_verlauf` mit owner_id, person, datum, pflegegrad, gesamtpunkte, notiz, antworten_json
  - `db/pflegegrad_verlauf.py` — `PflegegradEintrag` + `PflegegradVerlaufRepo`
  - `PflegraDB` um `pg_verlauf_*`-Methoden erweitert
  - Nach Berechnung: „💾 Einschätzung speichern" mit Person + Notiz-Feld
  - Verlaufsseite: Tabelle aller Einschätzungen mit PG-Badge, Lösch-Button, Person-Filter
  - Diagramm (Chart.js) sobald mind. 2 Einträge vorhanden
  - Navbar: 📈 Verlauf-Link ergänzt
  - Migration erfolgt automatisch beim Start

---

## [v46z7] – 2026-05-31

### Changed
- PDF-Ergebnisbericht: Leistungsübersicht ergänzt
  - Alle verfügbaren (✓) und nicht verfügbaren (✗) Leistungen nach SGB XI
  - Betrag, Einheit und Paragraph je Leistung
  - Fußnote mit Jahreszahl und Vollständigkeitshinweis

---

## [v46z6] – 2026-05-31

### Added
- Pflegegradrechner: Leistungsübersicht nach SGB XI
  - `leistungen_fuer_pflegegrad()` in `pflege_rules.py` — nutzt bestehende Regelwerk-Engine
  - 11 Leistungen abgedeckt: Pflegegeld, Sachleistungen, VP, KZP, Tagespflege, Entlastungsbetrag, Hilfsmittel, Wohnumfeld, DiPA, Wohngruppe, Vollstationär
  - ✓/✗ je nach Pflegegrad, mit Betrag, Paragraph und Alltagserklärung
  - GET `/pflegegrad/leistungen/{pflegegrad}` — JSON-API
  - Ergebnis-Panel: Leistungsraster direkt nach Berechnung, responsives 2-Spalten-Grid
  - 6 neue Tests (52 gesamt, alle grün)

---

## [v46z5] – 2026-05-31

### Added
- Pflegegradrechner: PDF-Ergebnisbericht (`/pflegegrad/pdf`)
  - `exportiere_pflegegrad_pdf()` in `pdf_export.py` (reportlab, gleiche Design-Tokens)
  - Inhalt: Pflegegrad-Badge, Gesamtpunkte, Begründung, Haupttreiber-Tabelle, Modulübersicht, Dokumentations-Tipps, Orientierungshinweis
  - Versicherter + Absender aus User-Settings
  - Button „📄 Ergebnisbericht als PDF" erscheint nach Berechnung
  - PDF-Formular wird mit aktuellen Antworten befüllt (kein zweites Abschicken nötig)

---

## [v46z4] – 2026-05-31

### Changed
- Pflegegradrechner: Ergebnis-Panel ausgebaut
  - **Haupttreiber**: Top-3 Module mit Icon, Punktzahl und Schweregrad
  - **Dokumentations-Tipps**: modulspezifische Hinweise für das Pflegetagebuch
  - Direktlink „Jetzt Pflegeeintrag anlegen →" im Ergebnis
  - Haupttreiber und Doku-Tipps nur sichtbar wenn relevant (PG > 0)
- `RechnerErgebnis` um `haupttreiber` und `dokumentations_tipps` erweitert
- 46/46 Tests weiterhin grün

---

## [v46z3] – 2026-05-31
  - Neues `hilfe`-Feld in `Kriterium`-Dataclass
  - Jedes Kriterium hat eine alltagssprachliche Erklärung (ℹ️-Button, aufklappbar)
  - Grüner Hinweiskasten, schließt sich beim Zurücksetzen

### Added
- `tests/test_pflegegrad_rechner.py` — 46 Tests (alle grün)
  - Grenzwerte PG0–PG5 exakt geprüft (12,5 / 27,0 / 47,5 / 70,0 / 90,0 Punkte)
  - Modul 2+3 Kombinationslogik: max(), nicht Summe/Durchschnitt
  - Gewichtungstabellen alle Module parametrisiert
  - Dokumentiert: 70,0 Punkte mit NBA-Stufentabelle nicht exakt erreichbar (67,5 → PG3, 71,25 → PG4)

---

## [v46z2] – 2026-05-31

### Added
- Pflegegradrechner (NBA) — `pflegegrad_rechner.py` + Router `/pflegegrad/` + Template
  - Alle 6 NBA-Module mit 53 Kriterien vollständig implementiert (§ 15 SGB XI)
  - Gewichtungslogik nach MDS-Begutachtungsrichtlinien: M4=40%, M5=20%, M2+M3 kombiniert=15%, M1=10%, M6=15%
  - Live-Punktzahl-Update während der Eingabe (JS)
  - Ergebnis-Panel mit Pflegegrad-Badge, Gesamtpunkten, Modulübersicht und Begründungstext
  - Hinweise je nach Ergebnis (Beantragung, VP/KZP-Anspruch, Pflegestützpunkt)
  - i18n DE/EN komplett
- Navbar: 🧮 Pflegegradrechner im User-Dropdown ergänzt

---

## [v46z1] – 2026-05-31

### Changed
- `models.py` split into domain modules under `db/`:
  - `db/schema.py` — `DbSchema` (connection + migration)
  - `db/eintraege.py` — `PflegeEintrag`, `EintragsRepo`, constants
  - `db/personen.py` — `PersonenRepo`
  - `db/versicherte.py` — `Versicherter`, `VersicherterRepo`
  - `db/users.py` — `User`, `UserRepo`
  - `db/ersatzpflege.py` — `Ersatzpflegekraft`, `ErsatzRepo`
  - `db/settings.py` — `UserSettings`, `UserSettingsRepo`, `PlanungsRepo`
- `models.py` reduced from 1168 → 138 lines (pure re-export facade)
- `db/__init__.py` updated to re-export all db submodules
- All existing `from models import ...` calls unchanged (full backwards compatibility)

---

## [v45.0] – 2026-05-30

### Added
- Docker Desktop Quick Start — `quickstart.bat` / `quickstart.sh` — Doppelklick-Start ohne Server-Kenntnisse
- `docker-compose.quickstart.yml` — zieht Image direkt von `ghcr.io/pflegra/core:latest`, kein Build nötig
- GHCR Package `ghcr.io/pflegra/core:latest` ist jetzt public
- Entlastungsbetrag Buchungsmaske (§ 45b SGB XI) — neue Seite im User-Dropdown
  - Buchungen erfassen: Datum, Betrag, Anbieter, Beschreibung, Beleg-Nr.
  - Monatsübersicht: Budget / Verbraucht / Rest pro Monat
  - Jahres-Übersicht mit Fortschrittsbalken
  - Anbieter-Autocomplete aus bisherigen Buchungen
- DB-Schema v13 — neue Tabelle `entlastung_buchungen`

### Changed
- Mobile PWA: Stat-Leiste im Dashboard immer 4 Kacheln in einer Reihe (kein Umbruch mehr)
- Mobile PWA: Person-Spalte in Einträge-Tabelle mit Ellipsis statt Zeilenumbruch
- Datenschutzhinweis in Ausfüllhilfe korrigiert

### Fixed
- Fix: Ersatzpflegekraft anlegen → 500er (ON CONFLICT owner_id fehlte)
- Fix: Adresse + Geburtsdatum der Ersatzpflegekraft erscheinen jetzt korrekt in der Ausfüllhilfe
- Fix: `ersatz_alle` filtert jetzt korrekt nach `owner_id`
- Fix: Ersatzpflegekraft wird direkt per Name aus DB geladen (nicht mehr aus Einträgen)

---

## [v41v] – 2026-05-27

### Added
- Entlastungsbetrag Vorjahresguthaben in Budget-Übersicht (§ 45b SGB XI)
- Ersatzpflegekräfte Stammdaten — neue DB-Tabelle, CRUD, Dropdown im Eintragsformular
- Ausfüllhilfe Verhinderungspflege — KK-unabhängiges PDF-Datenblatt (2 Seiten)
- Entlastungsbetrag Vorjahresguthaben im Budgetplaner (Eingabefeld, nutzbar bis 30.06.)
- DB-Schema v7 — Tabelle `ersatzpflegekraefte`
- 82 neue pytest-Tests (Budgetplaner, Speichern-Router, Vorjahresguthaben)

### Changed
- Budgetplaner: Speichern persistiert jetzt alle Felder (VP, KZP, SL-%, PG, Vorjahresguthaben, Checkbox)
- Budgetplaner: ⚖ Verteilen-Button in VP-Zeile verschoben
- Budgetplaner: Zurücksetzen setzt jetzt wirklich alle Felder zurück
- Budgetplaner: "Als PDF drucken" → "Als PDF speichern"
- Zahlenformat: Deutsches Format überall (1.234,56 €) — Jinja2-Filter `eur`/`eur0` + JS `fmtEur()`
- Ausfüllhilfe: Ersatzpflegekraft-Dropdown aus Stammdaten statt Freitext

### Fixed
- SyntaxError in `ausfuellhilfe_vp.py` (Python 3.8 Kompatibilität)
- Jinja2 Operator-Präzedenz bei `x * 12 | filter` → `(x * 12) | filter`

---

## [v41i–v41m] – 2026-05-27

### Added
- 54 neue Tests für Budgetplaner-Logik (§ 38 Kombinationsleistung, VP+KZP, Entlastungsbetrag, Pflegegrade)
- 28 neue Tests für Speichern-Router (`TestSpeichernRouter`)

---

## [v41h] – 2026-05-26

### Added
- Budgetplaner: Kombinationsleistung § 38 (SL-% kürzt Pflegegeld automatisch)
- Budgetplaner: Entlastungsbetrag KZP-Checkbox (Hotelkosten)
- Budgetplaner: Chips für Leistungsarten ein/ausblendbar
- Budgetplaner: AJAX-Speichern, Gleichmäßig verteilen, PDF-Druck
- JS modularisiert: `leseState()` / `berechne()` / `updateDOM()`

---

## [v40–v41g] – 2026-05

### Added
- Regelwerks-Härtung Phase F (pflege_rules.py zentralisiert)
- Prognose-Bug gefixt
- Plattformreife Phase G: Health/Version Endpoints, Docker Compose, SQLite-Optimierung
- Beträge 2026 vollständig in `pflege_rules.py`

---

## [v35–v39] – 2026-04/05

### Added
- Budgetplaner Grundstruktur (VP+KZP, Sachleistungen, Tagespflege, Hilfsmittel, Hausnotruf, Wohnumfeld, DiPA)
- Pflegegeld-Sätze PG 1–5

---

## [v30–v34] – 2026-03/04

### Added
- Produktreife Phase E: Auto-Backup, Systemstatus, Mobile, PDF-Exports, Datenpflege, Docs, Tests

---

## [v20–v29] – 2026-02/03

### Added
- UX Phase C: Dateneingabe, Tabellen, Suche, Export
- Menü-Neustrukturierung Phase D: Service/Verwaltung/Admin Dropdowns

---

## [v10–v19] – 2026-01/02

### Added
- Regelwerk Phase B: `pflege_rules.py` zentralisiert
- Sicherheit Phase A: Auth, CSRF, Rate-Limit, bcrypt

---

## [v1–v9] – 2025

### Added
- Initiale Migration von LibreOffice Calc / ODS-Makro-Lösung
- FastAPI + Jinja2 + SQLite Grundstruktur
- Home Assistant Add-on Struktur
- Erste VP-Eintragserfassung und Budgetberechnung
