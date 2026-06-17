# Pflegra

<p align="center">
  <a href="https://github.com/Pflegra/core/releases/latest"><img src="https://img.shields.io/github/v/release/Pflegra/core?style=flat-square&color=2C5F8A&label=Release" alt="Latest Release"></a>
  <a href="https://github.com/Pflegra/core/pkgs/container/core"><img src="https://img.shields.io/badge/Docker-ghcr.io%2Fpflegra%2Fcore-2C5F8A?style=flat-square&logo=docker&logoColor=white" alt="Docker"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-AGPLv3-3ABFAB?style=flat-square" alt="License"></a>
  <a href="https://pflegra.app"><img src="https://img.shields.io/badge/Website-pflegra.app-3ABFAB?style=flat-square" alt="Website"></a>
  <img src="https://img.shields.io/badge/Platform-Docker%20%7C%20Linux%20%7C%20Windows-0D1B2A?style=flat-square" alt="Platform">
</p>

<p align="center">
  <img src="docs/screenshots/dashboard.png" alt="Pflegra Dashboard" width="800">
</p>

Pflegra ist eine selbst gehostete Pflegeverwaltungssoftware für pflegende Angehörige in Deutschland. Sie unterstützt bei der Planung, Dokumentation und Verwaltung von Pflegeleistungen nach SGB XI.

Pflegra hilft Familien dabei, Verhinderungspflege, Entlastungsbetrag und weitere Pflegeleistungen zu verwalten. Ohne Tabellenkalkulation, ohne Cloud und ohne dass Daten das eigene Zuhause verlassen.

---

## Warum Pflegra?

Viele Angehörige verwalten Verhinderungspflege, Entlastungsbetrag und Pflegegrad-Unterlagen in Excel-Dateien, Papierordnern oder verschiedenen Apps.

Pflegra bündelt diese Aufgaben lokal auf dem eigenen Gerät. Ohne Cloud-Zwang, ohne Weitergabe sensibler Gesundheitsdaten und ohne monatliche Abo-Kosten.

---

## Funktionen

- **Pflegeeinträge:** Verhinderungspflege stundenweise oder tageweise erfassen, mit Datum, Dauer und Pflegeperson
- **Budgetverwaltung:** VP+KZP-Budget in Echtzeit, 56-Tage-Grenze, Jahresprognose
- **Budgetplanung:** vollständiges Jahresbudget über alle Leistungsarten planen (§ 36, § 37, § 39, § 40, § 41, § 45b SGB XI)
- **Pflegegradrechner:** NBA-Begutachtung nach § 15 SGB XI, alle 6 Module, 57 Kriterien mit Alltagserklärungen, PDF-Bericht
- **Leistungsfinder:** strukturierte Leistungsübersicht nach Pflegegrad, Versorgungsform und Leistungsart
- **Pflegegradverlauf:** Begutachtungsergebnisse speichern und als Trenddiagramm verfolgen
- **Entlastungsbetrag:** monatliches Budget, Vorjahresguthaben, Übertragsfrist 30. Juni (§ 45b SGB XI)
- **Gutachten-Analyse:** MD-Gutachten als PDF hochladen und automatisch auswerten — Pflegegrad, Punkte, alle 6 Module, Diagnosen
- **Pflegeberatung § 37.3 SGB XI:** Beratungstermine dokumentieren, Nachweise hochladen, Halbjahres-Fristen überwachen
- **Dokumentenarchiv:** Gutachten, Bescheide, Arztberichte und Nachweise pro versicherter Person archivieren
- **Aufgaben & Zeitachse:** offene Aufgaben mit Ampelfarben, chronologische Ereignisübersicht pro Person
- **Fristen & Termine:** eigene Fristen anlegen (MD-Termin, Schwerbehindertenausweis, Vollmacht u.v.m.) mit Ampelfarben im Dashboard
- **Erinnerungen:** Fristen und Pflegeberatungen per E-Mail oder Browser-Push-Benachrichtigung
- **Kontaktverwaltung:** Hausarzt, Pflegekasse, Pflegedienst und Beratungsstellen pro versicherter Person speichern
- **Pflegetagebuch & Chronik:** tägliche Beobachtungen strukturiert erfassen, Chat-ähnliche Chronik-Ansicht mit Schnelleingabe
- **Ausfüllhilfe:** kassenunabhängiges Datenblatt zum Ausfüllen der Formulare der eigenen Pflegekasse
- **PDF-Exporte:** Pflegenachweise, Budgetberichte, Antragsschreiben, Pflegegrad-Berichte
- **Ersatzpflegekräfte:** Stammkräfte in den Versichertendaten hinterlegen, bei Einträgen auswählen
- **Automatische Backups:** täglich, konfigurierbare Aufbewahrung, mit Wiederherstellung
- **Mehrbenutzer:** vollständige Datentrennung pro Nutzer, Rollen Admin/User, Benutzerverwaltung
- **Benutzervertretung und Audit-Log:** Admin kann temporär als Nutzer agieren, alle Aktionen werden protokolliert
- **Demo-System:** integrierter `demo/demo`-Account mit Beispieldaten, automatischer Reset
- **Fernzugriff per Tailscale:** sicherer Zugriff von unterwegs ohne Portfreigaben
- **Zweisprachig DE/EN:** vollständige deutsche und englische Oberfläche, umschaltbar per Klick

---

## Screenshots

| Login | Dashboard |
|---|---|
| ![Login](docs/screenshots/login.png) | ![Dashboard](docs/screenshots/dashboard.png) |

| Pflege-Einträge | Budgetplanung |
|---|---|
| ![Einträge](docs/screenshots/eintraege.png) | ![Budgetplanung](docs/screenshots/budgetplanung_2.png) |

| Anträge & Dokumente | Versicherten-Stammdaten |
|---|---|
| ![Anträge](docs/screenshots/antraege_dokomente.png) | ![Versicherter](docs/screenshots/versicherter.png) |

---

## Quick Start

### Option A: Docker Desktop (Windows/Mac)

1. [Docker Desktop](https://www.docker.com/products/docker-desktop) installieren
2. ZIP herunterladen und entpacken
3. `start.bat` doppelklicken (Windows) oder `./start.sh` ausführen (Mac/Linux)
4. Pflegra öffnet sich unter `http://localhost:8000`

**Einzeiler:**
```bash
docker run -d -p 8000:8000 -v pflegra_data:/data ghcr.io/pflegra/core:latest
```

### Option B: Docker Compose (Linux Server / VM)

```bash
git clone https://github.com/Pflegra/core.git
cd core
cp .env.example .env
docker compose up -d
```

Pflegra ist dann unter `http://localhost:8000` erreichbar.

### Option C: Direkt (Python 3.11+)

```bash
cd app
pip install -r requirements_web.txt
uvicorn web.app:app --host 0.0.0.0 --port 8000 --app-dir app
```

**Erster Login:** Ein `admin`-Account wird beim ersten Start automatisch über `/setup` angelegt.  
**Demo-Zugang:** `demo` / `demo`. Die Beispieldaten werden beim Abmelden automatisch zurückgesetzt.

---

## Fernzugriff (Tailscale)

Pflegra unterstützt sicheren Fernzugriff über [Tailscale](https://tailscale.com), ohne Ports ins Internet öffnen zu müssen.

1. Tailscale installieren: `curl -fsSL https://tailscale.com/install.sh | sh`
2. Anmelden: `sudo tailscale up`
3. Funnel aktivieren: `sudo tailscale funnel --bg --https=443 http://localhost:8000`
4. Pflegra ist dann unter `https://<gerätename>.ts.net` erreichbar

---

## Systemanforderungen

| Komponente | Minimum |
|---|---|
| Python | 3.11+ |
| RAM | 256 MB |
| Speicher | 500 MB |
| Betriebssystem | Linux, macOS, Windows (via Docker) |

---

## Unterstützte Leistungen (2026)

| Leistung | Rechtsgrundlage | Betrag |
|---|---|---|
| VP + KZP (gemeinsamer Topf) | § 39 SGB XI | 3.539 €/Jahr |
| Pflegegeld PG 2–5 | § 37 SGB XI | 347 – 990 €/Monat |
| Pflegesachleistungen PG 2–5 | § 36 SGB XI | 796 – 2.299 €/Monat |
| Tagespflege PG 2–5 | § 41 SGB XI | 721 – 2.085 €/Monat |
| Entlastungsbetrag | § 45b SGB XI | 131 €/Monat |
| Pflegehilfsmittel | § 40 SGB XI | 42 €/Monat |
| Wohnumfeldverbesserung | § 40 SGB XI | 4.180 € je Maßnahme |
| Hausnotruf | — | 25,50 €/Monat |
| DiPA App | § 40a SGB XI | 40 €/Monat |
| DiPA Unterstützung | § 40a SGB XI | 30 €/Monat |

Alle Beträge sind zentral in `app/pflege_rules.py` hinterlegt. Dadurch müssen Gesetzesänderungen nur an einer Stelle gepflegt werden.

---

## Architektur

```
app/
├── pflege_rules.py          # Central rules engine — all legal amounts per year
├── calculations.py          # Budget calculations, prognosis logic
├── leistungsfinder.py       # Benefit finder logic
├── pflegegrad_rechner.py    # NBA care level calculator (§ 15 SGB XI)
├── models.py                # DB facade — re-exports all db/ modules
├── db/
│   ├── schema.py            # DB schema, migrations
│   ├── eintraege.py
│   ├── personen.py
│   ├── versicherte.py
│   ├── users.py
│   ├── ersatzpflege.py
│   ├── settings.py
│   ├── entlastung.py
│   ├── audit.py
│   └── pflegegrad_verlauf.py
├── services/
│   ├── budget_service.py
│   ├── export_service.py
│   ├── import_service.py
│   └── backup_service.py
├── web/
│   ├── auth.py
│   ├── routers/
│   └── templates/
└── tests/
```

**Stack:** FastAPI · Jinja2 · SQLite · ReportLab · Python 3.11+

**Health-Endpunkt:** `GET /health` liefert Status, Datenbankintegrität, Schema-Version und Laufzeit.

**Auth:** bcrypt · CSRF protection · rate limiting · secure cookies · per-user data isolation

---

## Configuration

Copy `.env.example` to `.env`:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | HTTP port |
| `TZ` | `Europe/Berlin` | Timezone |
| `PFLEGRA_DATA` | `/data` | Data directory |
| `PFLEGRA_SECRET` | *(auto-generated)* | Session secret |
| `PFLEGRA_HTTPS` | `0` | Set to `1` behind HTTPS reverse proxy |
| `BACKUP_STUNDE` | `2` | Hour for daily auto-backup (0–23) |

---

## Development

```bash
pip install -r app/requirements_web.txt
cd app && pytest tests/ -v
uvicorn web.app:app --reload --port 8000 --app-dir app
```

---

## Rechtlicher Hinweis

Diese Software dient ausschließlich der persönlichen Orientierung und ersetzt keine Beratung durch Pflegekassen oder den Medizinischen Dienst. Alle Leistungsbeträge sollten stets mit der zuständigen Pflegekasse abgeglichen werden.

---

## License

Copyright © 2024–2026 Stefan Neu · [AGPLv3](LICENSE) · [s.l.neu@web.de](mailto:s.l.neu@web.de)

*Entstanden aus eigener Erfahrung mit der häuslichen Pflege von Angehörigen.*
