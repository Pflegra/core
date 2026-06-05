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

**A self-hosted care management platform for planning, organizing and tracking German care benefits (SGB XI).**

Pflegra helps families and care providers manage Verhinderungspflege, Kurzzeitpflege, and all related benefits — without spreadsheets, without data leaving your home.

---

## Features

- **Care record tracking** — log Verhinderungspflege entries with date, time, duration and care type
- **Budget management** — real-time VP+KZP budget status, 56-day limit tracking, annual prognosis
- **Budget simulator** — plan your full year across all benefit types (§ 36, § 37, § 39, § 40, § 41, § 45b SGB XI)
- **Rules engine** — all legal benefit amounts centralized in `pflege_rules.py`, updated per year
- **Care level calculator** — NBA assessment tool (§ 15 SGB XI), all 6 modules, 57 criteria with plain-language explanations, PDF report
- **Benefit finder** — structured benefit overview by care level, setting and benefit type
- **Care level history** — save and track assessments over time with trend chart
- **Entlastungsbetrag tracking** — monthly budget, prior-year carryover indicator (§ 45b SGB XI)
- **Ausfüllhilfe** — KK-independent data sheet for filling out your Pflegekasse's own forms
- **PDF exports** — care records, budget reports, application letters, care level assessment reports
- **Ersatzpflegekräfte** — manage substitute carers in Stammdaten, select per entry
- **Automatic backups** — daily, configurable retention, with restore
- **Multi-user support** — per-user data isolation, roles (admin/user), user management
- **Demo system** — built-in `demo/demo` account with sample data, auto-reset on logout
- **i18n DE/EN** — full German and English UI, language switcher in navbar
- **HTTPS / Tailscale** — built-in Tailscale integration for secure remote access
- **Docker deployment** — for standalone server or VM

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

### Option A — Docker Desktop (Windows/Mac)

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Download the ZIP and extract it
3. Double-click `start.bat` (Windows) or run `./start.sh` (Mac/Linux)
4. Pflegra opens at `http://localhost:8000`

**Or as a one-liner:**
```bash
docker run -d -p 8000:8000 -v pflegra_data:/share/pflegra ghcr.io/pflegra/core:latest
```

### Option B — Docker Compose (Linux Server / VM)

```bash
git clone https://github.com/Pflegra/core.git
cd core
cp .env.example .env
docker compose up -d
```

Open `http://localhost:8000` in your browser.

### Option C — Direct (Python 3.11+)

```bash
cd app
pip install -r requirements_web.txt
uvicorn web.app:app --host 0.0.0.0 --port 8000 --app-dir app
```

**First login:** an `admin` account is created automatically on first run via `/setup`.  
**Demo access:** `demo` / `demo` — resets automatically on logout.

---

## Remote Access (Tailscale)

Pflegra supports secure remote access via [Tailscale](https://tailscale.com) — without exposing ports to the internet.

1. Install Tailscale on your server: `curl -fsSL https://tailscale.com/install.sh | sh`
2. Authenticate: `sudo tailscale up`
3. Enable Funnel: `sudo tailscale funnel --bg --https=443 http://localhost:8000`
4. Pflegra will be available at `https://<your-device>.ts.net`

---

## Requirements

| Component | Minimum |
|---|---|
| Python | 3.11+ |
| RAM | 256 MB |
| Disk | 500 MB |
| OS | Linux, macOS, Windows (via Docker) |

---

## Supported benefit types (2026)

| Benefit | Legal basis | Amount |
|---|---|---|
| VP + KZP (shared pool) | § 39 SGB XI | 3.539 €/year |
| Pflegegeld PG 2–5 | § 37 SGB XI | 347 – 990 €/month |
| Pflegesachleistungen PG 2–5 | § 36 SGB XI | 796 – 2.299 €/month |
| Tagespflege PG 2–5 | § 41 SGB XI | 721 – 2.085 €/month |
| Entlastungsbetrag | § 45b SGB XI | 131 €/month |
| Pflegehilfsmittel | § 40 SGB XI | 42 €/month |
| Wohnumfeldverbesserung | § 40 SGB XI | 4.180 € per measure |
| Hausnotruf | — | 25,50 €/month |
| DiPA App | § 40a SGB XI | 40 €/month |
| DiPA Unterstützung | § 40a SGB XI | 30 €/month |

All amounts live in `app/pflege_rules.py` — one file to update when the law changes.

---

## Architecture

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

**Health endpoint:** `GET /health` — returns status, DB integrity, schema version, uptime

**Auth:** bcrypt · CSRF protection · rate limiting · secure cookies · per-user data isolation

---

## Configuration

Copy `.env.example` to `.env`:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` | HTTP port |
| `TZ` | `Europe/Berlin` | Timezone |
| `PFLEGRA_DATA` | `/share/pflegra` | Data directory |
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

## Legal

This software is for informational purposes only. It does not constitute legal or financial advice. Always verify benefit amounts with your Pflegekasse.

---

## License

Copyright © 2024–2026 Stefan Neu · [AGPLv3](LICENSE) · [s.l.neu@web.de](mailto:s.l.neu@web.de)

*Built for families navigating the German care system.*
