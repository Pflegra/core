"""
Pflegra  Logging
Einmalig beim Start aufrufen: setup_logging()
Danach in jedem Modul: log = logging.getLogger(__name__)
"""

import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_ordner: Path = Path("logs"), debug: bool = False):
    """
    Richtet File- und Console-Logging ein.
    Docker-Modus: wenn log_ordner nicht schreibbar → nur stdout.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    if any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        return

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)-25s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Datei-Handler — Fallback auf stdout wenn nicht schreibbar
    try:
        log_ordner.mkdir(parents=True, exist_ok=True)
        log_datei = log_ordner / "pflegra.log"
        fh = logging.handlers.RotatingFileHandler(
            log_datei, maxBytes=1_000_000, backupCount=5, encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG if debug else logging.INFO)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except (OSError, PermissionError):
        # Docker ohne persistentes Log-Volume → nur stdout
        pass

    # Konsole: INFO im Docker-Modus (stdout), sonst nur Warnings
    import os
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO if os.environ.get("PFLEGRA_DOCKER") == "1" else logging.WARNING)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    logging.getLogger(__name__).info("Logging gestartet")
