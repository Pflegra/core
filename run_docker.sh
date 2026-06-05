#!/bin/sh
# Pflegra – Startscript für Docker/VM-Betrieb (ohne Home Assistant)
set -e

DATA_DIR="${PFLEGRA_DATA:-/data}"
mkdir -p "${DATA_DIR}/backups"
mkdir -p "${DATA_DIR}/logs"
mkdir -p "${DATA_DIR}/Archiv"

export PFLEGRA_DATA="${DATA_DIR}"

echo "[Pflegra] Starte Backup-Scheduler..."
python3 /app/backup_scheduler.py &

echo "[Pflegra] Starte Web-App auf Port 8000..."
exec python3 -m uvicorn web.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level warning \
    --app-dir /app
