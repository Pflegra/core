"""
Pflegra  ExportService
Kapselt alle Export-Operationen. GUI ruft nur noch diesen Service.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from models import PflegeEintrag, PflegraDB, MONATE_DE
from csv_import import schreibe_csv
from pdf_export import (
    exportiere_monat_pdf, exportiere_jahres_pdf, archiv_export,
)
from config import Konfiguration

log = logging.getLogger(__name__)


@dataclass
class ExportErgebnis:
    """Ergebnis eines Export-Vorgangs."""
    erfolgreich:  list[Path] = field(default_factory=list)
    fehlgeschlagen: list[tuple[str, str]] = field(default_factory=list)  # (beschreibung, fehler)

    @property
    def gesamt(self) -> int:
        return len(self.erfolgreich) + len(self.fehlgeschlagen)

    @property
    def hat_fehler(self) -> bool:
        return len(self.fehlgeschlagen) > 0

    def __str__(self) -> str:
        zeilen = [f"{len(self.erfolgreich)} Dateien exportiert"]
        if self.fehlgeschlagen:
            zeilen.append(f"{len(self.fehlgeschlagen)} Fehler")
        for path in self.erfolgreich:
            zeilen.append(f"    {path}")
        for beschr, err in self.fehlgeschlagen:
            zeilen.append(f"    {beschr}: {err}")
        return "\n".join(zeilen)


class ExportService:
    """
    Zentrale Export-Logik fr PDF und CSV.
    Wird von ExportView und knftig von CLI/Batch-Export verwendet.
    """

    def __init__(self, db: PflegraDB, konfig: Konfiguration):
        self._db     = db
        self._konfig = konfig

    @property
    def _pflegedienst(self) -> str:
        return self._konfig.pflegedienst_name

    #  PDF 

    def pdf_monat(
        self,
        person: str,
        jahr: int,
        monat: int,
        owner_id: int,
        zielordner: Optional[Path] = None,
        eintraege: Optional[list[PflegeEintrag]] = None,
    ) -> Path:
        """
        Exportiert einen Monatsnachweis als PDF.
        Gibt den Pfad zur erstellten Datei zurck.
        """
        if eintraege is None:
            eintraege = self._db.nach_monat(person, jahr, monat, owner_id)

        if not eintraege:
            raise ValueError(
                f"Keine Eintrge fr {person} / {MONATE_DE[monat]} {jahr}"
            )

        if zielordner is None:
            zielordner = Path(self._konfig.letzter_export_ordner or ".")

        zielordner.mkdir(parents=True, exist_ok=True)
        sicherer_name = person.replace(",", "").replace(" ", "_")
        dateiname = f"Nachweis_{MONATE_DE[monat]}_{jahr}_{sicherer_name}.pdf"
        pfad = zielordner / dateiname

        exportiere_monat_pdf(
            eintraege, pfad, person, monat, jahr,
            pflegedienst=self._pflegedienst,
        )
        log.info("PDF exportiert: %s", pfad)
        return pfad
    def pdf_monate(
        self,
        person: str,
        jahr: int,
        monate: list[int],
        owner_id: int,
        zielordner: Optional[Path] = None,
    ) -> Path:
        """Exportiert mehrere Monate als eine zusammengefasste PDF."""
        from pdf_export import exportiere_mehrere_monate_pdf
        if not monate:
            raise ValueError("Keine Monate ausgewählt")
        if zielordner is None:
            zielordner = Path(self._konfig.letzter_export_ordner or ".")
        zielordner.mkdir(parents=True, exist_ok=True)
        sicherer_name = person.replace(",", "").replace(" ", "_")
        monate_str = "_".join(str(m) for m in sorted(monate))
        dateiname = f"Nachweis_{jahr}_{monate_str}_{sicherer_name}.pdf"
        pfad = zielordner / dateiname
        alle_eintraege = []
        for monat in sorted(monate):
            eintraege = self._db.nach_monat(person, jahr, monat, owner_id)
            alle_eintraege.extend(eintraege)
        if not alle_eintraege:
            raise ValueError(f"Keine Einträge für {person} in den gewählten Monaten")
        exportiere_mehrere_monate_pdf(
            alle_eintraege, pfad, person, jahr, sorted(monate),
            pflegedienst=self._pflegedienst,
        )
        log.info("Mehrmonats-PDF exportiert: %s", pfad)
        return pfad


    def pdf_jahr(
        self,
        person: str,
        jahr: int,
        owner_id: int,
        zielordner: Optional[Path] = None,
        eintraege: Optional[list[PflegeEintrag]] = None,
    ) -> Path:
        """Exportiert eine Jahresbersicht als PDF."""
        if eintraege is None:
            eintraege = self._db.nach_person_und_jahr(person, jahr, owner_id)

        if not eintraege:
            raise ValueError(f"Keine Eintrge fr {person} / {jahr}")

        if zielordner is None:
            zielordner = Path(self._konfig.letzter_export_ordner or ".")

        zielordner.mkdir(parents=True, exist_ok=True)
        sicherer_name = person.replace(",", "").replace(" ", "_")
        pfad = zielordner / f"Jahresuebersicht_{jahr}_{sicherer_name}.pdf"

        exportiere_jahres_pdf(
            eintraege, pfad, person, jahr,
            pflegedienst=self._pflegedienst,
        )
        log.info("Jahres-PDF exportiert: %s", pfad)
        return pfad

    def archiv_komplett(
        self,
        owner_id: int,
        zielordner: Optional[Path] = None,
        fortschritt_callback: Optional[Callable[[str], None]] = None,
    ) -> ExportErgebnis:
        """
        Exportiert alle Eintrge als vollständigen Archiv-Export.
        Struktur: zielordner/Jahr/Person/Nachweis_Monat.pdf
        """
        if zielordner is None:
            zielordner = Path(self._konfig.archiv_basis)

        alle = self._db.alle(owner_id)
        if not alle:
            raise ValueError("Keine Eintrge in der Datenbank.")

        ergebnis = ExportErgebnis()

        # Gruppieren nach Person + Jahr + Monat
        from itertools import groupby
        sortiert = sorted(alle, key=lambda e: (e.person, e.jahr, e.monat, e.datum))

        for (person, jahr, monat), gruppe in groupby(
            sortiert, key=lambda e: (e.person, e.jahr, e.monat)
        ):
            eintraege_gruppe = list(gruppe)
            beschr = f"{person} / {MONATE_DE[monat]} {jahr}"
            try:
                pfad = self.pdf_monat(
                    person, jahr, monat, owner_id,
                    zielordner=zielordner / str(jahr) / person,
                    eintraege=eintraege_gruppe,
                )
                ergebnis.erfolgreich.append(pfad)
                if fortschritt_callback:
                    fortschritt_callback(f"  {beschr}")
            except Exception as exc:
                ergebnis.fehlgeschlagen.append((beschr, str(exc)))
                log.error("Archiv-Export Fehler %s: %s", beschr, exc)
                if fortschritt_callback:
                    fortschritt_callback(f"  {beschr}: {exc}")

        return ergebnis

    #  CSV 

    def csv_export(
        self,
        zieldatei: Path,
        owner_id: int,
        person: Optional[str] = None,
        jahr: Optional[int] = None,
    ) -> Path:
        """
        Exportiert Eintrge als CSV.
        Optionale Filter: person und/oder jahr.
        """
        alle = self._db.alle(owner_id)

        gefiltert = alle
        if person:
            gefiltert = [e for e in gefiltert if e.person == person]
        if jahr:
            gefiltert = [e for e in gefiltert if e.jahr == jahr]

        if not gefiltert:
            raise ValueError("Keine Eintrge fr diese Filterauswahl.")

        schreibe_csv(gefiltert, zieldatei)
        log.info("CSV exportiert: %s (%d Eintrge)", zieldatei, len(gefiltert))
        return zieldatei
