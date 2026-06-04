"""
Pflegra – Entlastungsbetrag Nachweis PDF (§ 45b SGB XI)
Druckbare Jahresübersicht aller Buchungen mit Budget-Auswertung.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable,
)

FARBE_PRIMÄR = colors.HexColor("#2C5F8A")
FARBE_HELL   = colors.HexColor("#E8F0F8")
FARBE_GRAU   = colors.HexColor("#666666")
FARBE_TEXT   = colors.HexColor("#2D2D2D")
FARBE_GRÜN   = colors.HexColor("#16a34a")
FARBE_GRÜN_H = colors.HexColor("#dcfce7")
FARBE_ORANGE = colors.HexColor("#e67e22")
FARBE_ROT    = colors.HexColor("#e74c3c")

MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
          "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


def _styles() -> dict:
    basis = getSampleStyleSheet()
    s = {}

    def st(name, parent="Normal", **kw):
        s[name] = ParagraphStyle(name, parent=basis[parent], **kw)

    st("titel",      fontSize=14, fontName="Helvetica-Bold",    textColor=FARBE_PRIMÄR, spaceAfter=2)
    st("untertitel", fontSize=9,  fontName="Helvetica",         textColor=FARBE_GRAU,   spaceAfter=8)
    st("abschnitt",  fontSize=10, fontName="Helvetica-Bold",    textColor=FARBE_PRIMÄR, spaceBefore=10, spaceAfter=4)
    st("label",      fontSize=8,  fontName="Helvetica-Bold",    textColor=FARBE_GRAU)
    st("wert",       fontSize=10, fontName="Helvetica",         textColor=FARBE_TEXT,   leading=14)
    st("hinweis",    fontSize=8,  fontName="Helvetica-Oblique", textColor=FARBE_GRAU,   spaceAfter=4)
    st("fuss",       fontSize=7,  fontName="Helvetica",         textColor=FARBE_GRAU,   alignment=TA_CENTER)
    st("tabkopf",    fontSize=8,  fontName="Helvetica-Bold",    textColor=colors.white)
    st("tabzelle",   fontSize=7.5, fontName="Helvetica",         textColor=FARBE_TEXT,   leading=11)
    st("tabzelle_r", fontSize=7.5, fontName="Helvetica",         textColor=FARBE_TEXT,   leading=11, alignment=TA_RIGHT)
    st("summe_r",    fontSize=8.5, fontName="Helvetica-Bold",    textColor=FARBE_TEXT,   alignment=TA_RIGHT)
    return s


def erstelle_entlastung_pdf(
    pfad: str,
    person: str,
    jahr: int,
    buchungen: list,
    monatlich: float,
    vorjahr_guthaben: float,
    vorjahr_aktiv: bool,
    jahresmax: float,
    verfuegbar_gesamt: float,
    gesamt_verbraucht: float,
    jahres_rest: float,
    monate: list,
) -> str:
    """Erstellt die Entlastungsbetrag-Nachweis-PDF und gibt den Pfad zurück."""

    Path(pfad).parent.mkdir(parents=True, exist_ok=True)
    s = _styles()

    doc = SimpleDocTemplate(
        pfad,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title=f"Entlastungsbetrag {jahr} – {person}",
    )

    story = []
    W = doc.width

    # ── Kopf ──────────────────────────────────────────────────────────────────
    story.append(Paragraph(f"Entlastungsbetrag § 45b SGB XI · {jahr} · {person}", s["titel"]))
    story.append(Paragraph(
        f"Erstellt am {date.today().strftime('%d.%m.%Y')} · "
        f"{len(buchungen)} Buchungen · Pflegra",
        s["untertitel"]
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=FARBE_PRIMÄR, spaceAfter=8))

    # ── Jahresübersicht ────────────────────────────────────────────────────────
    story.append(Paragraph("Jahresübersicht", s["abschnitt"]))

    budget_data = [
        [Paragraph("Position", s["tabkopf"]),
         Paragraph("Betrag", s["tabkopf"])],
        [Paragraph(f"Jahresbudget ({monatlich:.2f} €/Monat × 12)", s["tabzelle"]),
         Paragraph(f"{jahresmax:.2f} €", s["tabzelle_r"])],
    ]
    if vorjahr_guthaben > 0:
        status = "nutzbar bis 30.06." if vorjahr_aktiv else "abgelaufen"
        budget_data.append([
            Paragraph(f"Vorjahresguthaben ({status})", s["tabzelle"]),
            Paragraph(f"{vorjahr_guthaben:.2f} €", s["tabzelle_r"]),
        ])
    budget_data += [
        [Paragraph("Gesamt verfügbar", s["tabzelle"]),
         Paragraph(f"{verfuegbar_gesamt:.2f} €", s["tabzelle_r"])],
        [Paragraph("Verbraucht (Buchungen)", s["tabzelle"]),
         Paragraph(f"{gesamt_verbraucht:.2f} €", s["tabzelle_r"])],
        [Paragraph("Restguthaben", s["summe_r"]),
         Paragraph(f"{jahres_rest:.2f} €", s["summe_r"])],
    ]

    rest_farbe = FARBE_GRÜN if jahres_rest > 0 else FARBE_ROT
    budget_tab = Table(budget_data, colWidths=[W * 0.72, W * 0.28])
    budget_tab.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), FARBE_PRIMÄR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, FARBE_HELL]),
        ("BACKGROUND",  (0, -1), (-1, -1), FARBE_GRÜN_H),
        ("TEXTCOLOR",   (0, -1), (-1, -1), rest_farbe),
        ("GRID",        (0, 0), (-1, -1), 0.25, FARBE_GRAU),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(budget_tab)
    story.append(Spacer(1, 0.4*cm))

    # ── Monatsübersicht ────────────────────────────────────────────────────────
    story.append(Paragraph("Monatsübersicht", s["abschnitt"]))

    monat_data = [[
        Paragraph("Monat", s["tabkopf"]),
        Paragraph("Budget", s["tabkopf"]),
        Paragraph("Verbraucht", s["tabkopf"]),
        Paragraph("Rest", s["tabkopf"]),
    ]]
    for m in monate:
        rest_color = FARBE_ROT if m["rest"] <= 0 else FARBE_TEXT
        monat_data.append([
            Paragraph(m["name"], s["tabzelle"]),
            Paragraph(f"{m['monatlich']:.2f} €", s["tabzelle_r"]),
            Paragraph(f"{m['verbraucht']:.2f} €", s["tabzelle_r"]),
            Paragraph(f"<font color='#{rest_color.hexval()[2:]}'>{m['rest']:.2f} €</font>", s["tabzelle_r"]),
        ])

    monat_tab = Table(monat_data, colWidths=[W*0.2, W*0.25, W*0.28, W*0.27])
    monat_tab.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), FARBE_PRIMÄR),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FARBE_HELL]),
        ("GRID",           (0, 0), (-1, -1), 0.25, FARBE_GRAU),
        ("TOPPADDING",     (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
        ("LEFTPADDING",    (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 5),
    ]))
    story.append(monat_tab)
    story.append(Spacer(1, 0.4*cm))

    # ── Buchungsliste ──────────────────────────────────────────────────────────
    if buchungen:
        story.append(Paragraph(f"Buchungen {jahr}", s["abschnitt"]))

        buch_data = [[
            Paragraph("Datum", s["tabkopf"]),
            Paragraph("Anbieter", s["tabkopf"]),
            Paragraph("Beschreibung", s["tabkopf"]),
            Paragraph("Beleg", s["tabkopf"]),
            Paragraph("Betrag", s["tabkopf"]),
        ]]
        for b in buchungen:
            datum_de = b.datum[8:10] + "." + b.datum[5:7] + "." + b.datum[0:4] if len(b.datum) == 10 else b.datum
            buch_data.append([
                Paragraph(datum_de, s["tabzelle"]),
                Paragraph(b.anbieter or "–", s["tabzelle"]),
                Paragraph(b.beschreibung or "–", s["tabzelle"]),
                Paragraph(b.beleg_nr or "–", s["tabzelle"]),
                Paragraph(f"{b.betrag:.2f} €", s["tabzelle_r"]),
            ])
        # Summenzeile
        buch_data.append([
            Paragraph("", s["tabzelle"]),
            Paragraph("", s["tabzelle"]),
            Paragraph("", s["tabzelle"]),
            Paragraph("Gesamt", s["summe_r"]),
            Paragraph(f"{gesamt_verbraucht:.2f} €", s["summe_r"]),
        ])

        buch_tab = Table(buch_data, colWidths=[W*0.12, W*0.28, W*0.25, W*0.17, W*0.18])
        buch_tab.setStyle(TableStyle([
            ("BACKGROUND",     (0, 0), (-1, 0), FARBE_PRIMÄR),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, FARBE_HELL]),
            ("BACKGROUND",     (0, -1), (-1, -1), FARBE_HELL),
            ("LINEABOVE",      (0, -1), (-1, -1), 1, FARBE_PRIMÄR),
            ("GRID",           (0, 0), (-1, -1), 0.25, FARBE_GRAU),
            ("TOPPADDING",     (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
            ("LEFTPADDING",    (0, 0), (-1, -1), 5),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 5),
        ]))
        story.append(buch_tab)

    # ── Fußzeile ──────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=FARBE_GRAU))
    story.append(Paragraph(
        f"Erstellt mit Pflegra · Entlastungsbetrag § 45b SGB XI · {jahr}",
        s["fuss"]
    ))

    doc.build(story)
    return pfad
