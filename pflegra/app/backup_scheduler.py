"""
Pflegra – Automatischer Backup-Scheduler
Läuft als Hintergrundprozess, erstellt täglich um 02:00 Uhr ein Backup.
Wird von run.sh gestartet.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Logging einrichten
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("backup_scheduler")

DATA_DIR = Path(os.environ.get("PFLEGRA_DATA", "/share/pflegra"))
BACKUP_STUNDE = int(os.environ.get("BACKUP_STUNDE", "2"))   # 02:00 Uhr
BACKUP_GRUND  = "auto"


def einmal_backup():
    """Führt ein einzelnes Backup durch."""
    sys.path.insert(0, "/app")
    try:
        from config import Konfiguration
        from services.backup_service import BackupService

        konfig_pfad = DATA_DIR / "config.json"
        konfig = Konfiguration.lade(konfig_pfad)
        db_pfad = DATA_DIR / "pflegra.db"

        if not db_pfad.exists():
            log.warning("DB nicht gefunden: %s", db_pfad)
            return

        svc = BackupService(konfig)
        svc._db_pfad = db_pfad
        svc._backup_ordner = db_pfad.parent / "backups"

        pfad = svc.erstelle_backup(grund=BACKUP_GRUND)
        if pfad:
            log.info("Auto-Backup erstellt: %s", pfad)
        else:
            log.warning("Auto-Backup fehlgeschlagen")
    except Exception as exc:
        log.error("Auto-Backup Fehler: %s", exc, exc_info=True)


def main():
    log.info("Backup-Scheduler gestartet (täglich %02d:00 Uhr)", BACKUP_STUNDE)
    letzter_backup_tag = None

    while True:
        jetzt = datetime.now()
        heute = jetzt.date()

        if jetzt.hour == BACKUP_STUNDE and letzter_backup_tag != heute:
            log.info("Starte tägliches Backup...")
            einmal_backup()
            letzter_backup_tag = heute

        # Jede Minute prüfen
        time.sleep(60)


if __name__ == "__main__":
    main()
