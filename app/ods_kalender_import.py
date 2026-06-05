"""
Pflegra  ODS-Kalender-Import
Liest das spezifische Kalenderformat der Pflegra-ODS-Vorlage.

Struktur der ODS-Datei:
  - Ein Sheet pro Person (z.B. "Jamie Neu", "Julian Neu")
  - 3 Monate nebeneinander in Spaltengruppen:
      Spalten 0-5:   Monat 1 (Tag, WT, Von, -, Bis, Std)
      Spalten 7-12:  Monat 2
      Spalten 14-19: Monat 3
  - 4 solcher Bloecke untereinander -> 12 Monate
  - Jahr steht bei Zelle "Jahr:" rechts im Sheet

Benoetigt: odfpy (pip install odfpy)
pandas ist NICHT erforderlich.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Callable

log = logging.getLogger(__name__)

SYSTEM_SHEETS = {"Dashboard", "Blanko", "Nachweis", "Statistik", "Historie"}

MONATE_DE = {
    "Januar": 1, "Februar": 2, "Maerz": 3, "Mrz": 3, "April": 4,
    "Mai": 5, "Juni": 6, "Juli": 7, "August": 8,
    "September": 9, "Oktober": 10, "November": 11, "Dezember": 12,
}


def _odf_zellwert(cell) -> object:
    """Liest den Wert einer ODF-Zelle (Text, Zahl, Datum, Zeit)."""
    from odf.text import P
    dtype = cell.getAttribute("valuetype")

    if dtype == "float":
        raw = cell.getAttribute("value")
        try:
            return float(raw)
        except (TypeError, ValueError):
            pass

    if dtype == "date":
        raw = cell.getAttribute("datevalue")
        if raw:
            try:
                return datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError:
                pass

    if dtype == "time":
        raw = cell.getAttribute("timevalue")
        if raw and raw.startswith("PT"):
            m = re.match(r"PT(\d+)H(\d+)M", raw)
            if m:
                return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"

    # Fallback: Text aus P-Elementen
    ps = cell.getElementsByType(P)
    if ps:
        text = "".join(
            str(n)
            for p in ps
            for n in p.childNodes
            if n.nodeType == n.TEXT_NODE
        ).strip()
        return text if text else None

    return None


def _lese_sheet_odf(doc, sheet_name: str) -> list[list]:
    """
    Liest ein Sheet aus einem geladenen ODF-Dokument.
    Gibt eine Liste von Zeilen zurueck (jede Zeile = Liste von Werten).
    """
    from odf.table import Table, TableRow, TableCell

    sheets = doc.spreadsheet.getElementsByType(Table)
    ws = None
    for s in sheets:
        if s.getAttribute("name") == sheet_name:
            ws = s
            break
    if ws is None:
        raise KeyError(f"Sheet '{sheet_name}' nicht gefunden")

    zeilen = []
    for row in ws.getElementsByType(TableRow):
        zeile = []
        for cell in row.getElementsByType(TableCell):
            rep = int(cell.getAttribute("numbercolumnsrepeated") or 1)
            wert = _odf_zellwert(cell)
            for _ in range(rep):
                zeile.append(wert)
        zeilen.append(zeile)
    return zeilen


def _sheet_namen(pfad: Path) -> list[str]:
    """Gibt alle Sheet-Namen einer ODS-Datei zurueck (ohne pandas)."""
    from odf.opendocument import load
    from odf.table import Table
    doc = load(str(pfad))
    return [s.getAttribute("name")
            for s in doc.spreadsheet.getElementsByType(Table)]


def _fmt_time(t) -> str:
    if t is None:
        return ""
    if hasattr(t, "strftime"):
        return t.strftime("%H:%M")
    s = str(t).strip()
    return s[:5] if len(s) >= 5 else s


def _parse_sheet(zeilen: list[list], sheet_name: str) -> list[dict]:
    """Parst Rohdaten eines Personen-Sheets in Eintrag-Dicts."""
    # Jahr suchen (steht rechts bei Zelle "Jahr:" in Spalte 22)
    jahr = datetime.now().year
    for row in zeilen:
        if len(row) > 23 and str(row[22]).strip() == "Jahr:":
            try:
                jahr = int(float(str(row[23])))
                break
            except (ValueError, TypeError):
                pass

    # Block-Header-Zeilen finden (Spalte 0 = Monatsname)
    block_rows = []
    for i, row in enumerate(zeilen):
        if not row:
            continue
        monat1_name = str(row[0]).strip() if row[0] is not None else ""
        if monat1_name not in MONATE_DE:
            continue
        # Monate stehen in Spalten 0, 2, 4
        monat2_name = str(row[2]).strip() if len(row) > 2 and row[2] is not None else ""
        monat3_name = str(row[4]).strip() if len(row) > 4 and row[4] is not None else ""
        block_rows.append((
            i,
            MONATE_DE[monat1_name],
            MONATE_DE.get(monat2_name),
            MONATE_DE.get(monat3_name),
        ))

    eintraege = []
    for block_idx, (header_row, monat1, monat2, monat3) in enumerate(block_rows):
        data_start = header_row + 2   # +1 Spaltenbezeichnung, +1 Daten
        data_end = block_rows[block_idx + 1][0] if block_idx + 1 < len(block_rows) else len(zeilen)

        for row_idx in range(data_start, data_end):
            row = zeilen[row_idx]

            for monat, c_tag, c_wt, c_von, c_bis, c_std in [
                (monat1, 0, 1, 2, 4, 5),
                (monat2, 7, 8, 9, 11, 12),
                (monat3, 14, 15, 16, 18, 19),
            ]:
                if monat is None:
                    continue
                if len(row) <= max(c_tag, c_wt, c_von, c_bis, c_std):
                    continue

                von_raw = row[c_von]
                bis_raw = row[c_bis]
                std_raw = row[c_std]

                if von_raw is None or bis_raw is None or std_raw is None:
                    continue

                try:
                    tag = int(float(str(row[c_tag])))
                except (ValueError, TypeError):
                    continue

                try:
                    d = date(jahr, monat, tag)
                except ValueError:
                    continue

                try:
                    stunden = round(float(str(std_raw).replace(",", ".")), 4)
                except (ValueError, TypeError):
                    continue

                wt = str(row[c_wt]).strip() if row[c_wt] is not None else ""

                eintraege.append({
                    "datum":     d,
                    "monat":     monat,
                    "jahr":      jahr,
                    "von":       _fmt_time(von_raw),
                    "bis":       _fmt_time(bis_raw),
                    "stunden":   stunden,
                    "person":    sheet_name,
                    "wochentag": wt,
                })

    return eintraege


def erkenne_format(pfad: Path | str) -> str:
    """
    Erkennt ob eine ODS-Datei das Pflegra-Kalenderformat hat.
    Gibt 'kalender', 'standard' oder 'unbekannt' zurueck.
    Benoetigt nur odfpy, kein pandas.
    """
    try:
        namen = _sheet_namen(Path(pfad))
        sheet_set = set(namen)
        # Kriterium 1: bekannte System-Sheets
        if sheet_set & {"Dashboard", "Blanko", "Nachweis", "Statistik"}:
            return "kalender"
        # Kriterium 2: Personen-Sheet mit Monatsstruktur
        personen = [s for s in namen if s not in SYSTEM_SHEETS]
        if personen:
            from odf.opendocument import load
            doc = load(str(pfad))
            zeilen = _lese_sheet_odf(doc, personen[0])
            if len(zeilen) > 2:
                zelle = str(zeilen[2][0]).strip() if zeilen[2] else ""
                if zelle in MONATE_DE:
                    return "kalender"
        return "standard"
    except Exception as exc:
        log.warning("erkenne_format Fehler: %s", exc)
        return "unbekannt"


def lese_ods_kalender(
    pfad: Path | str,
    fehler_callback: Optional[Callable[[str, Exception], None]] = None,
    person_filter: Optional[list[str]] = None,
) -> list:
    """
    Liest alle Personen-Sheets aus einer Pflegra-ODS-Kalender-Datei.
    Benoetigt nur odfpy, kein pandas.
    """
    try:
        from odf.opendocument import load
    except ImportError:
        raise ImportError("odfpy wird benoetigt: pip install odfpy")

    pfad = Path(pfad)
    if not pfad.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {pfad}")

    doc = load(str(pfad))
    alle_namen = _sheet_namen(pfad)
    log.info("ODS-Kalender '%s': Sheets: %s", pfad.name, alle_namen)

    personen_sheets = [
        s for s in alle_namen
        if s not in SYSTEM_SHEETS and (person_filter is None or s in person_filter)
    ]

    if not personen_sheets:
        log.warning("Keine Personen-Sheets gefunden")
        return []

    from models import PflegeEintrag

    alle_eintraege = []
    for sheet_name in personen_sheets:
        try:
            zeilen = _lese_sheet_odf(doc, sheet_name)
            raw = _parse_sheet(zeilen, sheet_name)
            for r in raw:
                try:
                    e = PflegeEintrag.from_dict(r)
                    alle_eintraege.append(e)
                except Exception as exc:
                    log.warning("Eintrag uebersprungen (%s %s): %s",
                                sheet_name, r.get("datum"), exc)
            log.info("  Sheet '%s': %d Eintraege", sheet_name, len(raw))
        except Exception as exc:
            log.error("Sheet '%s' fehlgeschlagen: %s", sheet_name, exc)
            if fehler_callback:
                fehler_callback(sheet_name, exc)

    log.info("ODS-Kalender gesamt: %d Eintraege", len(alle_eintraege))
    return alle_eintraege
