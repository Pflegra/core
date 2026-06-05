"""
Pflegra  BackupService
Automatisches SQLite-Backup mit Rotation (max. N Kopien behalten).
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from config import Konfiguration

log = logging.getLogger(__name__)

MAX_BACKUPS = 10   # lteste werden automatisch gelscht


class BackupService:
    """
    Erstellt zeitgestempelte Kopien der SQLite-Datenbank.
    Wird beim App-Start und beim Beenden automatisch aufgerufen.
    """

    def __init__(self, konfig: Konfiguration):
        self._konfig    = konfig
        self._db_pfad   = Path(konfig.datenbank_pfad)
        self._backup_ordner = self._db_pfad.parent / "backups"

    def erstelle_backup(self, grund: str = "auto") -> Path | None:
        """
        Erstellt ein Backup der Datenbank.
        Gibt den Backup-Pfad zurck, oder None wenn die DB nicht existiert.
        """
        if not self._db_pfad.exists():
            return None

        self._backup_ordner.mkdir(parents=True, exist_ok=True)

        zeitstempel = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_name = f"pflegra_{zeitstempel}_{grund}.db"
        backup_pfad = self._backup_ordner / backup_name

        # WAL-Checkpoint: ausstehende Änderungen in Hauptdatei schreiben
        try:
            import sqlite3
            with sqlite3.connect(str(self._db_pfad)) as conn:
                conn.execute("PRAGMA wal_checkpoint(FULL)")
        except Exception as exc:
            log.warning("WAL-Checkpoint fehlgeschlagen: %s", exc)

        shutil.copy2(self._db_pfad, backup_pfad)
        log.info("Backup erstellt: %s", backup_pfad)

        self._rotiere()
        return backup_pfad

    def liste_backups(self) -> list[Path]:
        """Gibt alle vorhandenen Backups zurck, neueste zuerst."""
        if not self._backup_ordner.exists():
            return []
        backups = sorted(
            self._backup_ordner.glob("pflegra_*.db"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return backups

    def wiederherstellen(self, backup_pfad: Path) -> bool:
        """
        Stellt ein Backup wieder her.
        Erstellt vorher ein Sicherungs-Backup der aktuellen DB.
        """
        if not backup_pfad.exists():
            log.error("Backup nicht gefunden: %s", backup_pfad)
            return False

        # Aktuelle DB zuerst sichern
        self.erstelle_backup(grund="vor_wiederherstellung")

        shutil.copy2(backup_pfad, self._db_pfad)
        log.info("Wiederhergestellt aus: %s", backup_pfad)
        return True

    def backup_groesse(self) -> int:
        """Gesamtgre aller Backups in Bytes."""
        return sum(
            p.stat().st_size
            for p in self.liste_backups()
            if p.exists()
        )

    def _rotiere(self, max_backups: int = MAX_BACKUPS):
        """Lscht lteste Backups wenn mehr als max_backups vorhanden."""
        backups = self.liste_backups()
        zu_loeschen = backups[max_backups:]
        for p in zu_loeschen:
            try:
                p.unlink()
                log.debug("Altes Backup gelscht: %s", p)
            except Exception as exc:
                log.warning("Backup-Lschung fehlgeschlagen: %s", exc)
