"""
Pflegera – Gutachten-Analyse Parser v0.2
Extrahiert strukturierte Daten aus MD/MDK-Gutachten PDFs.

Strategie:
1. Text direkt extrahieren (digitale PDFs) oder OCR (gescannte PDFs)
2. Primär: Berechnungsanlage (letzte Seiten) für Modulpunkte
3. Sekundär: Ergebnistabelle für Gesamtpunkte + Pflegegrad
4. Deckblatt für Metadaten
"""
from __future__ import annotations

import re
import io
import logging
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class ModulErgebnis:
    nummer: int
    name: str
    einzelpunkte: Optional[int] = None
    gewichtete_punkte: Optional[float] = None
    gewichtung_prozent: int = 0


@dataclass
class GutachtenErgebnis:
    gutachten_datum: Optional[str] = None
    gutachten_typ: Optional[str] = None
    anlass: Optional[str] = None
    bisheriger_pflegegrad: Optional[int] = None
    diagnosen: list[str] = field(default_factory=list)
    module: list[ModulErgebnis] = field(default_factory=list)
    gesamtpunkte: Optional[float] = None
    pflegegrad: Optional[int] = None
    pflegegrad_seit: Optional[str] = None
    besondere_bedarfskonstellation: bool = False
    ocr_verwendet: bool = False
    seiten_verarbeitet: int = 0
    konfidenz: str = "unbekannt"
    _rohtexte: list[str] = field(default_factory=list, repr=False)


MODUL_NAMEN = {
    1: "Mobilität",
    2: "Kognitive und kommunikative Fähigkeiten",
    3: "Verhaltensweisen und psychische Problemlagen",
    4: "Selbstversorgung",
    5: "Bewältigung krankheits-/therapiebedingter Anforderungen",
    6: "Gestaltung des Alltagslebens und sozialer Kontakte",
}

MODUL_GEWICHTUNGEN = {1: 10, 2: 15, 3: 15, 4: 40, 5: 20, 6: 15}


def pdf_text_extrahieren(pdf_pfad: str) -> tuple[list[str], bool]:
    import fitz
    doc = fitz.open(pdf_pfad)
    seiten_texte = []
    ocr_verwendet = False

    gesamt_text = sum(len(doc[i].get_text()) for i in range(min(5, len(doc))))

    if gesamt_text < 100:
        ocr_verwendet = True
        try:
            import pytesseract
            from PIL import Image
            for page in doc:
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes('png')))
                text = pytesseract.image_to_string(img, lang='deu')
                seiten_texte.append(text)
        except ImportError:
            seiten_texte = [""] * len(doc)
    else:
        for page in doc:
            seiten_texte.append(page.get_text())

    return seiten_texte, ocr_verwendet


def parse_berechnungsanlage(texte: list[str]) -> dict[int, tuple[Optional[int], Optional[float]]]:
    """
    Liest Einzelpunkte und gewichtete Punkte aus der Berechnungsanlage.
    Zuverlässigste Quelle — letzte Seiten des Gutachtens.
    """
    ergebnis = {}

    # Suche Berechnungsanlage in den letzten 3 Seiten
    anlage_text = "\n".join(texte[-3:])

    if "Berechnungs" not in anlage_text and "Bewertungsregeln" not in anlage_text:
        return ergebnis

    # Pattern für jedes Modul in der Berechnungsanlage:
    # Modul 1 Mobilität: Einzelpunkte in letzter Spalte, gewichtete Punkte am Zeilenende
    # Format: "10-15  EP\n 0  2,5  5  7,5  10  GP"

    # Modul 1
    m = re.search(r'Mobilit[äa]t.*?10-15\s+(\d+)\s*\n[^\n]*?(\d+[,\.]\d+)\s*$',
                  anlage_text, re.DOTALL | re.MULTILINE)
    if m:
        ergebnis[1] = (int(m.group(1)), float(m.group(2).replace(',', '.')))

    # Modul 2/3 kombiniert — höchster Wert
    m = re.search(r'[Hh][öo]chster\s+Wert.*?(\d+[,\.]\d+)\s*$',
                  anlage_text, re.MULTILINE)
    if m:
        gp = float(m.group(1).replace(',', '.'))
        # Einzelpunkte aus Modul 2 Zeile
        m2 = re.search(r'kommunikative\s+F[äa]higkeiten.*?17.33\s+(\d+)',
                       anlage_text, re.DOTALL)
        ep2 = int(m2.group(1)) if m2 else None
        m3 = re.search(r'Verhaltensweisen.*?7.65\s+(\d+)',
                       anlage_text, re.DOTALL)
        ep3 = int(m3.group(1)) if m3 else None
        ergebnis[2] = (ep2, gp)
        ergebnis[3] = (ep3, gp)

    # Modul 4 Selbstversorgung
    m = re.search(r'Selbstversorgung.*?37.54\s+(\d+)\s*\n[^\n]*?(\d+[,\.]\d+)',
                  anlage_text, re.DOTALL)
    if m:
        ergebnis[4] = (int(m.group(1)), float(m.group(2).replace(',', '.')))

    # Modul 5
    m = re.search(r'6.15\s+(\d+)\s*\n[^\n]*?(\d+[,\.]\d+)\s*\n[^\n]*Belastungen',
                  anlage_text, re.DOTALL)
    if not m:
        m = re.search(r'Belastungen\s*\n[^\n]*(\d+[,\.]\d+)\s*$',
                      anlage_text, re.MULTILINE)
    if m:
        gp5_str = m.group(1) if m.lastindex == 1 else m.group(2)
        # Einzelpunkte Modul 5 aus Modulabschnitt
        m5 = re.search(r'Summe\s+der\s+Einzelpunkte\s+(\d+)\s+Gewichtete\s+Punkte\s+5',
                       "\n".join(texte), re.IGNORECASE)
        ep5 = int(m5.group(1)) if m5 else None
        ergebnis[5] = (ep5, float(gp5_str.replace(',', '.')))

    # Modul 6
    m = re.search(r'12.18\s+(\d+)\s*\n[^\n]*?(\d+[,\.]\d+)',
                  anlage_text, re.DOTALL)
    if m:
        ergebnis[6] = (int(m.group(1)), float(m.group(2).replace(',', '.')))

    return ergebnis


def parse_ergebnistabelle(texte: list[str]) -> dict[int, float]:
    """Liest gewichtete Punkte aus der Ergebnistabelle (Abschnitt 5)."""
    volltext = "\n".join(texte)
    ergebnis = {}

    # Suche Ergebnistabelle
    match = re.search(
        r'Ergebnis\s+der\s+Begutachtung.*?Gesamtpunkte',
        volltext, re.DOTALL | re.IGNORECASE
    )
    if not match:
        return ergebnis

    block = volltext[match.start():match.end() + 200]

    # Extrahiere Modulpunkte aus der Tabelle
    patterns = [
        (1, r'Mobilit[äa]t\s+(\d+[,\.]\d+)'),
        (2, r'Kognitive.*?(\d+[,\.]\d+)'),
        (4, r'Selbstversorgung\s+(\d+[,\.]\d+)'),
        (5, r'Bew[äa]ltigung.*?(\d+[,\.]\d+)'),
        (6, r'Gestaltung.*?(\d+[,\.]\d+)'),
    ]

    for nr, pattern in patterns:
        m = re.search(pattern, block, re.DOTALL | re.IGNORECASE)
        if m:
            ergebnis[nr] = float(m.group(1).replace(',', '.'))

    return ergebnis


def parse_module(texte: list[str]) -> list[ModulErgebnis]:
    """Kombiniert Berechnungsanlage + Einzelpunkte aus Modulabschnitten."""
    module = []

    # Primär: Berechnungsanlage
    anlage = parse_berechnungsanlage(texte)

    # Fallback: Ergebnistabelle für GP
    ergebnis_gp = parse_ergebnistabelle(texte)

    # Einzelpunkte direkt aus Modulabschnitten
    volltext = "\n".join(texte)
    ep_pattern = re.compile(
        r'4\.(\d)\s+Modul\s+\d[^§\n]*.*?'
        r'Summe\s+der\s+Einzelpunkte\s+(\d+)\s+Gewichtete\s+Punkte\s+(\d+[,\.]\d+)',
        re.DOTALL | re.IGNORECASE
    )
    modul_ep = {}
    modul_gp = {}
    for m in ep_pattern.finditer(volltext):
        nr = int(m.group(1))
        modul_ep[nr] = int(m.group(2))
        modul_gp[nr] = float(m.group(3).replace(',', '.'))

    for nr in range(1, 7):
        ep, gp = anlage.get(nr, (None, None))

        # Direktextraktion bevorzugen wenn verfügbar
        if nr in modul_ep:
            ep = modul_ep[nr]
        if nr in modul_gp:
            gp = modul_gp[nr]

        # Fallback Ergebnistabelle
        if gp is None and nr in ergebnis_gp:
            gp = ergebnis_gp[nr]

        module.append(ModulErgebnis(
            nummer=nr,
            name=MODUL_NAMEN[nr],
            einzelpunkte=ep,
            gewichtete_punkte=gp,
            gewichtung_prozent=MODUL_GEWICHTUNGEN[nr],
        ))

    return module


def parse_gesamtpunkte(texte: list[str]) -> Optional[float]:
    volltext = "\n".join(texte)
    for pattern in [
        r'Gesamtpunkte\s+(\d+[,\.]\d+)',
        r'Summe\s+der\s+gewichteten\s+Punkte\s+(\d+[,\.]\d+)',
    ]:
        m = re.search(pattern, volltext, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(',', '.'))
    return None


def parse_pflegegrad(texte: list[str]) -> tuple[Optional[int], Optional[str]]:
    volltext = "\n".join(texte)

    # Aus Zusammenfassung (Deckblatt)
    m = re.search(
        r'Ergebnis[:\s]+Pflegegrad\s+(\d)[,\s]+seit\s+(\d{2}\.\d{2}\.\d{4})',
        volltext, re.IGNORECASE
    )
    if m:
        return int(m.group(1)), m.group(2)

    # Seit wann? Datum
    m_seit = re.search(r'Seit\s+wann\?\s+(\d{2}\.\d{2}\.\d{4})', volltext)
    seit = m_seit.group(1) if m_seit else None

    # Pflegegrad aus Tabelle
    m = re.search(r'[⊙☉●©@]\s*Pflegegrad\s+(\d)', volltext)
    if m:
        return int(m.group(1)), seit

    # Fallback
    m = re.search(r'Pflegegrad\s+(\d)\b', volltext, re.IGNORECASE)
    if m:
        grad = int(m.group(1))
        if 1 <= grad <= 5:
            return grad, seit

    return None, seit


def parse_diagnosen(texte: list[str]) -> list[str]:
    volltext = "\n".join(texte)
    m = re.search(
        r'Pflegebegr[üu]ndende\s+Diagnose[n\(\)]*\s*\n(.*?)(?:\nWeitere\s+Diagnosen|\n\d\s+Module|\Z)',
        volltext, re.DOTALL | re.IGNORECASE
    )
    if m:
        text = m.group(1).strip()
        text = re.sub(r'ICD\s*\d+\s+[A-Z]\d+[\.\d]*', '', text)
        diagnosen = [d.strip() for d in re.split(r'\n', text) if len(d.strip()) > 8]
        return diagnosen[:5]
    return []


def parse_metadaten(texte: list[str]) -> dict:
    volltext = "\n".join(texte[:3])
    result = {}

    if re.search(r'Widerspruch', volltext, re.IGNORECASE):
        result['typ'] = 'Widerspruch'
    elif re.search(r'H[öo]herstufungsantrag', volltext, re.IGNORECASE):
        result['typ'] = 'Höherstufungsantrag'
    elif re.search(r'Erstantrag', volltext, re.IGNORECASE):
        result['typ'] = 'Erstantrag'
    elif re.search(r'Wiederholungsbegutachtung', volltext, re.IGNORECASE):
        result['typ'] = 'Wiederholungsbegutachtung'

    m = re.search(r'vom\s+(\d{2}\.\d{2}\.\d{4})', volltext)
    if m:
        result['datum'] = m.group(1)

    m = re.search(r'Bisheriger\s+Pflegegrad[:\s]+Pflegegrad\s+(\d)', volltext, re.IGNORECASE)
    if m:
        result['bisheriger_pflegegrad'] = int(m.group(1))

    m = re.search(r'Anlass[^:]*:[^\n]*\n([^\n]+)', volltext)
    if m:
        result['anlass'] = m.group(1).strip()

    return result


def pflegegrad_berechnen(punkte: float) -> int:
    if punkte < 12.5: return 0
    elif punkte < 27: return 1
    elif punkte < 47.5: return 2
    elif punkte < 70: return 3
    elif punkte < 90: return 4
    else: return 5


def gutachten_analysieren(pdf_pfad: str) -> GutachtenErgebnis:
    ergebnis = GutachtenErgebnis()

    texte, ocr = pdf_text_extrahieren(pdf_pfad)
    ergebnis.ocr_verwendet = ocr
    ergebnis.seiten_verarbeitet = len(texte)
    ergebnis._rohtexte = texte

    meta = parse_metadaten(texte)
    ergebnis.gutachten_typ = meta.get('typ')
    ergebnis.gutachten_datum = meta.get('datum')
    ergebnis.bisheriger_pflegegrad = meta.get('bisheriger_pflegegrad')
    ergebnis.anlass = meta.get('anlass')

    ergebnis.diagnosen = parse_diagnosen(texte)
    ergebnis.module = parse_module(texte)
    ergebnis.gesamtpunkte = parse_gesamtpunkte(texte)

    pflegegrad, seit = parse_pflegegrad(texte)
    ergebnis.pflegegrad = pflegegrad
    ergebnis.pflegegrad_seit = seit

    if ergebnis.gesamtpunkte and not ergebnis.pflegegrad:
        ergebnis.pflegegrad = pflegegrad_berechnen(ergebnis.gesamtpunkte)

    if ergebnis.gesamtpunkte and ergebnis.pflegegrad:
        berechnet = pflegegrad_berechnen(ergebnis.gesamtpunkte)
        ergebnis.konfidenz = "hoch" if berechnet == ergebnis.pflegegrad else "mittel"
    elif ergebnis.pflegegrad or ergebnis.gesamtpunkte:
        ergebnis.konfidenz = "mittel"
    else:
        ergebnis.konfidenz = "niedrig"

    return ergebnis


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.WARNING)

    for pdf in sys.argv[1:] or ["/mnt/user-data/uploads/md1.pdf"]:
        print(f"\n{'='*50}")
        print(f"Analysiere: {pdf}")
        r = gutachten_analysieren(pdf)
        print(f"Typ: {r.gutachten_typ} | Datum: {r.gutachten_datum} | OCR: {r.ocr_verwendet}")
        print(f"Bisheriger PG: {r.bisheriger_pflegegrad} | Konfidenz: {r.konfidenz}")
        print(f"Diagnosen: {r.diagnosen}")
        print(f"Gesamtpunkte: {r.gesamtpunkte} → Pflegegrad {r.pflegegrad} (seit {r.pflegegrad_seit})")
        print(f"\nModule:")
        for m in r.module:
            ep = f"EP:{m.einzelpunkte:3}" if m.einzelpunkte is not None else "EP:  ?"
            gp = f"GP:{m.gewichtete_punkte:6.2f}" if m.gewichtete_punkte is not None else "GP:     ?"
            print(f"  {m.nummer}. {m.name[:42]:<42} {ep}  {gp}  ({m.gewichtung_prozent}%)")
