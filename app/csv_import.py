"""
Pflegra  CSV-Import
Liest Pflege-Eintrge aus CSV-Dateien ein.

Erwartetes CSV-Format (Semikolon-getrennt, erste Zeile = Header):
    datum;von;bis;stunden;person[;monat;jahr;wochentag]

datum kann folgende Formate haben:
    YYYY-MM-DD  (ISO, bevorzugt)
    DD.MM.YYYY  (deutsch)
    DD/MM/YYYY

Optionale Spalten monat, jahr, wochentag werden automatisch abgeleitet,
wenn sie fehlen oder leer sind.
"""

from __future__ import annotations

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable

from models import PflegeEintrag

log = logging.getLogger(__name__)

# Untersttzte Datumsformate, in dieser Reihenfolge versucht
_DATUM_FORMATE = ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"]

# Mgliche Spaltennamen-Varianten (je Feld eine Liste, alles lowercase)
_SPALTEN: dict[str, list[str]] = {
    "datum":     ["datum", "date", "einsatzdatum"],
    "von":       ["von", "beginn", "start", "von_uhr"],
    "bis":       ["bis", "ende", "end", "bis_uhr"],
    "stunden":   ["stunden", "hours", "dauer", "std"],
    "person":    ["person", "name", "pflegeperson", "pflegebeduerftiger",
                  "pflegebedrftiger", "patient"],
    "monat":     ["monat", "month"],
    "jahr":      ["jahr", "year", "jahr_zahl"],
    "wochentag": ["wochentag", "weekday", "tag"],
}


def _parse_datum(raw: str) -> datetime.date:
    raw = raw.strip()
    for fmt in _DATUM_FORMATE:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unbekanntes Datumsformat: '{raw}'")


def _norm_header(header: list[str]) -> dict[str, str]:
    """
    Gibt ein Mapping {internes_feld: csv_spaltenname} zurck,
    bereinigt um Gro-/Kleinschreibung und Leerzeichen.
    """
    lc = {h.lower().strip(): h for h in header}
    mapping: dict[str, str] = {}
    for feld, synonyme in _SPALTEN.items():
        for syn in synonyme:
            if syn in lc:
                mapping[feld] = lc[syn]
                break
    return mapping


def lese_csv(
    pfad: Path | str,
    encoding: str = "utf-8-sig",
    delimiter: str | None = None,
    fehler_callback: Callable[[int, str, Exception], None] | None = None,
    person_fallback: str | None = None,
) -> list[PflegeEintrag]:
    """
    Liest eine CSV-Datei und gibt eine Liste von PflegeEintrag-Objekten zurck.

    Parameter
    ---------
    pfad            Pfad zur CSV-Datei.
    encoding        Zeichenkodierung (Standard: UTF-8 mit BOM-Toleranz).
    delimiter       Trennzeichen; wird automatisch erkannt wenn None.
    fehler_callback Wird pro fehlerhafter Zeile aufgerufen:
                    callback(zeilennummer, rohzeile_als_str, exception).
                    Wenn None, werden Fehler nur geloggt.
    person_fallback Wird als Person verwendet wenn die Datei keine person-Spalte hat.

    Rckgabe
    --------
    Liste der erfolgreich geparsten PflegeEintrag-Objekte.
    """
    pfad = Path(pfad)
    if not pfad.exists():
        raise FileNotFoundError(f"CSV-Datei nicht gefunden: {pfad}")

    eintraege: list[PflegeEintrag] = []
    fehler_count = 0

    with pfad.open(encoding=encoding, newline="") as f:
        # Auto-Erkennung des Trennzeichens
        if delimiter is None:
            sample = f.read(4096)
            f.seek(0)
            sniff = csv.Sniffer()
            try:
                dialect = sniff.sniff(sample, delimiters=";,\t|")
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ";"  # Fallback

        reader = csv.DictReader(f, delimiter=delimiter)

        if reader.fieldnames is None:
            raise ValueError("CSV-Datei hat keinen Header.")

        mapping = _norm_header(list(reader.fieldnames))
        pflicht = ["datum", "von", "bis", "stunden"]
        if not person_fallback:
            pflicht.append("person")
        fehlende = [f for f in pflicht if f not in mapping]
        if fehlende:
            raise ValueError(
                f"Pflichtfelder fehlen im CSV-Header: {fehlende}. "
                f"Vorhandene Spalten: {list(reader.fieldnames)}"
            )

        for zeilennr, zeile in enumerate(reader, start=2):  # +2: Header = Zeile 1
            try:
                raw: dict[str, str] = {
                    feld: zeile[csv_spalte].strip()
                    for feld, csv_spalte in mapping.items()
                    if csv_spalte in zeile
                }

                datum = _parse_datum(raw["datum"])

                eintrag = PflegeEintrag.from_dict(
                    {
                        "datum":     datum,
                        "von":       raw["von"],
                        "bis":       raw["bis"],
                        "stunden":   raw["stunden"],
                        "person":    raw.get("person") or person_fallback,
                        "monat":     raw.get("monat") or datum.month,
                        "jahr":      raw.get("jahr") or datum.year,
                        "wochentag": raw.get("wochentag") or None,
                    }
                )
                eintraege.append(eintrag)

            except Exception as exc:
                fehler_count += 1
                zeile_str = str(dict(zeile))
                log.warning("Zeile %d bersprungen (%s): %s", zeilennr, exc, zeile_str)
                if fehler_callback:
                    fehler_callback(zeilennr, zeile_str, exc)

    log.info(
        "CSV '%s': %d Eintrge geladen, %d Fehler.",
        pfad.name, len(eintraege), fehler_count,
    )
    return eintraege


def schreibe_csv(
    eintraege: list[PflegeEintrag],
    pfad: Path | str,
    encoding: str = "utf-8-sig",
    delimiter: str = ";",
) -> Path:
    """
    Schreibt eine Liste von PflegeEintrag-Objekten als CSV-Datei.

    Gibt den tatschlichen Pfad zurck.
    """
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)

    felder = ["id", "datum", "monat", "jahr", "wochentag",
              "von", "bis", "stunden", "person"]

    with pfad.open("w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=felder,
            delimiter=delimiter,
            extrasaction="ignore",
        )
        writer.writeheader()
        for e in eintraege:
            writer.writerow(e.to_dict())

    log.info("CSV geschrieben: %s (%d Eintrge)", pfad, len(eintraege))
    return pfad
