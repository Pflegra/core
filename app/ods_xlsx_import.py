"""
Pflegra  ODS/XLSX-Import
Liest Pflege-Eintrge aus LibreOffice (.ods) und Excel (.xlsx, .xls) Dateien.

Spaltenformat: identisch mit dem CSV-Import (datum, von, bis, stunden, person, )
Erwartet einen Header in der ersten Zeile des ersten Sheets.

Abhngigkeiten:
    .xlsx / .xls:   openpyxl  (pip install openpyxl)
    .ods:           odfpy     (pip install odfpy)
    Alternativ:     pandas mit openpyxl/odf-Engine

Installiert durch: install.bat / pip install openpyxl odfpy
"""

from __future__ import annotations

import logging
from datetime import datetime, date
from pathlib import Path
from typing import Callable, Optional

from models import PflegeEintrag
from csv_import import _SPALTEN, _DATUM_FORMATE, _norm_header

log = logging.getLogger(__name__)

UNTERSTUETZTE_FORMATE = {
    ".xlsx": "Excel 2007+",
    ".xls":  "Excel 972003",
    ".ods":  "LibreOffice Calc",
}


def _parse_datum(raw) -> date:
    """Wandelt date/datetime-Objekte und Strings in date um."""
    if isinstance(raw, date):
        return raw if not isinstance(raw, datetime) else raw.date()
    if isinstance(raw, datetime):
        return raw.date()
    raw_str = str(raw).strip()
    for fmt in _DATUM_FORMATE:
        try:
            return datetime.strptime(raw_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unbekanntes Datumsformat: '{raw_str}'")


def _parse_uhrzeit(raw) -> str:
    """Normalisiert Uhrzeit-Werte auf HH:MM."""
    if raw is None:
        return ""
    # datetime.time aus openpyxl
    if hasattr(raw, "strftime"):
        return raw.strftime("%H:%M")
    s = str(raw).strip()
    # 09:00 oder 09:00:00
    if len(s) >= 5 and s[2] == ":":
        return s[:5]
    return s


def _parse_stunden(raw) -> float:
    """Wandelt verschiedene Stunden-Darstellungen in float um."""
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip().replace(",", ".")
    return float(s)


def _zeilen_zu_eintraege(
    header: list[str],
    zeilen: list[list],
    fehler_callback: Optional[Callable],
    dateiname: str,
    person_fallback: Optional[str] = None,
) -> list[PflegeEintrag]:
    """Konvertiert Rohdaten (Header + Zeilen) in PflegeEintrag-Objekte."""
    mapping = _norm_header(header)
    pflicht = ["datum", "von", "bis", "stunden"]
    if not person_fallback:
        pflicht.append("person")
    fehlende = [f for f in pflicht if f not in mapping]
    if fehlende:
        raise ValueError(
            f"Pflichtfelder fehlen: {fehlende}. "
            f"Vorhandene Spalten: {header}"
        )

    idx = {feld: header.index(mapping[feld]) for feld in mapping}
    eintraege: list[PflegeEintrag] = []

    for zeilennr, zeile in enumerate(zeilen, start=2):
        # Leerzeilen berspringen
        if all(z is None or str(z).strip() == "" for z in zeile):
            continue
        try:
            def zelle(feld):
                i = idx.get(feld)
                if i is None or i >= len(zeile):
                    return None
                v = zeile[i]
                return v if v is not None else None

            datum = _parse_datum(zelle("datum"))
            von   = _parse_uhrzeit(zelle("von"))
            bis   = _parse_uhrzeit(zelle("bis"))
            std   = _parse_stunden(zelle("stunden"))
            pers_raw = zelle("person")
            pers  = str(pers_raw).strip() if pers_raw is not None else ""
            if not pers:
                pers = person_fallback or ""
            if not pers:
                raise ValueError("Person darf nicht leer sein (und kein Fallback gesetzt).")

            eintrag = PflegeEintrag.from_dict({
                "datum":     datum,
                "von":       von,
                "bis":       bis,
                "stunden":   std,
                "person":    pers,
                "monat":     zelle("monat") or datum.month,
                "jahr":      zelle("jahr")  or datum.year,
                "wochentag": zelle("wochentag") or None,
                "art":       str(zelle("art") or ""),
                "grund":     str(zelle("grund") or ""),
                "ersatz_name":    str(zelle("ersatz_name")    or ""),
                "ersatz_art":     str(zelle("ersatz_art")     or ""),
                "ersatz_adresse": str(zelle("ersatz_adresse") or ""),
                "notiz":          str(zelle("notiz")          or ""),
            })
            eintraege.append(eintrag)

        except Exception as exc:
            zeile_str = str(zeile)
            log.warning("Zeile %d bersprungen (%s): %s", zeilennr, exc, zeile_str)
            if fehler_callback:
                fehler_callback(zeilennr, zeile_str, exc)

    log.info("'%s': %d Eintrge geladen.", dateiname, len(eintraege))
    return eintraege


#  Format-spezifische Lese-Funktionen 

def _lese_xlsx(pfad: Path) -> tuple[list[str], list[list]]:
    """Liest .xlsx / .xls via openpyxl."""
    try:
        import openpyxl
    except ImportError:
        raise ImportError(
            "openpyxl nicht installiert.\n"
            "Bitte: pip install openpyxl\n"
            "Oder: Doppelklick auf install.bat"
        )
    wb = openpyxl.load_workbook(pfad, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Das Tabellenblatt ist leer.")
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    zeilen = [list(r) for r in rows[1:]]
    return header, zeilen


def _lese_xls(pfad: Path) -> tuple[list[str], list[list]]:
    """Liest .xls (alt) via xlrd, Fallback auf openpyxl."""
    try:
        import xlrd
        wb = xlrd.open_workbook(str(pfad))
        ws = wb.sheet_by_index(0)
        header = [str(ws.cell_value(0, c)).strip() for c in range(ws.ncols)]
        zeilen = []
        for r in range(1, ws.nrows):
            zeile = []
            for c in range(ws.ncols):
                ct = ws.cell_type(r, c)
                cv = ws.cell_value(r, c)
                if ct == xlrd.XL_CELL_DATE:
                    import xlrd.xldate
                    cv = xlrd.xldate.xldate_as_datetime(cv, wb.datemode).date()
                zeile.append(cv)
            zeilen.append(zeile)
        return header, zeilen
    except ImportError:
        # xlrd fehlt  openpyxl versuchen
        return _lese_xlsx(pfad)


def _lese_ods(pfad: Path) -> tuple[list[str], list[list]]:
    """Liest .ods via odfpy."""
    try:
        from odf.opendocument import load
        from odf.table import Table, TableRow, TableCell
        from odf.text import P
    except ImportError:
        raise ImportError(
            "odfpy nicht installiert.\n"
            "Bitte: pip install odfpy\n"
            "Oder: Doppelklick auf install.bat"
        )

    doc = load(str(pfad))
    sheets = doc.spreadsheet.getElementsByType(Table)
    if not sheets:
        raise ValueError("Keine Tabellenbltter in der ODS-Datei gefunden.")

    ws = sheets[0]
    alle_zeilen: list[list] = []

    for row in ws.getElementsByType(TableRow):
        zeile: list = []
        for cell in row.getElementsByType(TableCell):
            # Wiederholungsanzahl
            rep = int(cell.getAttribute("numbercolumnsrepeated") or 1)
            # Zellwert
            ps = cell.getElementsByType(P)
            wert: Optional[str] = None
            if ps:
                wert = "".join(
                    str(n) for p in ps
                    for n in p.childNodes
                    if n.nodeType == n.TEXT_NODE
                ).strip() or None
            # Datentyp
            dtype = cell.getAttribute("valuetype")
            if dtype == "float":
                raw_val = cell.getAttribute("value")
                try:
                    wert = float(raw_val)
                except (TypeError, ValueError):
                    pass
            elif dtype == "date":
                raw_val = cell.getAttribute("datevalue")
                if raw_val:
                    try:
                        wert = datetime.strptime(raw_val, "%Y-%m-%d").date()
                    except ValueError:
                        pass
            elif dtype == "time":
                raw_val = cell.getAttribute("timevalue")
                # PT09H00M00S  09:00
                if raw_val and raw_val.startswith("PT"):
                    try:
                        import re
                        m = re.match(r"PT(\d+)H(\d+)M", raw_val)
                        if m:
                            wert = f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
                    except Exception:
                        pass

            for _ in range(rep):
                zeile.append(wert)
        alle_zeilen.append(zeile)

    if not alle_zeilen:
        raise ValueError("Das erste Tabellenblatt ist leer.")

    header = [str(h).strip() if h is not None else "" for h in alle_zeilen[0]]
    zeilen = alle_zeilen[1:]
    return header, zeilen


#  ffentliche API 

def lese_tabelle(
    pfad: Path | str,
    fehler_callback: Optional[Callable[[int, str, Exception], None]] = None,
    person_fallback: Optional[str] = None,
) -> list[PflegeEintrag]:
    """
    Liest eine XLSX-, XLS- oder ODS-Datei und gibt PflegeEintrag-Objekte zurck.

    Parameter
    ---------
    pfad            Pfad zur Datei.
    fehler_callback Wird pro fehlerhafter Zeile aufgerufen:
                    callback(zeilennummer, rohzeile_als_str, exception).
    person_fallback Person-Name falls die Datei keine person-Spalte enthlt.

    Rckgabe
    --------
    Liste der erfolgreich geparsten PflegeEintrag-Objekte.
    """
    pfad = Path(pfad)
    if not pfad.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {pfad}")

    ext = pfad.suffix.lower()
    if ext not in UNTERSTUETZTE_FORMATE:
        raise ValueError(
            f"Dateiformat '{ext}' nicht untersttzt. "
            f"Untersttzt: {', '.join(UNTERSTUETZTE_FORMATE)}"
        )

    log.info("Lese %s (%s)", pfad.name, UNTERSTUETZTE_FORMATE[ext])

    if ext == ".ods":
        header, zeilen = _lese_ods(pfad)
    elif ext == ".xls":
        header, zeilen = _lese_xls(pfad)
    else:
        header, zeilen = _lese_xlsx(pfad)

    return _zeilen_zu_eintraege(header, zeilen, fehler_callback, pfad.name,
                                person_fallback=person_fallback)


def pruefe_abhaengigkeiten_tabelle() -> dict[str, bool]:
    """
    Prft welche Import-Bibliotheken installiert sind.
    Gibt dict {format: verfgbar} zurck.
    """
    ergebnis = {}
    try:
        import openpyxl
        ergebnis[".xlsx"] = True
    except ImportError:
        ergebnis[".xlsx"] = False

    try:
        import odf
        ergebnis[".ods"] = True
    except ImportError:
        ergebnis[".ods"] = False

    try:
        import xlrd
        ergebnis[".xls"] = True
    except ImportError:
        # xls auch ber openpyxl (neuere xls werden manchmal untersttzt)
        ergebnis[".xls"] = ergebnis.get(".xlsx", False)

    return ergebnis
