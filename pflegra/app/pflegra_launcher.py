"""
Pflegra – Windows Launcher
Startet den Pflegra-Server (Uvicorn) und öffnet den Browser.

Phase 1: Minimal, kein Tray, kein Auto-Update.
"""
from __future__ import annotations

import os
import sys
import time
import socket
import threading
import webbrowser
from pathlib import Path

# ── Pfade einrichten ──────────────────────────────────────────────────────────

# Bei frozen EXE: _MEIPASS ins sys.path damit alle Module gefunden werden
if getattr(sys, "frozen", False):
    app_dir = Path(sys._MEIPASS)
else:
    app_dir = Path(__file__).resolve().parent

sys.path.insert(0, str(app_dir))

from _paths import get_app_dir, get_data_dir

DATA_DIR = get_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# PFLEGRA_DATA setzen damit app.py es findet
os.environ["PFLEGRA_DATA"] = str(DATA_DIR)

HOST = "127.0.0.1"
PORT = 8000
URL  = f"http://{HOST}:{PORT}"

# ── Port-Check ────────────────────────────────────────────────────────────────

def port_frei(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) != 0


def warte_auf_server(host: str, port: int, timeout: int = 30) -> bool:
    """Wartet bis der Server antwortet."""
    start = time.time()
    while time.time() - start < timeout:
        if not port_frei(host, port):
            return True
        time.sleep(0.3)
    return False


# ── Browser öffnen ────────────────────────────────────────────────────────────

def browser_oeffnen():
    if warte_auf_server(HOST, PORT):
        webbrowser.open(URL)
    else:
        print(f"[FEHLER] Server nicht erreichbar nach 30 Sekunden: {URL}")


# ── Server starten ────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 45)
    print("  Pflegra wird gestartet...")
    print(f"  Daten: {DATA_DIR}")
    print("=" * 45)
    print()

    if not port_frei(HOST, PORT):
        print(f"[INFO] Pflegra läuft bereits auf {URL}")
        print("[INFO] Browser wird geöffnet...")
        webbrowser.open(URL)
        return

    # Browser im Hintergrund öffnen sobald Server bereit
    t = threading.Thread(target=browser_oeffnen, daemon=True)
    t.start()

    print(f"[INFO] Starte Server auf {URL}")
    print("[INFO] Zum Beenden: Dieses Fenster schließen\n")

    import uvicorn
    uvicorn.run(
        "web.app:app",
        host=HOST,
        port=PORT,
        log_level="warning",
        app_dir=str(app_dir),
    )


if __name__ == "__main__":
    main()
