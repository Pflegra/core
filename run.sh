#!/bin/sh
DATA_DIR="${PFLEGRA_DATA:-/data}"
mkdir -p "${DATA_DIR}/Archiv"
mkdir -p "${DATA_DIR}/backups"
mkdir -p "${DATA_DIR}/logs"

export PFLEGRA_DATA="${DATA_DIR}"

echo "Starte Pflegra auf Port 8000..."
exec python3 -m uvicorn web.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level warning \
    --app-dir /app
