# Pflegra – Quickstart

## Voraussetzungen

Nur **Docker Desktop** wird benötigt:
👉 https://www.docker.com/products/docker-desktop

Nach der Installation Docker Desktop starten (erscheint in der Taskleiste).

---

## Windows

| Datei | Beschreibung |
|---|---|
| `start.bat` | Pflegra starten + Browser öffnen |
| `stop.bat` | Pflegra beenden |
| `update.bat` | Auf neueste Version aktualisieren |
| `status.bat` | Status prüfen |

**Erster Start:**
1. `start.bat` doppelklicken
2. Beim ersten Start wird das Image heruntergeladen (~200 MB) — einmalig
3. Browser öffnet sich automatisch auf `http://localhost:8000`

---

## Linux / Mac

```bash
./start.sh    # Starten
./stop.sh     # Beenden
./update.sh   # Aktualisieren
```

---

## Erster Login

| | |
|---|---|
| **Demo-Account** | `demo` / `demo` (Musterdaten, wird automatisch zurückgesetzt) |
| **Admin einrichten** | Beim ersten Start wird `/setup` aufgerufen |

---

## Daten & Backup

Alle Daten liegen im Docker-Volume `pflegra_data` — sie bleiben beim Beenden erhalten.

Backup erstellen: In Pflegra unter **Einstellungen → Backup**.

---

## Konfiguration (optional)

Kopiere `.env.example` nach `.env` und passe an:

```
copy .env.example .env   # Windows
cp .env.example .env     # Linux/Mac
```

Wichtigste Einstellung: `PFLEGRA_SECRET` — ein zufälliger Wert für die Session-Verschlüsselung.

---

## Ports

Standard: `http://localhost:8000`

Anderen Port nutzen: In `.env` den Wert `PORT=8001` setzen.

---

## Probleme?

```
status.bat          # Status prüfen (Windows)
docker logs pflegra # Logs anzeigen
```

GitHub: https://github.com/Pflegra/core
