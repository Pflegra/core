"""
Pflegra  PDF-Export
Erzeugt professionelle Verhinderungspflege-Nachweise als PDF.

Verwendet reportlab (Platypus-API fr einfache Formatierung).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable,
    KeepTogether,
    PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from models import PflegeEintrag, MONATE_DE

log = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Farben & Design                                                     #
# ------------------------------------------------------------------ #
FARBE_PRIMR   = colors.HexColor("#2C5F8A")   # Dunkelblau
FARBE_HELL     = colors.HexColor("#E8F0F8")   # Sehr helles Blau
FARBE_AKZENT   = colors.HexColor("#4A90C4")   # Mittleres Blau
FARBE_TEXT     = colors.HexColor("#2D2D2D")
FARBE_GRAU     = colors.HexColor("#666666")
FARBE_TRENN    = colors.HexColor("#CCCCCC")

def _erstelle_styles() -> dict:
    basis = getSampleStyleSheet()
    s = {}

    s["titel"] = ParagraphStyle(
        "PNTitel",
        parent=basis["Normal"],
        fontSize=18,
        fontName="Helvetica-Bold",
        textColor=FARBE_PRIMR,
        spaceAfter=4,
        alignment=TA_LEFT,
    )
    s["untertitel"] = ParagraphStyle(
        "PNUntertitel",
        parent=basis["Normal"],
        fontSize=11,
        fontName="Helvetica",
        textColor=FARBE_GRAU,
        spaceAfter=2,
        alignment=TA_LEFT,
    )
    s["abschnitt"] = ParagraphStyle(
        "PNAbschnitt",
        parent=basis["Normal"],
        fontSize=9,
        fontName="Helvetica-Bold",
        textColor=FARBE_PRIMR,
        spaceBefore=8,
        spaceAfter=4,
    )
    s["normal"] = ParagraphStyle(
        "PNNormal",
        parent=basis["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=FARBE_TEXT,
    )
    s["klein"] = ParagraphStyle(
        "PKlein",
        parent=basis["Normal"],
        fontSize=7.5,
        fontName="Helvetica",
        textColor=FARBE_GRAU,
    )
    s["fusszeile"] = ParagraphStyle(
        "PNFuss",
        parent=basis["Normal"],
        fontSize=7,
        fontName="Helvetica",
        textColor=FARBE_GRAU,
        alignment=TA_CENTER,
    )
    s["summe_label"] = ParagraphStyle(
        "PNSummeLabel",
        parent=basis["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=FARBE_PRIMR,
        alignment=TA_RIGHT,
    )
    s["summe_wert"] = ParagraphStyle(
        "PNSummeWert",
        parent=basis["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=FARBE_PRIMR,
        alignment=TA_LEFT,
    )
    return s


def _tabellen_stil(n_zeilen: int = 0) -> TableStyle:
    """n_zeilen = Gesamtanzahl Zeilen inkl. Header."""
    stil = TableStyle([
        # Header-Zeile
        ("BACKGROUND",   (0, 0), (-1, 0), FARBE_PRIMR),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 8.5),
        ("TOPPADDING",   (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING",(0, 0), (-1, 0), 6),
        # Datenzellen
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 8.5),
        ("TOPPADDING",   (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 1), (-1, -1), 5),
        ("TEXTCOLOR",    (0, 1), (-1, -1), FARBE_TEXT),
        # Gitter
        ("GRID",         (0, 0), (-1, -1), 0.4, FARBE_TRENN),
        ("LINEBELOW",    (0, 0), (-1, 0), 1.5, FARBE_PRIMR),
        # Ausrichtung Stunden (rechts)
        ("ALIGN",        (5, 0), (5, -1), "RIGHT"),
    ])

    # Wechselnde Zeilenfarben  nur bis tatschliche Zeilenanzahl
    for i in range(1, n_zeilen):
        if i % 2 == 1:
            stil.add("BACKGROUND", (0, i), (-1, i), colors.white)
        else:
            stil.add("BACKGROUND", (0, i), (-1, i), FARBE_HELL)

    return stil


# ------------------------------------------------------------------ #
#  ffentliche API                                                     #
# ------------------------------------------------------------------ #

def exportiere_monat_pdf(
    eintraege: list[PflegeEintrag],
    pfad: Path | str,
    person: Optional[str] = None,
    monat: Optional[int] = None,
    jahr: Optional[int] = None,
    pflegedienst: str = "",
    unterschrift_person: str = "",
) -> Path:
    """
    Erstellt einen monatlichen Verhinderungspflege-Nachweis als PDF.

    Parameter
    ---------
    eintraege           Liste der PflegeEintrag-Objekte fr diesen Export.
    pfad                Zieldatei (wird erstellt inkl. Elternordner).
    person              Anzeigename (wird aus Eintrgen abgeleitet wenn None).
    monat               Monat 112 (wird abgeleitet wenn None).
    jahr                Jahr (wird abgeleitet wenn None).
    pflegedienst        Optionaler Name des Pflegedienstes fr den Header.
    unterschrift_person Name der unterzeichnenden Person.

    Rckgabe
    --------
    Path zur erstellten PDF-Datei.
    """
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)

    if not eintraege:
        raise ValueError("Keine Eintrge vorhanden  PDF wird nicht erstellt.")

    # Meta aus Eintrgen ableiten, wenn nicht bergeben
    person  = person  or eintraege[0].person
    monat   = monat   or eintraege[0].monat
    jahr    = jahr    or eintraege[0].jahr

    eintraege_sorted = sorted(eintraege, key=lambda e: (e.datum, e.von))

    s = _erstelle_styles()

    doc = SimpleDocTemplate(
        str(pfad),
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=3.0 * cm,
        title=f"Verhinderungspflege-Nachweis {MONATE_DE[monat]} {jahr}",
        author="Pflegra",
        subject=f"Nachweis fr {person}",
    )

    story = []

    # ---- Kopfzeile ------------------------------------------------ #
    story.append(Paragraph("Verhinderungspflege-Nachweis", s["titel"]))
    story.append(Paragraph(
        f"{MONATE_DE[monat]} {jahr}    {person}",
        s["untertitel"]
    ))
    if pflegedienst:
        story.append(Paragraph(pflegedienst, s["klein"]))

    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=FARBE_PRIMR))
    story.append(Spacer(1, 0.4 * cm))

    # ---- Stammdaten-Box ------------------------------------------- #
    story.append(Paragraph("Stammdaten", s["abschnitt"]))

    info_daten = [
        ["Pflegebedrftige Person:", person,
         "Monat / Jahr:", f"{MONATE_DE[monat]} {jahr}"],
        ["Anzahl Einstze:", str(len(eintraege_sorted)),
         "Gesamtstunden:", _format_stunden(sum(e.stunden for e in eintraege_sorted))],
    ]
    info_tabelle = Table(
        info_daten,
        colWidths=[4.5 * cm, 5.0 * cm, 3.5 * cm, 4.0 * cm],
    )
    info_tabelle.setStyle(TableStyle([
        ("FONTNAME",     (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR",    (0, 0), (0, -1), FARBE_GRAU),
        ("TEXTCOLOR",    (2, 0), (2, -1), FARBE_GRAU),
        ("FONTNAME",     (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",     (2, 0), (2, -1), "Helvetica-Bold"),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("BACKGROUND",   (0, 0), (-1, -1), FARBE_HELL),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [FARBE_HELL, colors.white]),
        ("BOX",          (0, 0), (-1, -1), 0.5, FARBE_TRENN),
        ("INNERGRID",    (0, 0), (-1, -1), 0.3, FARBE_TRENN),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_tabelle)
    story.append(Spacer(1, 0.5 * cm))

    # ---- Einsatz-Tabelle ------------------------------------------ #
    story.append(Paragraph("Einsatznachweis", s["abschnitt"]))

    header = ["Nr.", "Wochentag", "Datum", "Von", "Bis", "Stunden"]
    tabel_daten = [header]
    for i, e in enumerate(eintraege_sorted, start=1):
        tabel_daten.append([
            str(i),
            e.wochentag,
            e.datum.strftime("%d.%m.%Y"),
            e.von,
            e.bis,
            _format_stunden(e.stunden),
        ])

    # Summenzeile
    gesamt = sum(e.stunden for e in eintraege_sorted)
    tabel_daten.append(["", "", "", "", "Gesamt:", _format_stunden(gesamt)])

    col_breiten = [1.0 * cm, 3.0 * cm, 3.0 * cm, 2.2 * cm, 2.2 * cm, 2.5 * cm]
    tabelle = Table(tabel_daten, colWidths=col_breiten, repeatRows=1)

    ts = _tabellen_stil(len(tabel_daten))
    # Summenzeile hervorheben
    summe_zeile = len(tabel_daten) - 1
    ts.add("FONTNAME",     (0, summe_zeile), (-1, summe_zeile), "Helvetica-Bold")
    ts.add("TEXTCOLOR",    (0, summe_zeile), (-1, summe_zeile), FARBE_PRIMR)
    ts.add("LINEABOVE",    (0, summe_zeile), (-1, summe_zeile), 1.0, FARBE_PRIMR)
    ts.add("BACKGROUND",   (0, summe_zeile), (-1, summe_zeile), FARBE_HELL)
    ts.add("ALIGN",        (4, summe_zeile), (5, summe_zeile), "RIGHT")

    tabelle.setStyle(ts)
    story.append(tabelle)
    story.append(Spacer(1, 0.8 * cm))

    # ---- Unterschrift --------------------------------------------- #
    story.append(HRFlowable(width="100%", thickness=0.5, color=FARBE_TRENN))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Unterschrift & Besttigung", s["abschnitt"]))

    unterschrift_daten = [
        ["Datum:", "_" * 30, "Unterschrift Pflegeperson:", "_" * 30],
        ["", "", "", ""],
    ]
    if unterschrift_person:
        unterschrift_daten[1][2] = ""
        unterschrift_daten[1][3] = unterschrift_person

    unt_tabelle = Table(
        unterschrift_daten,
        colWidths=[2.0 * cm, 5.5 * cm, 5.0 * cm, 5.0 * cm],
    )
    unt_tabelle.setStyle(TableStyle([
        ("FONTNAME",     (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR",    (0, 0), (0, -1), FARBE_GRAU),
        ("TEXTCOLOR",    (2, 0), (2, -1), FARBE_GRAU),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    story.append(unt_tabelle)

    # ---- Fuzeile im Dokument ------------------------------------- #
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=0.3, color=FARBE_TRENN))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Erstellt mit Pflegra    {MONATE_DE[monat]} {jahr}    {person}",
        s["fusszeile"]
    ))

    doc.build(story, onFirstPage=_seiten_rahmen, onLaterPages=_seiten_rahmen)
    log.info("PDF erstellt: %s", pfad)
    return pfad


def exportiere_jahres_pdf(
    eintraege: list[PflegeEintrag],
    pfad: Path | str,
    person: Optional[str] = None,
    jahr: Optional[int] = None,
    pflegedienst: str = "",
) -> Path:
    """
    Erstellt eine Jahresbersicht als PDF mit einer Zeile pro Monat.
    """
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)

    if not eintraege:
        raise ValueError("Keine Eintrge vorhanden.")

    person = person or eintraege[0].person
    jahr   = jahr   or eintraege[0].jahr

    s = _erstelle_styles()

    doc = SimpleDocTemplate(
        str(pfad),
        pagesize=A4,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        topMargin=2.5 * cm, bottomMargin=3.0 * cm,
        title=f"Jahresbersicht Verhinderungspflege {jahr}",
    )
    story = []

    story.append(Paragraph(f"Jahresbersicht {jahr}", s["titel"]))
    story.append(Paragraph(f"Verhinderungspflege    {person}", s["untertitel"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=FARBE_PRIMR))
    story.append(Spacer(1, 0.5 * cm))

    # Monatssummierung
    monate_daten: dict[int, dict] = {
        m: {"einsaetze": 0, "stunden": 0.0}
        for m in range(1, 13)
    }
    for e in eintraege:
        if e.jahr == jahr:
            monate_daten[e.monat]["einsaetze"] += 1
            monate_daten[e.monat]["stunden"] += e.stunden

    header = ["Monat", "Einstze", "Gesamtstunden"]
    tabel_daten = [header]
    for m in range(1, 13):
        md = monate_daten[m]
        tabel_daten.append([
            MONATE_DE[m],
            str(md["einsaetze"]) if md["einsaetze"] > 0 else "",
            _format_stunden(md["stunden"]) if md["stunden"] > 0 else "",
        ])

    gesamt_einsaetze = sum(md["einsaetze"] for md in monate_daten.values())
    gesamt_stunden   = sum(md["stunden"]   for md in monate_daten.values())
    tabel_daten.append(["Gesamt", str(gesamt_einsaetze), _format_stunden(gesamt_stunden)])

    tabelle = Table(tabel_daten, colWidths=[5.0 * cm, 3.5 * cm, 4.0 * cm])
    ts = _tabellen_stil(len(tabel_daten))
    summe_zeile = len(tabel_daten) - 1
    ts.add("FONTNAME",  (0, summe_zeile), (-1, summe_zeile), "Helvetica-Bold")
    ts.add("TEXTCOLOR", (0, summe_zeile), (-1, summe_zeile), FARBE_PRIMR)
    ts.add("LINEABOVE", (0, summe_zeile), (-1, summe_zeile), 1.0, FARBE_PRIMR)
    ts.add("BACKGROUND",(0, summe_zeile), (-1, summe_zeile), FARBE_HELL)
    tabelle.setStyle(ts)
    story.append(tabelle)

    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.3, color=FARBE_TRENN))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Erstellt mit Pflegra    Jahresbersicht {jahr}    {person}",
        s["fusszeile"]
    ))

    doc.build(story, onFirstPage=_seiten_rahmen, onLaterPages=_seiten_rahmen)
    log.info("Jahres-PDF erstellt: %s", pfad)
    return pfad


def archiv_export(
    eintraege: list[PflegeEintrag],
    basis: Path = Path("Archiv"),
    pflegedienst: str = "",
) -> list[Path]:
    """
    Exportiert alle Eintrge geordnet nach Person und Monat in den Archivordner.
    Struktur: Archiv/<Jahr>/<Person>/Nachweis_<Monat>_<Jahr>.pdf

    Gibt alle erstellten PDF-Pfade zurck.
    """
    from itertools import groupby

    sortiert = sorted(eintraege, key=lambda e: (e.person, e.jahr, e.monat, e.datum))
    erzeugte: list[Path] = []

    for (person, jahr, monat), gruppe in groupby(
        sortiert, key=lambda e: (e.person, e.jahr, e.monat)
    ):
        eintraege_gruppe = list(gruppe)
        ordner = basis / str(jahr) / person
        dateiname = f"Nachweis_{MONATE_DE[monat]}_{jahr}.pdf"
        pdf_pfad = ordner / dateiname

        try:
            exportiere_monat_pdf(
                eintraege_gruppe, pdf_pfad,
                person=person, monat=monat, jahr=jahr,
                pflegedienst=pflegedienst,
            )
            erzeugte.append(pdf_pfad)
        except Exception as exc:
            log.error("Fehler bei %s/%d/%02d: %s", person, jahr, monat, exc)

    return erzeugte


# ------------------------------------------------------------------ #
#  Hilfsfunktionen                                                     #
# ------------------------------------------------------------------ #

def _format_stunden(stunden: float) -> str:
    """Formatiert Stunden als 'X,XX h'."""
    return f"{stunden:.2f} h".replace(".", ",")


def _seiten_rahmen(canvas, doc):
    """Seitennummer + Erstellungshinweis in der Fußzeile."""
    from reportlab.lib.units import cm
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(FARBE_GRAU)
    breite = doc.pagesize[0]
    hoehe  = doc.pagesize[1]
    # Seitennummer rechts
    canvas.drawRightString(
        breite - 2.5 * cm,
        1.5 * cm,
        f"Seite {doc.page}",
    )
    # Erstellt-Hinweis links
    canvas.drawString(
        2.5 * cm,
        1.5 * cm,
        "Erstellt mit Pflegra",
    )
    # Trennlinie
    canvas.setStrokeColor(FARBE_TRENN)
    canvas.setLineWidth(0.3)
    canvas.line(2.5 * cm, 1.8 * cm, breite - 2.5 * cm, 1.8 * cm)
    canvas.restoreState()

def exportiere_mehrere_monate_pdf(
    eintraege: list,
    pfad,
    person: str,
    jahr: int,
    monate: list,
    pflegedienst: str = "",
) -> "Path":
    """
    Erstellt eine zusammengefasste PDF fuer mehrere Monate als durchgehende Liste.
    Monate als Zwischenueberschriften, einmal Datum + Unterschrift am Ende.
    """
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate

    monate_sorted = sorted(monate)
    monate_namen = [MONATE_DE[m] for m in monate_sorted]

    s = _erstelle_styles()

    doc = SimpleDocTemplate(
        str(pfad),
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=3.0 * cm,
        title=f"Verhinderungspflege-Nachweis {', '.join(monate_namen)} {jahr}",
        author="Pflegra",
    )

    story = []

    # Kopfzeile
    story.append(Paragraph("Verhinderungspflege-Nachweis", s["titel"]))
    story.append(Paragraph(
        f"{', '.join(monate_namen)} {jahr}    {person}", s["untertitel"]
    ))
    if pflegedienst:
        story.append(Paragraph(pflegedienst, s["klein"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=1.5, color=FARBE_PRIMR))
    story.append(Spacer(1, 0.5 * cm))

    # Durchgehende Tabelle mit Monats-Zwischenueberschriften
    header = ["Nr.", "Datum", "Wochentag", "Von", "Bis", "Stunden"]
    tabel_daten = [header]
    col_breiten = [1.0*cm, 3.0*cm, 3.0*cm, 2.2*cm, 2.2*cm, 2.5*cm]

    gesamt_stunden = 0.0
    gesamt_einsaetze = 0
    lfd_nr = 1
    monat_header_zeilen = []

    for monat in monate_sorted:
        monat_eintraege = sorted(
            [e for e in eintraege if e.monat == monat],
            key=lambda e: (e.datum, e.von)
        )
        if not monat_eintraege:
            continue

        # Monat als Zwischenueberschrift (als eigene Zeile mit Colspan-Effekt)
        monat_header_zeilen.append(len(tabel_daten))
        monat_stunden = sum(e.stunden for e in monat_eintraege)
        tabel_daten.append([
            MONATE_DE[monat],
            f"{len(monat_eintraege)} Einsaetze",
            f"{_format_stunden(monat_stunden)}",
            "", "", "",
        ])

        for e in monat_eintraege:
            tabel_daten.append([
                str(lfd_nr),
                e.datum.strftime("%d.%m.%Y"),
                e.wochentag,
                e.von,
                e.bis,
                _format_stunden(e.stunden),
            ])
            lfd_nr += 1
            gesamt_stunden += e.stunden
            gesamt_einsaetze += 1

    if not gesamt_einsaetze:
        raise ValueError("Keine Eintraege fuer die gewaehlten Monate")

    # Summenzeile
    summe_idx = len(tabel_daten)
    tabel_daten.append([
        "", "", "", "",
        "Gesamt:", _format_stunden(gesamt_stunden)
    ])

    tabelle = Table(tabel_daten, colWidths=col_breiten, repeatRows=1)
    ts = _tabellen_stil(len(tabel_daten))

    # Monatsueberschriften hervorheben - volle farbige Box
    for zeile_idx in monat_header_zeilen:
        ts.add("BACKGROUND",    (0, zeile_idx), (-1, zeile_idx), FARBE_PRIMR)
        ts.add("FONTNAME",      (0, zeile_idx), (-1, zeile_idx), "Helvetica-Bold")
        ts.add("FONTSIZE",      (0, zeile_idx), (-1, zeile_idx), 10)
        ts.add("TEXTCOLOR",     (0, zeile_idx), (-1, zeile_idx), colors.white)
        ts.add("TOPPADDING",    (0, zeile_idx), (-1, zeile_idx), 7)
        ts.add("BOTTOMPADDING", (0, zeile_idx), (-1, zeile_idx), 7)
        ts.add("LEFTPADDING",   (0, zeile_idx), (-1, zeile_idx), 8)
        ts.add("SPAN",          (0, zeile_idx), (1, zeile_idx))
        ts.add("LINEABOVE",     (0, zeile_idx), (-1, zeile_idx), 2.0, FARBE_PRIMR)
        ts.add("LINEBELOW",     (0, zeile_idx), (-1, zeile_idx), 0.5, colors.white)

    # Summenzeile
    ts.add("FONTNAME",  (0, summe_idx), (-1, summe_idx), "Helvetica-Bold")
    ts.add("TEXTCOLOR", (0, summe_idx), (-1, summe_idx), FARBE_PRIMR)
    ts.add("LINEABOVE", (0, summe_idx), (-1, summe_idx), 1.0, FARBE_PRIMR)
    ts.add("BACKGROUND",(0, summe_idx), (-1, summe_idx), FARBE_HELL)
    ts.add("ALIGN",     (4, summe_idx), (5, summe_idx), "RIGHT")
    tabelle.setStyle(ts)

    story.append(tabelle)
    story.append(Spacer(1, 0.8 * cm))

    # Einmal Unterschrift am Ende
    story.append(HRFlowable(width="100%", thickness=0.5, color=FARBE_TRENN))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Unterschrift & Bestaetigung", s["abschnitt"]))
    unt_daten = [[
        "Datum:", "_" * 30,
        "Unterschrift Pflegeperson:", "_" * 30,
    ]]
    unt_tabelle = Table(unt_daten, colWidths=[2.0*cm, 5.5*cm, 5.0*cm, 5.0*cm])
    unt_tabelle.setStyle(TableStyle([
        ("FONTNAME",      (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("TEXTCOLOR",     (0,0), (0,-1),  FARBE_GRAU),
        ("TEXTCOLOR",     (2,0), (2,-1),  FARBE_GRAU),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(unt_tabelle)
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=0.3, color=FARBE_TRENN))
    story.append(Spacer(1, 0.2 * cm))
    story.append(Paragraph(
        f"Erstellt mit Pflegra    {', '.join(monate_namen)} {jahr}    {person}",
        s["fusszeile"]
    ))

    doc.build(story, onFirstPage=_seiten_rahmen, onLaterPages=_seiten_rahmen)
    log.info("Mehrmonats-PDF erstellt: %s", pfad)
    return pfad




# ------------------------------------------------------------------ #
#  Pflegegrad-Einschätzungsbericht                                    #
# ------------------------------------------------------------------ #

def exportiere_pflegegrad_pdf(
    ergebnis,
    versicherter_name: str = "",
    absender_name: str = "",
    datum: str = "",
    ausgabe_pfad: Optional[str] = None,
) -> bytes:
    """
    Erzeugt einen PDF-Bericht zur Pflegegrad-Einschätzung.

    ergebnis: RechnerErgebnis aus pflegegrad_rechner.berechne_pflegegrad()
    Gibt PDF als bytes zurück (und optional in Datei).
    """
    import io
    from datetime import date as _date

    puffer = io.BytesIO()
    ziel = ausgabe_pfad or puffer

    doc = SimpleDocTemplate(
        ziel if isinstance(ziel, str) else puffer,
        pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title="Pflegegrad-Einschätzung",
    )

    s = _erstelle_styles()
    elemente = []
    breite = A4[0] - 4*cm

    datum_str = datum or _date.today().strftime("%d.%m.%Y")
    pg = ergebnis.pflegegrad
    farben_pg = {
        0: colors.HexColor("#718096"),
        1: colors.HexColor("#38a169"),
        2: colors.HexColor("#d69e2e"),
        3: colors.HexColor("#dd6b20"),
        4: colors.HexColor("#e53e3e"),
        5: colors.HexColor("#9b2c2c"),
    }
    farbe_pg = farben_pg.get(pg, FARBE_PRIMR)

    # ── Kopfzeile ──────────────────────────────────────────────────
    kopf_daten = [[
        Paragraph("Pflegra", ParagraphStyle("PGKopf", parent=s["titel"], fontSize=14)),
        Paragraph(
            f"Pflegegrad-Einschätzung<br/>"
            f"<font size='8' color='#718096'>{datum_str}</font>",
            ParagraphStyle("PGKopfR", parent=s["normal"], alignment=TA_RIGHT, fontSize=10, fontName="Helvetica-Bold"),
        ),
    ]]
    kopf = Table(kopf_daten, colWidths=[breite*0.6, breite*0.4])
    kopf.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LINEBELOW", (0,0), (-1,0), 1.5, FARBE_PRIMR),
        ("BOTTOMPADDING", (0,0), (-1,0), 8),
    ]))
    elemente.append(kopf)
    elemente.append(Spacer(1, 0.4*cm))

    # Versicherter / Ersteller
    if versicherter_name or absender_name:
        meta_zeilen = []
        if versicherter_name:
            meta_zeilen.append([
                Paragraph("Pflegebedürftige Person:", s["klein"]),
                Paragraph(versicherter_name, s["normal"]),
            ])
        if absender_name:
            meta_zeilen.append([
                Paragraph("Erstellt von:", s["klein"]),
                Paragraph(absender_name, s["normal"]),
            ])
        meta = Table(meta_zeilen, colWidths=[4*cm, breite-4*cm])
        meta.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "TOP"), ("TOPPADDING", (0,0), (-1,-1), 2)]))
        elemente.append(meta)
        elemente.append(Spacer(1, 0.3*cm))

    elemente.append(HRFlowable(width=breite, thickness=0.5, color=FARBE_TRENN))
    elemente.append(Spacer(1, 0.4*cm))

    # ── Ergebnis-Box ───────────────────────────────────────────────
    pg_text = f"Pflegegrad {pg}" if pg > 0 else "Kein Pflegebedarf"
    erg_daten = [[
        Paragraph(
            f'<font color="{farbe_pg.hexval()}" size="28"><b>{pg_text}</b></font>',
            ParagraphStyle("PGErg", parent=s["normal"], alignment=TA_CENTER),
        ),
        Paragraph(
            f'<b>{ergebnis.gesamtpunkte:.1f}</b><br/>'
            f'<font size="8" color="#718096">Gesamtpunkte</font>',
            ParagraphStyle("PGPkt", parent=s["normal"], alignment=TA_CENTER, fontSize=20),
        ),
    ]]
    erg_box = Table(erg_daten, colWidths=[breite*0.6, breite*0.4])
    erg_box.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#f7fafc")),
        ("BOX", (0,0), (-1,-1), 1.5, FARBE_PRIMR),
        ("ROUNDEDCORNERS", [6]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
    ]))
    elemente.append(erg_box)
    elemente.append(Spacer(1, 0.15*cm))

    # Bezeichnung
    elemente.append(Paragraph(ergebnis.pflegegrad_bezeichnung, s["klein"]))
    elemente.append(Spacer(1, 0.5*cm))

    # ── Begründung ─────────────────────────────────────────────────
    elemente.append(Paragraph("Begründung", s["abschnitt"]))
    elemente.append(Paragraph(ergebnis.begruendung, s["normal"]))
    elemente.append(Spacer(1, 0.4*cm))

    # ── Haupttreiber ───────────────────────────────────────────────
    if ergebnis.haupttreiber:
        elemente.append(Paragraph("Besonders relevante Bereiche", s["abschnitt"]))
        ht_daten = [["Modul", "Bereich", "Schweregrad", "Pkt."]]
        for t in ergebnis.haupttreiber:
            ht_daten.append([
                Paragraph(f'Modul {t["modul_id"]}', s["normal"]),
                Paragraph(t["bezeichnung"], s["normal"]),
                Paragraph(t["schweregrad"], s["klein"]),
                Paragraph(f'{t["punkte"]:.1f}', ParagraphStyle("PGR", parent=s["normal"], alignment=TA_RIGHT)),
            ])
        ht = Table(ht_daten, colWidths=[2*cm, breite-7.5*cm, 3.5*cm, 2*cm])
        ht.setStyle(_tabellen_stil(len(ht_daten)))
        elemente.append(ht)
        elemente.append(Spacer(1, 0.4*cm))

    # ── Modulübersicht ─────────────────────────────────────────────
    elemente.append(Paragraph("Modulübersicht", s["abschnitt"]))
    mod_daten = [["Modul", "Bezeichnung", "Rohpkt.", "Gew. Pkt.", "Schweregrad"]]
    for m in ergebnis.modul_ergebnisse:
        mod_daten.append([
            Paragraph(str(m.modul_id), s["normal"]),
            Paragraph(m.bezeichnung, s["normal"]),
            Paragraph(str(m.rohpunkte), ParagraphStyle("PGR2", parent=s["normal"], alignment=TA_RIGHT)),
            Paragraph(f'{m.gewichtete_punkte:.1f}', ParagraphStyle("PGR3", parent=s["normal"], alignment=TA_RIGHT)),
            Paragraph(m.schweregrad, s["klein"]),
        ])
    mod = Table(mod_daten, colWidths=[1.5*cm, breite-9.5*cm, 2*cm, 2.5*cm, 3.5*cm])
    mod.setStyle(_tabellen_stil(len(mod_daten)))
    elemente.append(mod)
    elemente.append(Spacer(1, 0.4*cm))

    # ── Dokumentations-Tipps ───────────────────────────────────────
    if ergebnis.dokumentations_tipps:
        elemente.append(Paragraph("Empfehlungen für die Dokumentation", s["abschnitt"]))
        for tipp in ergebnis.dokumentations_tipps:
            elemente.append(Paragraph(f"• {tipp}", s["normal"]))
            elemente.append(Spacer(1, 0.15*cm))
        elemente.append(Spacer(1, 0.2*cm))

    # ── Leistungsübersicht ─────────────────────────────────────────
    if ergebnis.pflegegrad > 0:
        from pflege_rules import leistungen_fuer_pflegegrad
        leistungen = leistungen_fuer_pflegegrad(ergebnis.pflegegrad)
        verfuegbar = [l for l in leistungen if l["verfuegbar"]]
        nicht = [l for l in leistungen if not l["verfuegbar"]]

        elemente.append(Paragraph("Mögliche Leistungen nach SGB XI", s["abschnitt"]))

        leis_daten = [["Leistung", "Betrag", "Paragraph"]]
        for l in verfuegbar:
            betrag_str = f"{l['betrag']:,.0f} {l['einheit']}".replace(",", ".")
            leis_daten.append([
                Paragraph(f"✓ {l['titel']}", s["normal"]),
                Paragraph(betrag_str, ParagraphStyle("PGRL", parent=s["normal"], alignment=TA_RIGHT)),
                Paragraph(l["paragraf"], s["klein"]),
            ])
        for l in nicht:
            leis_daten.append([
                Paragraph(f"✗ {l['titel']}", s["klein"]),
                Paragraph("—", ParagraphStyle("PGRLS", parent=s["klein"], alignment=TA_RIGHT)),
                Paragraph(l["paragraf"], s["klein"]),
            ])

        leis = Table(leis_daten, colWidths=[breite*0.5, breite*0.28, breite*0.22])
        leis_stil = _tabellen_stil(len(leis_daten))
        leis_stil.add("TEXTCOLOR", (0, len(verfuegbar)+1), (0, -1), colors.HexColor("#aaaaaa"))
        leis.setStyle(leis_stil)
        elemente.append(leis)
        elemente.append(Spacer(1, 0.15*cm))
        elemente.append(Paragraph(
            "Angaben basieren auf den gesetzlichen Beträgen 2026. Kein Anspruch auf Vollständigkeit.",
            s["klein"],
        ))
        elemente.append(Spacer(1, 0.3*cm))

    # ── Hinweis-Box ────────────────────────────────────────────────
    elemente.append(HRFlowable(width=breite, thickness=0.5, color=FARBE_TRENN))
    elemente.append(Spacer(1, 0.2*cm))
    elemente.append(Paragraph(
        "⚠️ Dieses Dokument ist eine Orientierungshilfe und ersetzt keine offizielle "
        "Begutachtung durch den MDK/Medicproof. Erstellt mit Pflegra — Self-hosted Care Management.",
        s["klein"],
    ))

    doc.build(elemente, onFirstPage=_seiten_rahmen, onLaterPages=_seiten_rahmen)

    if ausgabe_pfad:
        return b""
    return puffer.getvalue()


# ------------------------------------------------------------------ #
#  Widerspruch gegen Pflegegrad-Bescheid                             #
# ------------------------------------------------------------------ #

def erstelle_widerspruch_pdf(
    absender_name:    str,
    absender_adresse: str,
    versicherter:     object,
    bescheid_datum:   str,
    bescheid_az:      str,
    aktueller_pg:     int,
    beantragter_pg:   int,
    widerspruch_typ:  str,   # "fristsichernd" | "begruendet"
    begruendung:      str,
    module_kritik:    list,  # [{modul_id, modul_name, kritik}]
    datum_heute:      str,
    ausgabe_pfad=None,
) -> bytes:
    """
    Erzeugt einen Widerspruchsbrief gegen einen Pflegegrad-Bescheid.
    """
    import io
    puffer = io.BytesIO()
    ziel = ausgabe_pfad or puffer

    doc = SimpleDocTemplate(
        ziel if isinstance(ziel, str) else puffer,
        pagesize=A4,
        rightMargin=2.5*cm, leftMargin=2.5*cm,
        topMargin=2.5*cm, bottomMargin=2*cm,
        title="Widerspruch Pflegegrad",
    )

    s = _erstelle_styles()
    elemente = []
    breite = A4[0] - 5*cm

    # ── Absender ──────────────────────────────────────────────────
    for zeile in absender_adresse.strip().split("\n"):
        elemente.append(Paragraph(zeile, s["normal"]))
    elemente.append(Spacer(1, 0.2*cm))
    elemente.append(Paragraph(datum_heute, s["normal"]))
    elemente.append(Spacer(1, 0.8*cm))

    # ── Empfänger (Pflegekasse) ───────────────────────────────────
    if versicherter and versicherter.krankenkasse:
        elemente.append(Paragraph(f"<b>{versicherter.krankenkasse}</b>", s["normal"]))
        if versicherter.krankenkasse_adresse:
            for zeile in versicherter.krankenkasse_adresse.strip().split("\n"):
                elemente.append(Paragraph(zeile, s["normal"]))
    elemente.append(Spacer(1, 0.8*cm))

    # ── Betreff ───────────────────────────────────────────────────
    betreff = (
        f"Widerspruch gegen Ihren Bescheid vom {bescheid_datum}"
        f"{f' (Az.: {bescheid_az})' if bescheid_az else ''}"
    )
    if versicherter:
        betreff += f"\nVersicherter: {versicherter.name}"
        if versicherter.versicherungsnr:
            betreff += f", Vers.-Nr.: {versicherter.versicherungsnr}"

    for zeile in betreff.strip().split("\n"):
        elemente.append(Paragraph(f"<b>{zeile}</b>", s["normal"]))
    elemente.append(Spacer(1, 0.5*cm))

    # ── Anrede ────────────────────────────────────────────────────
    elemente.append(Paragraph("Sehr geehrte Damen und Herren,", s["normal"]))
    elemente.append(Spacer(1, 0.3*cm))

    # ── Fristsichernder Widerspruch ───────────────────────────────
    if widerspruch_typ == "fristsichernd":
        elemente.append(Paragraph(
            f"hiermit lege ich fristwahrend <b>Widerspruch</b> gegen Ihren Bescheid vom "
            f"<b>{bescheid_datum}</b> ein, mit dem für die oben genannte versicherte Person "
            f"<b>Pflegegrad {aktueller_pg}</b> festgestellt wurde.",
            s["normal"]
        ))
        elemente.append(Spacer(1, 0.3*cm))
        elemente.append(Paragraph(
            "Der festgestellte Pflegegrad entspricht nach meiner Einschätzung nicht dem "
            "tatsächlichen Pflegebedarf. Ich behalte mir vor, den Widerspruch innerhalb "
            "der gesetzlichen Frist ausführlich zu begründen.",
            s["normal"]
        ))
        elemente.append(Spacer(1, 0.3*cm))
        elemente.append(Paragraph(
            "Ich bitte Sie, mir das vollständige Gutachten des Medizinischen Dienstes (MD) "
            "bzw. Medicproof zuzusenden, damit ich eine detaillierte Stellungnahme "
            "erarbeiten kann.",
            s["normal"]
        ))

    # ── Begründeter Widerspruch ───────────────────────────────────
    else:
        elemente.append(Paragraph(
            f"hiermit lege ich <b>Widerspruch</b> gegen Ihren Bescheid vom "
            f"<b>{bescheid_datum}</b> ein, mit dem für die oben genannte versicherte Person "
            f"<b>Pflegegrad {aktueller_pg}</b> festgestellt wurde.",
            s["normal"]
        ))
        elemente.append(Spacer(1, 0.3*cm))

        if beantragter_pg > aktueller_pg:
            elemente.append(Paragraph(
                f"Nach meiner Einschätzung entspricht der tatsächliche Pflegebedarf "
                f"mindestens <b>Pflegegrad {beantragter_pg}</b>.",
                s["normal"]
            ))
            elemente.append(Spacer(1, 0.3*cm))

        # Begründung
        if begruendung:
            elemente.append(Paragraph("<b>Begründung:</b>", s["abschnitt"]))
            elemente.append(Paragraph(begruendung, s["normal"]))
            elemente.append(Spacer(1, 0.3*cm))

        # Modul-Kritik
        if module_kritik:
            elemente.append(Paragraph(
                "<b>Konkrete Einwände gegen das Gutachten:</b>", s["abschnitt"]
            ))
            elemente.append(Spacer(1, 0.15*cm))
            for m in module_kritik:
                if m.get("kritik"):
                    elemente.append(Paragraph(
                        f"<b>Modul {m['modul_id']} – {m['modul_name']}:</b>",
                        s["normal"]
                    ))
                    elemente.append(Paragraph(m["kritik"], s["normal"]))
                    elemente.append(Spacer(1, 0.2*cm))

        elemente.append(Paragraph(
            "Ich bitte Sie, den Pflegegrad entsprechend zu korrigieren und eine "
            "erneute Begutachtung durch den Medizinischen Dienst anzuordnen.",
            s["normal"]
        ))

    # ── Abschluss ─────────────────────────────────────────────────
    elemente.append(Spacer(1, 0.5*cm))
    elemente.append(Paragraph(
        "Ich bitte um eine schriftliche Bestätigung des Eingangs dieses Widerspruchs.",
        s["normal"]
    ))
    elemente.append(Spacer(1, 0.8*cm))
    elemente.append(Paragraph("Mit freundlichen Grüßen", s["normal"]))
    elemente.append(Spacer(1, 1.2*cm))
    elemente.append(Paragraph(absender_name, s["normal"]))

    doc.build(elemente, onFirstPage=_seiten_rahmen, onLaterPages=_seiten_rahmen)

    if ausgabe_pfad:
        return b""
    return puffer.getvalue()
