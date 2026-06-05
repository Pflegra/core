"""
Pflegra  Konfiguration
Liest und schreibt Einstellungen in eine config.json Datei.
Alle Werte haben sinnvolle Standardwerte.
"""

from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass, asdict, field

KONFIG_DATEI = Path("config.json")


@dataclass
class Konfiguration:
    """Alle persistenten Einstellungen der Anwendung."""

    # Pflegedienst / Organisation
    pflegedienst_name: str = ""
    pflegedienst_adresse: str = ""

    # Backup
    auto_backup_stunde: int = 2     # Uhrzeit für tägliches Auto-Backup (0-23)
    benutzer_name: str = "admin"
    passwort_hash: str = ""     # bcrypt-Hash, leer = kein Login nötig (Erststart)
    absender_name: str = ""
    absender_adresse: str = ""
    absender_mail: str = ""
    absender_geburtsdatum: str = ""   # TT.MM.JJJJ – für Vollmacht

    # Finanzen
    stundensatz: float = 20.00

    # Gesetzlicher Jahresbetrag ( 39 SGB XI, Reform ab 01.07.2025)
    # Gemeinsamer Topf fr Verhinderungs- und Kurzzeitpflege
    budget_basis: float = 3_539.00          # gemeinsamer Jahresbetrag
    budget_aufstockung_max: float = 0.00    # nicht mehr separat (gemeinsamer Topf)

    # Pfade
    archiv_basis: str = "Archiv"
    datenbank_pfad: str = "pflegra.db"
    letzter_export_ordner: str = ""
    letzter_import_ordner: str = ""

    # Fenster
    fenster_breite: int = 1100
    fenster_hoehe: int = 700
    fenster_x: int = -1   # -1 = zentrieren
    fenster_y: int = -1

    # Anzeige
    standard_person: str = ""
    standard_jahr: int = 0   # 0 = aktuelles Jahr

    @classmethod
    def lade(cls, pfad: Path = KONFIG_DATEI) -> "Konfiguration":
        """Ldt Konfiguration aus JSON. Fehlende Felder = Standardwerte."""
        if not pfad.exists():
            return cls()
        try:
            with pfad.open(encoding="utf-8") as f:
                daten = json.load(f)
            # Nur bekannte Felder bernehmen, unbekannte ignorieren
            bekannte = {f.name for f in cls.__dataclass_fields__.values()}
            gefiltert = {k: v for k, v in daten.items() if k in bekannte}
            return cls(**gefiltert)
        except Exception:
            return cls()   # Fehlerhafte Config  Standardwerte

    def speichere(self, pfad: Path = KONFIG_DATEI):
        """Schreibt aktuelle Konfiguration als JSON."""
        pfad.parent.mkdir(parents=True, exist_ok=True)
        with pfad.open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    @property
    def budget_gesamt(self) -> float:
        return self.budget_basis + self.budget_aufstockung_max
