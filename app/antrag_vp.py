"""
Pflegra – Antrag auf Kostenerstattung Verhinderungspflege § 39 SGB XI
Universeller Brief-PDF, KK-unabhängig.

Modi:
    vorsorglich  – laufendes Jahr, Details folgen bei Abrechnung
    manuell      – konkrete Monate, Stunden und Betrag aus DB
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

from models import MONATE_DE

FARBE_PRIMÄR  = colors.HexColor("#2C5F8A")
FARBE_HELL    = colors.HexColor("#E8F0F8")
FARBE_GRAU    = colors.HexColor("#666666")
FARBE_TEXT    = colors.HexColor("#2D2D2D")
FARBE_TRENN   = colors.HexColor("#CCCCCC")


def _styles() -> dict:
    basis = getSampleStyleSheet()
    s = {}
    def st(name, parent="Normal", **kw):
        s[name] = ParagraphStyle(name, parent=basis[parent], **kw)
    st("absender",   fontSize=9,  fontName="Helvetica",      textColor=FARBE_TEXT,  leading=13)
    st("empfaenger", fontSize=10, fontName="Helvetica",      textColor=FARBE_TEXT,  leading=15)
    st("datum",      fontSize=10, fontName="Helvetica",      textColor=FARBE_TEXT,  alignment=TA_RIGHT)
    st("betreff",    fontSize=11, fontName="Helvetica-Bold",  textColor=FARBE_PRIMÄR, spaceBefore=4, spaceAfter=4)
    st("anrede",     fontSize=10, fontName="Helvetica",      textColor=FARBE_TEXT,  spaceAfter=4)
    st("text",       fontSize=10, fontName="Helvetica",      textColor=FARBE_TEXT,  leading=15, spaceAfter=4)
    st("label",      fontSize=9,  fontName="Helvetica-Bold", textColor=FARBE_GRAU)
    st("wert",       fontSize=9,  fontName="Helvetica",      textColor=FARBE_TEXT)
    st("gruss",      fontSize=10, fontName="Helvetica",      textColor=FARBE_TEXT,  spaceBefore=6)
    st("unterschrift", fontSize=9, fontName="Helvetica",     textColor=FARBE_GRAU)
    st("fuss",       fontSize=7,  fontName="Helvetica",      textColor=FARBE_GRAU,  alignment=TA_CENTER)
    return s


def _fmt_stunden(stunden: float) -> str:
    return f"{stunden:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " h"


def _fmt_betrag(betrag: float) -> str:
    return f"{betrag:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"


def _heute_str(ort: str = "") -> str:
    h = date.today()
    d = f"{h.day:02d}.{h.month:02d}.{h.year}"
    return f"{ort}, den {d}" if ort else d


def _monate_text(monate: list[int], jahr: int) -> str:
    ms = sorted(monate)
    if len(ms) == 1:
        return f"{MONATE_DE[ms[0]]} {jahr}"
    if ms == list(range(ms[0], ms[-1] + 1)):
        return f"{MONATE_DE[ms[0]]} bis {MONATE_DE[ms[-1]]} {jahr}"
    return ", ".join(MONATE_DE[m] for m in ms[:-1]) + f" und {MONATE_DE[ms[-1]]} {jahr}"


def erstelle_antrag_pdf(
    pfad: Path | str,
    absender_name: str,
    absender_adresse: str,
    absender_mail: str = "",
    kk_name: str = "",
    kk_adresse: str = "",
    versicherter_name: str = "",
    versicherter_adresse: str = "",
    versicherungsnr: str = "",
    geburtsdatum: str = "",
    modus: str = "vorsorglich",
    jahr: int = 0,
    monate: Optional[list[int]] = None,
    stunden_gesamt: float = 0.0,
    betrag_gesamt: float = 0.0,
    ort: str = "",
) -> Path:
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)

    if not jahr:
        jahr = date.today().year
    if not ort:
        zeilen = [z.strip() for z in absender_adresse.splitlines() if z.strip()]
        if zeilen:
            letzte = zeilen[-1]
            teile = letzte.split(" ", 1)
            ort = teile[1] if len(teile) > 1 and teile[0].isdigit() else letzte

    s = _styles()

    doc = SimpleDocTemplate(
        str(pfad),
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.5 * cm,
        title=f"Antrag auf Kostenerstattung Verhinderungspflege {jahr}",
        author="Pflegra",
    )

    story = []

    # ── Absender ──────────────────────────────────────────────────
    abs_zeilen = [z.strip() for z in absender_adresse.splitlines() if z.strip()]
    abs_block = absender_name
    if abs_zeilen:
        abs_block += "<br/>" + "<br/>".join(abs_zeilen)
    if absender_mail:
        abs_block += f"<br/>Mail: {absender_mail}"
    story.append(Paragraph(abs_block, s["absender"]))
    story.append(Spacer(1, 0.1 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=FARBE_TRENN))
    story.append(Spacer(1, 0.25 * cm))

    # ── Empfänger ─────────────────────────────────────────────────
    abs_einz = absender_name + (f", {abs_zeilen[0]}" if abs_zeilen else "")
    story.append(Paragraph(f"<font size='7' color='#888888'>{abs_einz}</font>", s["absender"]))
    story.append(Spacer(1, 0.1 * cm))

    empf_zeilen = []
    if kk_adresse:
        adresse_zeilen = [z.strip() for z in kk_adresse.splitlines() if z.strip()]
        erste_zeile = adresse_zeilen[0].lower() if adresse_zeilen else ""
        if kk_name and kk_name.lower().split()[0] not in erste_zeile:
            empf_zeilen.append(f"<b>{kk_name}</b>")
        empf_zeilen.extend(adresse_zeilen)
    elif kk_name:
        empf_zeilen.append(f"<b>{kk_name}</b>")
    if empf_zeilen:
        story.append(Paragraph("<br/>".join(empf_zeilen), s["empfaenger"]))
    story.append(Spacer(1, 0.1 * cm))

    # ── Datum ─────────────────────────────────────────────────────
    story.append(Paragraph(_heute_str(ort), s["datum"]))
    story.append(Spacer(1, 0.1 * cm))

    # ── Betreff ───────────────────────────────────────────────────
    story.append(Paragraph(
        "Betreff: Antrag auf Kostenerstattung für Verhinderungspflege nach § 39 SGB XI",
        s["betreff"]
    ))
    story.append(HRFlowable(width="100%", thickness=1.0, color=FARBE_PRIMÄR))
    story.append(Spacer(1, 0.25 * cm))

    # ── Anrede ────────────────────────────────────────────────────
    story.append(Paragraph("Sehr geehrte Damen und Herren,", s["anrede"]))

    # ── Brieftext ─────────────────────────────────────────────────
    if modus == "vorsorglich":
        story.append(Paragraph(
            f"hiermit beantrage ich die Verhinderungspflege vorsorglich für das laufende Jahr {jahr}. "
            f"Die nachfolgenden individuellen Angaben können und werden erst mit Wahrnehmung der "
            f"Ersatzleistung im Rahmen der Abrechnung bekanntgegeben:",
            s["text"]
        ))
        story.append(Spacer(1, 0.1 * cm))
        for punkt in [
            "Grund der Verhinderung,",
            f"Name und Anschrift und Verhältnis der Ersatzpflegeperson zu "
            f"{versicherter_name or 'der versicherten Person'} "
            f"und ob diese im selben Haushalt lebt und",
            "ob die verhinderte Pflegeperson stundenweise oder tageweise verhindert ist.",
        ]:
            story.append(Paragraph(f"• {punkt}", s["text"]))

    else:  # manuell
        monate_s = _monate_text(monate or [], jahr)
        story.append(Paragraph(
            f"hiermit beantrage ich die Erstattung der Kosten für Verhinderungspflege "
            f"nach § 39 SGB XI für den Zeitraum {monate_s}.",
            s["text"]
        ))
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(
            f"Im genannten Zeitraum wurden insgesamt <b>{_fmt_stunden(stunden_gesamt)}</b> "
            f"Verhinderungspflege in Anspruch genommen. "
            f"Die Gesamtkosten belaufen sich auf <b>{_fmt_betrag(betrag_gesamt)}</b>.",
            s["text"]
        ))
        story.append(Spacer(1, 0.1 * cm))
        story.append(Paragraph(
            "Der beigefügte Nachweis der Verhinderungspflege mit Einzelnachweisen "
            "und Unterschriften liegt diesem Antrag bei.",
            s["text"]
        ))

    story.append(Spacer(1, 0.25 * cm))

    # ── Versicherten-Block ────────────────────────────────────────
    story.append(Paragraph("Bitte berücksichtigen Sie diese Beantragung für:", s["text"]))
    story.append(Spacer(1, 0.1 * cm))

    vers_daten = []
    if versicherter_name:
        vers_daten.append(["Name:", versicherter_name])
    if geburtsdatum:
        vers_daten.append(["Geboren am:", geburtsdatum])
    if versicherter_adresse:
        vers_daten.append(["Wohnhaft in:", " ".join(l.strip() for l in versicherter_adresse.splitlines() if l.strip())])
    if versicherungsnr:
        vers_daten.append(["Versichertennummer:", versicherungsnr])
    if modus == "manuell" and monate:
        vers_daten.append(["Zeitraum:", _monate_text(monate, jahr)])

    if vers_daten:
        t = Table(vers_daten, colWidths=[5.0 * cm, 10.5 * cm])
        t.setStyle(TableStyle([
            ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME",      (1, 0), (1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 0), (-1, -1), 9.5),
            ("TEXTCOLOR",     (0, 0), (0, -1), FARBE_GRAU),
            ("TEXTCOLOR",     (1, 0), (1, -1), FARBE_TEXT),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("BACKGROUND",    (0, 0), (-1, -1), FARBE_HELL),
            ("BOX",           (0, 0), (-1, -1), 0.5, FARBE_TRENN),
            ("INNERGRID",     (0, 0), (-1, -1), 0.3, FARBE_TRENN),
        ]))
        story.append(t)

    story.append(Spacer(1, 0.1 * cm))

    # ── Schluss ───────────────────────────────────────────────────
    story.append(Paragraph(
        "Bitte senden Sie mir eine kurze Bestätigung an meine Absender-Adresse.",
        s["text"]
    ))
    story.append(Spacer(1, 0.1 * cm))
    story.append(Paragraph("Mit freundlichen Grüßen", s["gruss"]))
    story.append(Spacer(1, 1.0 * cm))

    # ── Unterschriftsbereich + Fußzeile ──────────────────────────
    unt = Table(
        [
            ["_" * 35, "_" * 25],
            [absender_name, _heute_str(ort)],
            ["", ""],
            [Paragraph(
                f"<font size='7' color='#999999'>Erstellt mit Pflegra  ·  "
                f"Antrag auf Kostenerstattung Verhinderungspflege § 39 SGB XI  ·  {jahr}</font>",
                s["fuss"]
            ), ""],
        ],
        colWidths=[10.0 * cm, 6.0 * cm],
    )
    unt.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, 1), 9),
        ("TEXTCOLOR",     (0, 0), (-1, 1), FARBE_GRAU),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("ALIGN",         (1, 0), (1, 1), "RIGHT"),
        ("LINEABOVE",     (0, 3), (1, 3), 0.3, FARBE_TRENN),
        ("SPAN",          (0, 3), (1, 3)),
        ("ALIGN",         (0, 3), (1, 3), "CENTER"),
    ]))
    story.append(unt)

    doc.build(story)
    return pfad
