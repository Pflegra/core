#!/usr/bin/with-contenv bashio

DATA_DIR="/share/pflegra"
mkdir -p "${DATA_DIR}/Archiv"
mkdir -p "${DATA_DIR}/backups"
mkdir -p "${DATA_DIR}/logs"
cd "${DATA_DIR}"
export PFLEGRA_DATA="${DATA_DIR}"

# HTTPS/Tailscale: secure Cookie aktivieren wenn gesetzt
if bashio::config.exists 'https_enabled' && bashio::config.true 'https_enabled'; then
    export PFLEGRA_HTTPS="1"
    bashio::log.info "HTTPS-Modus aktiv (secure Cookies)"
else
    export PFLEGRA_HTTPS="0"
fi

bashio::log.info "Starte Backup-Scheduler..."
python3 /app/backup_scheduler.py &
SCHEDULER_PID=$!
bashio::log.info "Backup-Scheduler läuft (PID: ${SCHEDULER_PID})"

INGRESS_ENTRY=$(bashio::addon.ingress_entry)
export INGRESS_ENTRY
echo "${INGRESS_ENTRY}" > /tmp/ingress_entry
bashio::log.info "Starte Pflegra auf Port 8000 (ingress: ${INGRESS_ENTRY})"
exec python3 -m uvicorn web.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --root-path "${INGRESS_ENTRY}" \
    --proxy-headers \
    --forwarded-allow-ips "*" \
    --log-level warning \
    --app-dir /app
