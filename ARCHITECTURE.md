# Pflegra – Architektur-Dokumentation

> Stand: v47 · Letzte Aktualisierung: Mai 2026

---

## Systemidentität

```
Selbstgehostete Pflege-Management-Plattform
für Pflegeleistungen nach SGB XI (Deutschland)
```

- **Kein SaaS** — läuft ausschließlich im Heimnetz / auf eigenem Server
- **Kein Framework-Spielplatz** — bewusst pragmatisch gehalten
- **Keine Cloud-Abhängigkeit** — alle Daten lokal in SQLite
- **Multi-User** — volle Datenisolation, Rollen (admin/user)

---

## Technologie-Entscheidungen

| Entscheidung | Gewählt | Warum |
|---|---|---|
| Web-Framework | FastAPI + Jinja2 | Server-Side-Rendering, kein JS-Framework-Overhead |
| Datenbank | SQLite | Ausreichend für Self-Hosted, keine Infrastruktur nötig |
| ORM | Kein ORM | Direktes SQLite, volle Kontrolle |
| Frontend | HTML + CSS + minimal JS | Kein Build-Step, kein Node.js, direkt wartbar |
| Deployment | HA Add-on (Docker) | Läuft auf bestehendem Home Assistant Server |
| PDF | reportlab | Bewährt, keine externe Abhängigkeit |
| Auth | Session-Cookie + bcrypt | Minimal, ausreichend für Self-Hosted |
| i18n | JSON-Dateien + make_t() | Schlank, ohne externe Abhängigkeiten |

---

## Schichtenarchitektur

```
┌─────────────────────────────────────────────┐
│  web/                                       │
│  ├── app.py              FastAPI-App        │
│  ├── auth.py             Session-Auth       │
│  ├── csrf.py             CSRF-Schutz        │
│  ├── routers/            HTTP-Endpunkte     │
│  │   ├── deps.py         base_ctx, get_db   │
│  │   ├── eintraege.py                       │
│  │   ├── entlastung.py                      │
│  │   ├── pflegegrad.py   + Verlauf          │
│  │   ├── leistungsfinder.py                 │
│  │   ├── budget_planung.py                  │
│  │   ├── antraege.py                        │
│  │   ├── admin.py                           │
│  │   └── ...                                │
│  └── templates/          Jinja2-HTML (26)   │
├─────────────────────────────────────────────┤
│  services/                                  │
│  ├── budget_service.py                      │
│  ├── export_service.py                      │
│  ├── import_service.py                      │
│  └── backup_service.py                      │
├─────────────────────────────────────────────┤
│  Fachlogik                                  │
│  ├── pflege_rules.py       Gesetzesregeln   │
│  ├── calculations.py       Berechnungen     │
│  ├── pflegegrad_rechner.py NBA § 15 SGB XI  │
│  └── leistungsfinder.py    Leistungslogik   │
├─────────────────────────────────────────────┤
│  db/                                        │
│  ├── schema.py    Verbindung + Migration    │
│  ├── eintraege.py                           │
│  ├── personen.py                            │
│  ├── versicherte.py                         │
│  ├── users.py                               │
│  ├── ersatzpflege.py                        │
│  ├── settings.py                            │
│  ├── entlastung.py                          │
│  └── pflegegrad_verlauf.py                  │
│  models.py  ← Fassade, re-exportiert alles  │
├─────────────────────────────────────────────┤
│  Persistenz                                 │
│  └── SQLite  /share/pflegra/pflegra.db      │
└─────────────────────────────────────────────┘
```

### Wichtige Prinzipien

**Router kennen keine Fachlogik.**
Router nehmen HTTP-Anfragen entgegen, delegieren an Services/Fachlogik, geben Responses zurück.

**`pflege_rules.py` ist die einzige Wahrheitsquelle für Gesetzesregeln.**
Alle Beträge, Grenzen und Sätze stehen dort — jahresweise, nirgendwo sonst.

**`db/` ist nach Fachdomänen aufgeteilt.**
`models.py` ist nur eine Fassade für Rückwärtskompatibilität — alle Klassen und Repos leben in `db/`.

**`base_ctx` kommt ausschließlich aus `deps.py`.**
Alle Templates erhalten `_()`, `lang`, `current_user`, `csrf_token` aus einer einzigen Quelle.

---

## DB-Schema-Versionen

Automatische Migration beim Start (`db/schema.py → DbSchema.migrate()`).
Aktuelle Version: **v14**

| Version | Änderung |
|---|---|
| 1–5 | Initiales Schema, Einträge, Personen, Versicherte |
| 6–9 | Budget-Planung, Ersatzpflegekräfte, UNIQUE-Constraints |
| 10 | User-Settings |
| 11–12 | owner_id in versicherte |
| 13 | entlastung_buchungen |
| 14 | pflegegrad_verlauf |

---

## Datenhaltung

```
/share/pflegra/
├── pflegra.db          Haupt-Datenbank (SQLite)
├── config.json         Konfiguration
├── .secret_key         Session-Secret (auto-generiert)
├── backups/            Automatische + manuelle Backups
├── logs/               Anwendungslog (rotierend)
└── Archiv/             Exportierte PDFs und CSVs
```

---

## Sicherheit

| Bereich | Implementierung |
|---|---|
| Auth | Session-Cookie, bcrypt-Passwort-Hash, 12h Ablauf |
| CSRF | Double-Submit-Cookie-Pattern |
| Rate-Limit | 5 Fehlversuche / 5 Minuten pro IP (In-Memory) |
| Validierung | Zentral in `web/validation.py` |
| HTTPS | Via Tailscale Funnel oder Reverse Proxy |

---

## Was bewusst NICHT eingeführt wurde

| Nicht eingeführt | Begründung |
|---|---|
| React / Vue | Kein Build-Step, kein Node.js, direkt wartbar |
| PostgreSQL | SQLite ist für Self-Hosted ausreichend |
| ORM | Direktes SQLite gibt volle Kontrolle |
| JWT | Session-Cookies sind einfacher und sicherer |
| gettext/Babel | JSON-i18n ist ausreichend für DE+EN |

---

## Deployment

```bash
# Standard Deploy (HA Add-on)
cd /share && unzip -o pflegra_addon_vXX.zip
cp -r /share/pflegra/app /addons/pflegra/
ha apps rebuild local_pflegra

# Logs
tail -f /share/pflegra/logs/pflegra.log

# Git (English commits)
cd /share/pflegra
git add -A && git commit -m "vXX — description" && git push
```
