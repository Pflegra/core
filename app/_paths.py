"""
Pflegra – Pfad-Helper für PyInstaller (frozen) und normalen Betrieb.

Im frozen-Zustand (EXE) liegen alle Programmdateien unter sys._MEIPASS.
Datendateien (DB, Backups, Logs) liegen immer unter %APPDATA%/Pflegra.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Verzeichnis mit den Programmdateien (templates, static, translations)."""
    if getattr(sys, "frozen", False):
        # PyInstaller EXE: alles unter _MEIPASS
        return Path(sys._MEIPASS)
    # Normaler Betrieb: app/ Verzeichnis
    return Path(__file__).resolve().parent


def get_data_dir() -> Path:
    """Verzeichnis für Nutzerdaten (DB, Backups, Logs, Config)."""
    # Explizite Umgebungsvariable hat immer Vorrang
    env = os.environ.get("PFLEGRA_DATA")
    if env:
        return Path(env)

    if getattr(sys, "frozen", False):
        # EXE unter Windows: %APPDATA%\Pflegra
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Pflegra"
        # Fallback: neben der EXE
        return Path(sys.executable).parent / "data"

    # Normaler Betrieb: app/ Verzeichnis (bisheriges Verhalten)
    return Path(__file__).resolve().parent
