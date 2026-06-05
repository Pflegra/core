# Pflegra – Deployment-Guide

## Aktuell: Home Assistant OS + Tailscale

### Add-on deployen
```bash
cp /homeassistant/pflegra_addon_vXX.zip /share/
cd /share && unzip -o pflegra_addon_vXX.zip
cp -r /share/pflegra/app /addons/pflegra/
ha apps rebuild local_pflegra
```

### Logs beobachten
```bash
tail -f /share/pflegra/logs/pflegra.log
```

### Health-Check
```
http://192.168.178.93:8000/health
```

---

## VM / Server (Docker Compose)

### Voraussetzungen
- Ubuntu 22.04+ / Debian 12+
- Docker + Docker Compose installiert
- Min. 512 MB RAM, 2 GB Disk

### Installation
```bash
# 1. Repo klonen oder ZIP entpacken
git clone <repo> pflegra
cd pflegra

# 2. Konfiguration
cp .env.example .env
nano .env  # Werte anpassen

# 3. Starten
docker compose up -d

# 4. Health prüfen
curl http://localhost:8000/health
```

### Daten-Migration von HA OS
```bash
# Backup auf HA erstellen
# → Browser: http://192.168.178.93:8000/backup/

# Backup auf neuen Server kopieren
scp ha-user@192.168.178.93:/share/pflegra/backups/pflegra_*.db ./

# In Docker-Volume einspielen
docker run --rm -v pflegra_data:/data \
  -v $(pwd):/backup alpine \
  cp /backup/pflegra_DATUM.db /data/pflegra.db

# Config kopieren
scp ha-user@192.168.178.93:/share/pflegra/config.json ./
docker run --rm -v pflegra_data:/data \
  -v $(pwd):/backup alpine \
  cp /backup/config.json /data/

# Starten
docker compose up -d
```

### Mit Nginx als Reverse Proxy (HTTPS)
```nginx
server {
    listen 443 ssl;
    server_name pflege.deinedomain.de;

    ssl_certificate     /etc/letsencrypt/live/pflege.deinedomain.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pflege.deinedomain.de/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# .env anpassen
PFLEGRA_HTTPS=1
docker compose up -d
```

### Mit Caddy (einfacher, automatisches HTTPS)
```caddyfile
pflege.deinedomain.de {
    reverse_proxy localhost:8000
}
```

### Mit Tailscale auf VM
```bash
# Tailscale installieren
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Zertifikat holen
sudo tailscale cert $(tailscale status --json | jq -r .Self.DNSName)

# HTTPS aktivieren
PFLEGRA_HTTPS=1 docker compose up -d
```

---

## Umgebungsvariablen

| Variable | Bedeutung | Default |
|---|---|---|
| `PFLEGRA_DATA` | Datenverzeichnis | `/data` |
| `PFLEGRA_HTTPS` | Secure Cookie | `0` |
| `PFLEGRA_SECRET` | Session-Secret | auto |
| `PFLEGRA_DEBUG` | Debug-Logging | `0` |
| `PFLEGRA_DOCKER` | Docker-Modus (stdout logging) | `0` |
| `BACKUP_STUNDE` | Auto-Backup Uhrzeit | `2` |
| `PORT` | HTTP-Port | `8000` |
| `TZ` | Zeitzone | `Europe/Berlin` |

---

## Monitoring

### Health-Check
```bash
curl http://localhost:8000/health
# {"status":"ok","db":"ok","db_integrity":"ok","schema_version":6,"uptime_s":273,"version":"2.3.0"}
```

### Version
```bash
curl http://localhost:8000/version
# {"version":"2.3.0","python":"3.11.8"}
```

### DB-Integrität
```bash
curl http://localhost:8000/admin/integrity
# {"integrity":"ok","ok":true}
```

---

## Backup & Recovery

### Manuelles Backup
```bash
# Via Web-UI
http://localhost:8000/backup/

# Via Kommandozeile (Docker)
docker exec pflegra python3 -c "
import sys; sys.path.insert(0,'/app')
from models import PflegraDB
import shutil, datetime
db = PflegraDB('/data/pflegra.db')
db._schema.wal_checkpoint()
shutil.copy('/data/pflegra.db', f'/data/backups/manual_{datetime.date.today()}.db')
print('Backup erstellt')
"
```

### Restore
```bash
# Über Web-UI: /backup/ → Restore-Button
# Oder manuell:
docker stop pflegra
cp /data/backups/pflegra_DATUM.db /data/pflegra.db
docker start pflegra
```

### DB komprimieren (VACUUM)
```bash
# Via Web-UI: Admin → DB komprimieren
# Oder:
curl -X POST http://localhost:8000/admin/vacuum
```

---

## Checkliste Produktionsbetrieb

- [ ] Passwort gesetzt (`/einstellungen/`)
- [ ] HTTPS aktiv (Reverse Proxy + `PFLEGRA_HTTPS=1`)
- [ ] `PFLEGRA_SECRET` gesetzt
- [ ] Auto-Backup läuft (`/backup/` prüfen)
- [ ] Externes Backup vorhanden (NAS/USB)
- [ ] Health-Endpoint erreichbar
- [ ] Log-Rotation konfiguriert
