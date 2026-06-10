"""
Pflegra – Vollmacht Pflegeversicherung
Universeller Brief-PDF, KK-unabhängig.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

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
    st("bullet",     fontSize=10, fontName="Helvetica",      textColor=FARBE_TEXT,  leading=15,
       leftIndent=14, spaceAfter=3)
    st("gruss",      fontSize=10, fontName="Helvetica",      textColor=FARBE_TEXT,  spaceBefore=6)
    st("fuss",       fontSize=7,  fontName="Helvetica",      textColor=FARBE_GRAU,  alignment=TA_CENTER)
    return s


def _heute_str(ort: str = "") -> str:
    h = date.today()
    d = f"{h.day:02d}.{h.month:02d}.{h.year}"
    return f"{ort}, den {d}" if ort else d


def _ort_aus_adresse(adresse: str) -> str:
    zeilen = [z.strip() for z in adresse.splitlines() if z.strip()]
    if not zeilen:
        return ""
    letzte = zeilen[-1]
    teile = letzte.split(" ", 1)
    return teile[1] if len(teile) > 1 and teile[0].isdigit() else letzte


def erstelle_vollmacht_pdf(
    pfad: Path | str,
    # Versicherter (erteilt Vollmacht)
    versicherter_name: str,
    versicherter_adresse: str,
    versicherungsnr: str = "",
    # Bevollmächtigter (Absender aus Einstellungen)
    bevollmaechtigter_name: str = "",
    bevollmaechtigter_adresse: str = "",
    bevollmaechtigter_geburtsdatum: str = "",
    # Krankenkasse
    kk_name: str = "",
    kk_adresse: str = "",
    # Meta
    gueltig_ab: str = "",
) -> Path:
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)

    ort = _ort_aus_adresse(versicherter_adresse)
    if not gueltig_ab:
        h = date.today()
        gueltig_ab = f"{h.day:02d}.{h.month:02d}.{h.year}"

    s = _styles()

    doc = SimpleDocTemplate(
        str(pfad), pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2.5*cm, bottomMargin=3.0*cm,
        title="Vollmacht Pflegeversicherung",
        author="Pflegra",
    )
    story = []

    # ── Absender (Versicherter) ───────────────────────────────────────────────
    abs_zeilen = [z.strip() for z in versicherter_adresse.splitlines() if z.strip()]
    abs_block = versicherter_name
    if abs_zeilen:
        abs_block += "<br/>" + "<br/>".join(abs_zeilen)
    story.append(Paragraph(abs_block, s["absender"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=FARBE_TRENN))
    story.append(Spacer(1, 0.5*cm))

    # Fensterumschlag-Zeile
    abs_einz = versicherter_name + (f", {abs_zeilen[0]}" if abs_zeilen else "")
    story.append(Paragraph(f"<font size='7' color='#888888'>{abs_einz}</font>", s["absender"]))
    story.append(Spacer(1, 0.2*cm))

    # Empfänger
    empf_zeilen = []
    if kk_adresse:
        adresse_zeilen = [z.strip() for z in kk_adresse.splitlines() if z.strip()]
        erste = adresse_zeilen[0].lower() if adresse_zeilen else ""
        if kk_name and kk_name.lower().split()[0] not in erste:
            empf_zeilen.append(f"<b>{kk_name}</b>")
        empf_zeilen.extend(adresse_zeilen)
    elif kk_name:
        empf_zeilen.append(f"<b>{kk_name}</b>")
    if empf_zeilen:
        story.append(Paragraph("<br/>".join(empf_zeilen), s["empfaenger"]))
    story.append(Spacer(1, 1.0*cm))

    # Datum
    story.append(Paragraph(_heute_str(ort), s["datum"]))
    story.append(Spacer(1, 0.6*cm))

    # Betreff
    story.append(Paragraph("Betreff: Vollmacht", s["betreff"]))
    if versicherungsnr:
        story.append(Paragraph(f"Versichertennummer: {versicherungsnr}", s["text"]))
    story.append(HRFlowable(width="100%", thickness=1.0, color=FARBE_PRIMÄR))
    story.append(Spacer(1, 0.5*cm))

    # Anrede + Einleitungstext
    story.append(Paragraph("Sehr geehrte Damen und Herren,", s["anrede"]))
    story.append(Paragraph("Hiermit erteile ich:", s["text"]))
    story.append(Spacer(1, 0.3*cm))

    # Bevollmächtigter-Block
    bev_daten = []
    if bevollmaechtigter_name:
        bev_daten.append(["Name:", bevollmaechtigter_name])
    if bevollmaechtigter_geburtsdatum:
        bev_daten.append(["Geboren am:", bevollmaechtigter_geburtsdatum])
    if bevollmaechtigter_adresse:
        bev_daten.append(["Wohnhaft in:", " ".join(l.strip() for l in bevollmaechtigter_adresse.splitlines() if l.strip())])

    if bev_daten:
        t = Table(bev_daten, colWidths=[5.0*cm, 10.5*cm])
        t.setStyle(TableStyle([
            ("FONTNAME",      (0,0),(0,-1), "Helvetica-Bold"),
            ("FONTNAME",      (1,0),(1,-1), "Helvetica"),
            ("FONTSIZE",      (0,0),(-1,-1), 9.5),
            ("TEXTCOLOR",     (0,0),(0,-1), FARBE_GRAU),
            ("TEXTCOLOR",     (1,0),(1,-1), FARBE_TEXT),
            ("TOPPADDING",    (0,0),(-1,-1), 4),
            ("BOTTOMPADDING", (0,0),(-1,-1), 4),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
            ("BACKGROUND",    (0,0),(-1,-1), FARBE_HELL),
            ("BOX",           (0,0),(-1,-1), 0.5, FARBE_TRENN),
            ("INNERGRID",     (0,0),(-1,-1), 0.3, FARBE_TRENN),
        ]))
        story.append(t)
    story.append(Spacer(1, 0.4*cm))

    # Vollmachtstext
    kk_kurz = kk_name or "der Pflegekasse"
    story.append(Paragraph(
        f"die Vollmacht, mich in allen Angelegenheiten der Kranken- und Pflegeversicherung "
        f"bei {kk_kurz} zu vertreten. Die Vollmacht gilt für das Verwaltungs- und "
        f"Widerspruchsverfahren und ermächtigt zu allen Verfahrenshandlungen. Insbesondere "
        f"umfasst sie die Befugnis, Anträge zu stellen, zu verfolgen, Rechtsmittel "
        f"einzulegen, zurückzunehmen oder auf sie zu verzichten. Diese Vollmacht gilt für "
        f"alle zukünftigen {kk_kurz} betreffenden Angelegenheiten. Etwaige in der "
        f"Vergangenheit erteilte Vollmachten erlöschen hiermit.",
        s["text"]
    ))
    story.append(Paragraph("Diese Vollmacht umfasst folgende Bereiche:", s["text"]))
    story.append(Spacer(1, 0.15*cm))

    for bullet in [
        f"Auskünfte in allen Belangen der Kranken- und Pflegeversicherung bei {kk_kurz} "
        f"erhalten zu dürfen und Einsicht in sämtliche Sozial- und Gesundheitsdaten nehmen zu können.",
        f"Anträge zu stellen und Erklärungen abzugeben. Die Vollmacht umfasst die Vertretung "
        f"in sämtlichen Angelegenheiten der Kranken- und Pflegeversicherung gegenüber {kk_kurz}.",
        "Zusätzlich soll der gesamte Schriftverkehr an die Bevollmächtigte/den Bevollmächtigten gehen.",
        f"Die Vollmacht umfasst die Vertretung in sämtlichen Angelegenheiten der Kranken- und "
        f"Pflegeversicherung gegenüber {kk_kurz}.",
    ]:
        story.append(Paragraph(f"• {bullet}", s["bullet"]))

    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("Die Vollmacht gilt über den Tod hinaus.", s["text"]))
    story.append(Spacer(1, 0.4*cm))

    # Seite 2 Inhalt (Schweigepflicht + Gültigkeit)
    story.append(Paragraph(
        f"Ich entbinde die Kranken- und Pflegekasse {kk_kurz} von ihrer Schweigepflicht "
        f"gegenüber der bevollmächtigten Person.",
        s["text"]
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"Diese Vollmacht gilt ab dem {gueltig_ab}.", s["text"]))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        f"Diese Vollmacht kann jederzeit bei {kk_kurz} mündlich, schriftlich oder zur "
        f"Niederschrift widerrufen werden.",
        s["text"]
    ))
    story.append(Spacer(1, 0.8*cm))

    # Unterschrift
    unt = Table(
        [[f"Unterschrift {versicherter_name}", _heute_str(ort)]],
        colWidths=[9.5*cm, 6.5*cm],
    )
    unt.setStyle(TableStyle([
        ("FONTNAME",   (0,0),(-1,-1), "Helvetica"),
        ("FONTSIZE",   (0,0),(-1,-1), 9),
        ("TEXTCOLOR",  (0,0),(-1,-1), FARBE_GRAU),
        ("LINEABOVE",  (0,0),(0,0), 0.5, FARBE_TRENN),
        ("LINEABOVE",  (1,0),(1,0), 0.5, FARBE_TRENN),
        ("TOPPADDING", (0,0),(-1,-1), 5),
        ("ALIGN",      (1,0),(1,0), "RIGHT"),
    ]))
    story.append(unt)
    story.append(Spacer(1, 0.5*cm))

    # Datenschutz-Klausel
    story.append(Paragraph(
        f"Ich stimme zu, dass die Pflegeversicherung {kk_kurz} diese Daten nach § 60 SGB I "
        f"in Verbindung mit § 94 SGB XI im Rahmen der Datenschutzrichtlinien verarbeitet.",
        s["text"]
    ))

    # Fußzeile
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width="100%", thickness=0.3, color=FARBE_TRENN))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "Erstellt mit pflegra.app  ·  Vollmacht Pflegeversicherung",
        s["fuss"]
    ))

    doc.build(story)
    return pfad
