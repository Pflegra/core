"""
Pflegra  ImportService
CSV-Import mit Duplikat-Erkennung, Validierung und Vorschau.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from models import PflegeEintrag, PflegraDB
from csv_import import lese_csv

log = logging.getLogger(__name__)


@dataclass
class ImportVorschau:
    """Ergebnis der Analyse vor dem tatschlichen Import."""
    eintraege_neu:       list[PflegeEintrag] = field(default_factory=list)
    eintraege_duplikat:  list[PflegeEintrag] = field(default_factory=list)
    zeilen_fehlerhaft:   list[tuple[int, str, str]] = field(default_factory=list)  # (nr, zeile, fehler)

    @property
    def anzahl_neu(self) -> int:
        return len(self.eintraege_neu)

    @property
    def anzahl_duplikate(self) -> int:
        return len(self.eintraege_duplikat)

    @property
    def anzahl_fehler(self) -> int:
        return len(self.zeilen_fehlerhaft)

    def zusammenfassung(self) -> str:
        teile = [f"{self.anzahl_neu} neue Eintrge"]
        if self.anzahl_duplikate:
            teile.append(f"{self.anzahl_duplikate} Duplikate (werden bersprungen)")
        if self.anzahl_fehler:
            teile.append(f"{self.anzahl_fehler} fehlerhafte Zeilen")
        return "  |  ".join(teile)


@dataclass
class ImportErgebnis:
    """Ergebnis nach durchgefhrtem Import."""
    importiert:   int = 0
    uebersprungen: int = 0
    fehler:       int = 0

    def __str__(self) -> str:
        teile = [f"{self.importiert} importiert"]
        if self.uebersprungen:
            teile.append(f"{self.uebersprungen} Duplikate bersprungen")
        if self.fehler:
            teile.append(f"{self.fehler} Fehler")
        return "  |  ".join(teile)


class ImportService:
    """
    Kapselt den CSV-Import mit Duplikat-Erkennung.
    GUI zeigt zuerst die Vorschau, Nutzer besttigt, dann importiere().
    """

    def __init__(self, db: PflegraDB):
        self._db = db

    def analysiere_tabelle(self, pfad: Path, owner_id: int,
                           person_fallback: str | None = None) -> ImportVorschau:
        """
        Liest eine XLSX/XLS/ODS-Datei und prft auf Duplikate.
        person_fallback wird verwendet wenn die Datei keine person-Spalte hat.
        """
        from ods_xlsx_import import lese_tabelle
        vorschau = ImportVorschau()
        fehler_liste: list[tuple[int, str, str]] = []

        eintraege = lese_tabelle(
            pfad,
            fehler_callback=lambda n, z, e: fehler_liste.append((n, z, str(e))),
            person_fallback=person_fallback,
        )
        vorschau.zeilen_fehlerhaft = fehler_liste

        bestehende = self._lade_duplikat_schluessel(owner_id)
        for e in eintraege:
            e.owner_id = owner_id
            key = self._schluessel(e)
            if key in bestehende:
                vorschau.eintraege_duplikat.append(e)
            else:
                vorschau.eintraege_neu.append(e)

        log.info(
            "Tabellen-Analyse '%s': %d neu, %d Duplikate, %d Fehler",
            pfad.name,
            vorschau.anzahl_neu,
            vorschau.anzahl_duplikate,
            vorschau.anzahl_fehler,
        )
        return vorschau

    def analysiere(self, csv_pfad: Path, owner_id: int,
                   person_fallback: str | None = None) -> ImportVorschau:
        """
        Liest die CSV und prft auf Duplikate ohne etwas zu speichern.
        Duplikat = gleiche Person + Datum + Von-Uhrzeit bereits in DB.
        """
        vorschau = ImportVorschau()
        fehler_liste: list[tuple[int, str, str]] = []

        eintraege = lese_csv(
            csv_pfad,
            fehler_callback=lambda n, z, e: fehler_liste.append((n, z, str(e))),
            person_fallback=person_fallback,
        )
        vorschau.zeilen_fehlerhaft = fehler_liste

        # Bestehende Eintrge als Set fr schnellen Duplikat-Check
        bestehende = self._lade_duplikat_schluessel(owner_id)

        for e in eintraege:
            e.owner_id = owner_id
            key = self._schluessel(e)
            if key in bestehende:
                vorschau.eintraege_duplikat.append(e)
            else:
                vorschau.eintraege_neu.append(e)

        log.info(
            "CSV-Analyse '%s': %d neu, %d Duplikate, %d Fehler",
            csv_pfad.name,
            vorschau.anzahl_neu,
            vorschau.anzahl_duplikate,
            vorschau.anzahl_fehler,
        )
        return vorschau

    def importiere(
        self,
        vorschau: ImportVorschau,
        owner_id: int,
        auch_duplikate: bool = False,
    ) -> ImportErgebnis:
        """
        Fhrt den Import durch. Normalerweise nur neue Eintrge.
        Mit auch_duplikate=True werden alle eingefgt (fr expliziten Re-Import).
        """
        zu_importieren = vorschau.eintraege_neu
        uebersprungen  = vorschau.anzahl_duplikate

        if auch_duplikate:
            zu_importieren = zu_importieren + vorschau.eintraege_duplikat
            uebersprungen  = 0

        for e in zu_importieren:
            e.owner_id = owner_id

        if zu_importieren:
            self._db.insert_many(zu_importieren)

        ergebnis = ImportErgebnis(
            importiert=len(zu_importieren),
            uebersprungen=uebersprungen,
            fehler=vorschau.anzahl_fehler,
        )
        log.info("Import abgeschlossen: %s", ergebnis)
        return ergebnis

    def importiere_direkt(self, csv_pfad: Path, owner_id: int) -> ImportErgebnis:
        """
        Kombiniert analysiere() + importiere() in einem Schritt.
        Fr programmatischen Aufruf ohne GUI-Dialog.
        """
        vorschau = self.analysiere(csv_pfad, owner_id)
        return self.importiere(vorschau, owner_id)

    #  Hilfsmethoden 

    def _lade_duplikat_schluessel(self, owner_id: int) -> set[tuple]:
        """Ldt alle bestehenden Eintrge als kompakte Schlsselmenge."""
        alle = self._db.alle(owner_id)
        return {self._schluessel(e) for e in alle}

    @staticmethod
    def _schluessel(e: PflegeEintrag) -> tuple:
        """Eindeutiger Schlssel fr Duplikat-Erkennung."""
        return (e.person, e.datum.isoformat(), e.von)
