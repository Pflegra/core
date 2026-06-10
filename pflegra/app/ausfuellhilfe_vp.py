"""
Pflegra – Ausfüllhilfe Verhinderungspflege
KK-unabhängiges Datenblatt zum Ausfüllen des KK-eigenen Formulars.

Seite 1: Stammdaten (Versicherter, Pflegeperson, Ersatzpflegekraft, Zeitraum)
Seite 2: Einzelnachweise (Tabelle Datum / Von–Bis / Stunden)

Datenschutz:
- Ersatzpflegekraft-Daten (Geburtsdatum, Adresse) werden NUR im PDF verwendet,
  nicht in der Datenbank gespeichert.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)

FARBE_PRIMÄR = colors.HexColor("#2C5F8A")
FARBE_HELL   = colors.HexColor("#E8F0F8")
FARBE_GRAU   = colors.HexColor("#666666")
FARBE_TEXT   = colors.HexColor("#2D2D2D")
FARBE_TRENN  = colors.HexColor("#CCCCCC")
FARBE_GRÜN   = colors.HexColor("#16a34a")
FARBE_GRÜN_H = colors.HexColor("#dcfce7")


def _styles() -> dict:
    basis = getSampleStyleSheet()
    s = {}

    def st(name, parent="Normal", **kw):
        s[name] = ParagraphStyle(name, parent=basis[parent], **kw)

    st("titel",      fontSize=14, fontName="Helvetica-Bold",  textColor=FARBE_PRIMÄR, spaceAfter=2)
    st("untertitel", fontSize=9,  fontName="Helvetica",       textColor=FARBE_GRAU,   spaceAfter=8)
    st("abschnitt",  fontSize=10, fontName="Helvetica-Bold",  textColor=FARBE_PRIMÄR, spaceBefore=10, spaceAfter=4)
    st("label",      fontSize=8,  fontName="Helvetica-Bold",  textColor=FARBE_GRAU)
    st("wert",       fontSize=10, fontName="Helvetica",       textColor=FARBE_TEXT,   leading=14)
    st("hinweis",    fontSize=8,  fontName="Helvetica-Oblique", textColor=FARBE_GRAU, spaceAfter=4)
    st("fuss",       fontSize=7,  fontName="Helvetica",       textColor=FARBE_GRAU,   alignment=TA_CENTER)
    st("tabkopf",    fontSize=9,  fontName="Helvetica-Bold",  textColor=colors.white)
    st("tabzelle",   fontSize=9,  fontName="Helvetica",       textColor=FARBE_TEXT,   leading=12)
    st("tabzelle_r", fontSize=9,  fontName="Helvetica",       textColor=FARBE_TEXT,   leading=12, alignment=TA_RIGHT)
    st("summe",      fontSize=10, fontName="Helvetica-Bold",  textColor=FARBE_TEXT)
    st("dsgvo",      fontSize=7,  fontName="Helvetica-Oblique", textColor=FARBE_GRAU, spaceAfter=2)
    return s


def _fmt_stunden(stunden: float) -> str:
    return f"{stunden:.2f}".replace(".", ",")

def _fmt_betrag(betrag: float) -> str:
    return f"{betrag:.2f}".replace(".", ",")


def _heute() -> str:
    h = date.today()
    return f"{h.day:02d}.{h.month:02d}.{h.year}"


def _feld_tabelle(paare: List[Tuple[str, str]], s: dict, col_breite=(5*cm, 11*cm)) -> Table:
    """Erzeugt eine zweispaltige Label/Wert-Tabelle."""
    data = []
    for label, wert in paare:
        data.append([
            Paragraph(label, s["label"]),
            Paragraph(wert or "–", s["wert"]),
        ])
    t = Table(data, colWidths=col_breite)
    t.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("LINEBELOW",    (0, 0), (-1, -1), 0.3, FARBE_TRENN),
    ]))
    return t


def erstelle_ausfuellhilfe_pdf(
    pfad: Path,
    # Versicherter
    versicherter_name: str,
    versicherter_adresse: str,
    versicherter_geburtsdatum: str,
    versicherungsnr: str,
    kk_name: str,
    # Pflegeperson (Absender)
    pflegeperson_name: str,
    pflegeperson_adresse: str,
    # Ersatzpflegekraft (temporär, nicht gespeichert)
    ersatz_name: str,
    ersatz_geburtsdatum: str = "",
    ersatz_adresse: str = "",
    ersatz_art: str = "Privatperson",
    # Zeitraum
    zeitraum_von: str = "",
    zeitraum_bis: str = "",
    grund: str = "",
    # Einträge
    eintraege: Optional[List] = None,
    stundensatz: float = 20.0,
) -> Path:
    """Erstellt die Ausfüllhilfe als PDF."""

    eintraege = eintraege or []
    stunden_gesamt = sum(e.stunden for e in eintraege)
    betrag_gesamt  = stunden_gesamt * stundensatz

    doc = SimpleDocTemplate(
        str(pfad),
        pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title="Nachweis der Verhinderungspflege",
        author="Pflegra",
    )

    s = _styles()
    story = []

    # ── SEITE 1 ──────────────────────────────────────────────────────────────

    # Kopf
    story.append(Paragraph("Nachweis der Verhinderungspflege", s["titel"]))
    story.append(Paragraph(
        f"Verhinderungspflege § 39 SGB XI · Zeitraum: {zeitraum_von} – {zeitraum_bis} · "
        f"Erstellt am {_heute()}",
        s["untertitel"]
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=FARBE_PRIMÄR, spaceAfter=10))

    # Versicherter
    story.append(Paragraph("Angaben zum/zur Versicherten", s["abschnitt"]))
    story.append(_feld_tabelle([
        ("Vor- und Nachname",     versicherter_name),
        ("Adresse",               versicherter_adresse),
        ("Geburtsdatum",          versicherter_geburtsdatum),
        ("Versichertennummer",    versicherungsnr),
        ("Krankenkasse",          kk_name),
    ], s))

    # Pflegeperson
    story.append(Paragraph("Angaben zur verhinderten Pflegeperson", s["abschnitt"]))
    story.append(_feld_tabelle([
        ("Vor- und Nachname",  pflegeperson_name),
        ("Adresse",            pflegeperson_adresse),
    ], s))

    # Ersatzpflegekraft
    story.append(Paragraph("Angaben zur Ersatz-/Verhinderungspflegekraft", s["abschnitt"]))
    story.append(_feld_tabelle([
        ("Vor- und Nachname",  ersatz_name),
        ("Geburtsdatum",       ersatz_geburtsdatum or "–"),
        ("Adresse",            ersatz_adresse or "–"),
        ("Art der Ersatzpflege", ersatz_art),
    ], s))

    # DSGVO-Hinweis Ersatzpflegekraft
    story.append(Paragraph(
        "Datenschutzhinweis: Angaben zur Ersatzpflegekraft werden gemäß DSGVO "
        "ausschließlich zur Abrechnung der Verhinderungspflege nach § 39 SGB XI genutzt.",
        s["dsgvo"]
    ))

    # Zeitraum & Grund
    story.append(Paragraph("Zeitraum und Grund", s["abschnitt"]))
    story.append(_feld_tabelle([
        ("Zeitraum von",       zeitraum_von),
        ("Zeitraum bis",       zeitraum_bis),
        ("Grund der Beantragung", grund or "–"),
    ], s))

    # Zusammenfassung
    story.append(Paragraph("Zusammenfassung", s["abschnitt"]))
    story.append(_feld_tabelle([
        ("Anzahl Einsätze",    str(len(eintraege))),
        ("Stunden gesamt",     f"{_fmt_stunden(stunden_gesamt)} Std."),
        ("Betrag gesamt",      f"{_fmt_betrag(betrag_gesamt)} €"),
        ("Stundensatz",        f"{_fmt_betrag(stundensatz)} €/Std."),
    ], s))

    story.append(Spacer(1, 0.5*cm))

    # Unterschriften Seite 1
    story.append(HRFlowable(width="100%", thickness=0.5, color=FARBE_TRENN))
    story.append(Spacer(1, 0.3*cm))
    unterschrift_data = [[
        Paragraph("Datum, Unterschrift Versicherter/Vertreter", s["hinweis"]),
        Paragraph("Telefonnummer (freiwillig)", s["hinweis"]),
    ]]
    unt = Table(unterschrift_data, colWidths=[10*cm, 6*cm])
    unt.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (0,0), 0.5, FARBE_TEXT),
        ("LINEABOVE", (1,0), (1,0), 0.5, FARBE_TEXT),
        ("TOPPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(unt)

    # Fußzeile Seite 1
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"Erstellt mit Pflegra · Nachweis der Verhinderungspflege § 39 SGB XI · {date.today().year}",
        s["fuss"]
    ))

    # ── SEITENUMBRUCH ────────────────────────────────────────────────────────
    story.append(PageBreak())

    # ── SEITE 2 — EINZELNACHWEISE ────────────────────────────────────────────

    story.append(Paragraph("Einzelnachweise", s["titel"]))
    story.append(Paragraph(
        f"Stundenweise Verhinderungspflege · {zeitraum_von} – {zeitraum_bis} · "
        f"{versicherter_name}",
        s["untertitel"]
    ))
    story.append(HRFlowable(width="100%", thickness=1.5, color=FARBE_PRIMÄR, spaceAfter=10))

    if eintraege:
        # Tabellenkopf
        tab_data = [[
            Paragraph("Datum",          s["tabkopf"]),
            Paragraph("Von",            s["tabkopf"]),
            Paragraph("Bis",            s["tabkopf"]),
            Paragraph("Stunden",        s["tabkopf"]),
            Paragraph("Art",            s["tabkopf"]),
            Paragraph("Ersatzpflege",   s["tabkopf"]),
        ]]

        for i, e in enumerate(sorted(eintraege, key=lambda x: (x.datum, x.von))):
            datum_str = e.datum.strftime("%d.%m.%Y")
            art_str   = "tageweise" if e.art == "tageweise" else "stundenweise"
            # Ersatzname: pro Eintrag wenn vorhanden, sonst einmalig eingegebener
            ez_name   = e.ersatz_name if e.ersatz_name else ersatz_name
            tab_data.append([
                Paragraph(datum_str,                s["tabzelle"]),
                Paragraph(e.von or "–",             s["tabzelle"]),
                Paragraph(e.bis or "–",             s["tabzelle"]),
                Paragraph(_fmt_stunden(e.stunden),  s["tabzelle_r"]),
                Paragraph(art_str,                  s["tabzelle"]),
                Paragraph(ez_name or "–",           s["tabzelle"]),
            ])

        # Summenzeile
        tab_data.append([
            Paragraph("Gesamt", s["summe"]),
            Paragraph("", s["tabzelle"]),
            Paragraph("", s["tabzelle"]),
            Paragraph(_fmt_stunden(stunden_gesamt), s["summe"]),
            Paragraph("", s["tabzelle"]),
            Paragraph("", s["tabzelle"]),
        ])

        tab = Table(
            tab_data,
            colWidths=[2.8*cm, 1.6*cm, 1.6*cm, 2*cm, 2.8*cm, 5.2*cm],
            repeatRows=1,
        )
        tab.setStyle(TableStyle([
            # Kopfzeile
            ("BACKGROUND",   (0, 0), (-1, 0),  FARBE_PRIMÄR),
            ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
            ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, 0),  9),
            ("TOPPADDING",   (0, 0), (-1, 0),  6),
            ("BOTTOMPADDING",(0, 0), (-1, 0),  6),
            # Datenzeilen
            ("FONTSIZE",     (0, 1), (-1, -2), 9),
            ("ROWBACKGROUNDS",(0, 1), (-1, -2), [colors.white, FARBE_HELL]),
            ("TOPPADDING",   (0, 1), (-1, -2), 4),
            ("BOTTOMPADDING",(0, 1), (-1, -2), 4),
            ("GRID",         (0, 0), (-1, -1), 0.3, FARBE_TRENN),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            # Summenzeile
            ("BACKGROUND",   (0, -1), (-1, -1), FARBE_GRÜN_H),
            ("FONTNAME",     (0, -1), (-1, -1), "Helvetica-Bold"),
            ("LINEABOVE",    (0, -1), (-1, -1), 1.0, FARBE_GRÜN),
            ("TOPPADDING",   (0, -1), (-1, -1), 6),
            ("BOTTOMPADDING",(0, -1), (-1, -1), 6),
        ]))
        story.append(tab)
    else:
        story.append(Paragraph("Keine Einträge im gewählten Zeitraum.", s["hinweis"]))

    story.append(Spacer(1, 0.6*cm))

    # Betrag-Box
    betrag_data = [[
        Paragraph(
            f"Für <b>{_fmt_stunden(stunden_gesamt)} Stunden</b> Ersatz-/Verhinderungspflege "
            f"habe ich <b>{_fmt_betrag(betrag_gesamt)} EUR</b> erhalten.",
            s["wert"]
        )
    ]]
    betrag_t = Table(betrag_data, colWidths=[16*cm])
    betrag_t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), FARBE_GRÜN_H),
        ("BOX",          (0,0), (-1,-1), 0.8, FARBE_GRÜN),
        ("TOPPADDING",   (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0), (-1,-1), 8),
        ("LEFTPADDING",  (0,0), (-1,-1), 10),
    ]))
    story.append(betrag_t)
    story.append(Spacer(1, 0.5*cm))

    # Unterschriften Seite 2 (Ersatzpflegekraft)
    story.append(HRFlowable(width="100%", thickness=0.5, color=FARBE_TRENN))
    story.append(Spacer(1, 0.3*cm))
    unt2_data = [[
        Paragraph("Datum, Unterschrift Ersatz-/Verhinderungspflegekraft", s["hinweis"]),
        Paragraph("Telefonnummer (freiwillig)", s["hinweis"]),
    ]]
    unt2 = Table(unt2_data, colWidths=[10*cm, 6*cm])
    unt2.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (0,0), 0.5, FARBE_TEXT),
        ("LINEABOVE", (1,0), (1,0), 0.5, FARBE_TEXT),
        ("TOPPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(unt2)

    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"Erstellt mit Pflegra · Nachweis der Verhinderungspflege § 39 SGB XI · {date.today().year}",
        s["fuss"]
    ))

    doc.build(story)
    return pfad
