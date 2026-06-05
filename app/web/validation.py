"""
Pflegra – zentrale Eingabevalidierung
Alle Routers importieren von hier. Kein Validierungscode in den Routers.
"""
from __future__ import annotations

import re
import tempfile
from datetime import date, datetime
from pathlib import Path

# ── Konstanten ───────────────────────────────────────────────────────────────

MAX_UPLOAD_BYTES  = 5 * 1024 * 1024   # 5 MB
ERLAUBTE_SUFFIXE  = {".csv", ".xlsx", ".ods"}
UHRZEIT_RE        = re.compile(r"^\d{2}:\d{2}$")
MAX_STUNDEN       = 24.0
MAX_NAME_LEN      = 120
MAX_NOTIZ_LEN     = 500
MAX_ADRESSE_LEN   = 250

# Temporäre Dateien dürfen nur aus /tmp kommen (Pfad-Traversal-Schutz)
ERLAUBTER_TMP_ORDNER = Path(tempfile.gettempdir()).resolve()


class Validierungsfehler(ValueError):
    """Fachlicher Validierungsfehler – wird dem Nutzer angezeigt."""
    pass


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _check(bedingung: bool, meldung: str) -> None:
    if not bedingung:
        raise Validierungsfehler(meldung)


def _str(wert: str, feld: str, max_len: int = MAX_NAME_LEN) -> str:
    """Bereinigt und prüft einen Pflicht-Textfeld."""
    bereinigt = wert.strip()
    _check(len(bereinigt) > 0, f"{feld} darf nicht leer sein.")
    _check(len(bereinigt) <= max_len, f"{feld} ist zu lang (max. {max_len} Zeichen).")
    return bereinigt


def _opt_str(wert: str, feld: str, max_len: int = MAX_NAME_LEN) -> str:
    """Bereinigt ein optionales Textfeld ohne Pflicht-Prüfung."""
    bereinigt = wert.strip()
    _check(len(bereinigt) <= max_len, f"{feld} ist zu lang (max. {max_len} Zeichen).")
    return bereinigt


# ── Eintrag-Validierung ───────────────────────────────────────────────────────

def validiere_eintrag(
    datum: str,
    von: str,
    bis: str,
    stunden: str,
    person: str,
    art: str,
    grund: str,
    ersatz_name: str,
    ersatz_art: str,
    ersatz_adresse: str,
    notiz: str,
) -> dict:
    """
    Validiert alle Felder eines Pflege-Eintrags.
    Gibt ein dict mit bereinigten Werten zurück oder wirft Validierungsfehler.
    """
    from models import PFLEGE_ARTEN, PFLEGE_GRUENDE, ERSATZ_ARTEN

    # Datum
    try:
        datum_obj = datetime.strptime(datum.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise Validierungsfehler("Ungültiges Datum – bitte im Format JJJJ-MM-TT angeben.")
    _check(datum_obj.year >= 2020, "Datum liegt vor 2020 – bitte prüfen.")
    _check(datum_obj <= date.today(), "Datum liegt in der Zukunft.")

    # Uhrzeiten
    von_s = von.strip()
    bis_s = bis.strip()
    _check(bool(UHRZEIT_RE.match(von_s)), "Von-Uhrzeit ungültig (Format HH:MM erwartet).")
    _check(bool(UHRZEIT_RE.match(bis_s)), "Bis-Uhrzeit ungültig (Format HH:MM erwartet).")

    # Stunden
    try:
        stunden_f = float(stunden.strip().replace(",", "."))
    except ValueError:
        raise Validierungsfehler("Stunden: Ungültige Zahl.")
    _check(stunden_f > 0, "Stunden müssen größer als 0 sein.")
    _check(stunden_f <= MAX_STUNDEN, f"Stunden dürfen maximal {MAX_STUNDEN} betragen.")

    # Person
    person_s = _str(person, "Person")

    # Enumerationen
    _check(art in PFLEGE_ARTEN, f"Ungültige Pflegeart: {art!r}")
    _check(grund in PFLEGE_GRUENDE, f"Ungültiger Grund: {grund!r}")
    _check(ersatz_art in ERSATZ_ARTEN, f"Ungültige Ersatzart: {ersatz_art!r}")

    return {
        "datum": datum_obj,
        "von": von_s,
        "bis": bis_s,
        "stunden": stunden_f,
        "person": person_s,
        "art": art,
        "grund": grund,
        "ersatz_name":    _opt_str(ersatz_name, "Ersatzname"),
        "ersatz_art":     ersatz_art,
        "ersatz_adresse": _opt_str(ersatz_adresse, "Ersatzadresse", MAX_ADRESSE_LEN),
        "notiz":          _opt_str(notiz, "Notiz", MAX_NOTIZ_LEN),
    }


# ── Personen-Validierung ─────────────────────────────────────────────────────

def validiere_person_name(name: str) -> str:
    """Gibt bereinigten Namen zurück oder wirft Validierungsfehler."""
    return _str(name, "Name")


# ── Versicherter-Validierung ──────────────────────────────────────────────────

def validiere_versicherter(
    person_name: str,
    adresse: str,
    versicherungsnr: str,
    krankenkasse: str,
    krankenkasse_adresse: str,
    pflegegrad: int,
    geburtsdatum: str,
    mail: str,
    notiz: str,
) -> dict:
    person_s = _str(person_name, "Person")
    _check(0 <= pflegegrad <= 5, f"Pflegegrad muss zwischen 0 und 5 liegen, nicht {pflegegrad}.")
    vnr = versicherungsnr.strip()
    _check(len(vnr) <= 20, "Versicherungsnummer zu lang (max. 20 Zeichen).")
    # Geburtsdatum optional, aber wenn gefüllt dann TT.MM.JJJJ
    geb = geburtsdatum.strip()
    if geb:
        import re as _re
        _check(bool(_re.match(r"^\d{2}\.\d{2}\.\d{4}$", geb)),
               "Geburtsdatum bitte im Format TT.MM.JJJJ angeben.")
    return {
        "person_name":          person_s,
        "adresse":              _opt_str(adresse, "Adresse", MAX_ADRESSE_LEN),
        "versicherungsnr":      vnr,
        "krankenkasse":         _opt_str(krankenkasse, "Krankenkasse"),
        "krankenkasse_adresse": _opt_str(krankenkasse_adresse, "KK-Adresse", MAX_ADRESSE_LEN),
        "pflegegrad":           pflegegrad,
        "geburtsdatum":         geb,
        "mail":                 _opt_str(mail, "E-Mail"),
        "notiz":                _opt_str(notiz, "Notiz", MAX_NOTIZ_LEN),
    }


# ── Import-Validierung ───────────────────────────────────────────────────────

def validiere_upload_datei(dateiname: str, dateigroesse: int) -> str:
    """
    Prüft Dateiname und -größe beim Upload.
    Gibt die Dateiendung (lowercase) zurück.
    """
    suffix = Path(dateiname).suffix.lower()
    _check(
        suffix in ERLAUBTE_SUFFIXE,
        f"Nicht erlaubtes Dateiformat: {suffix!r}. Erlaubt: {', '.join(sorted(ERLAUBTE_SUFFIXE))}",
    )
    _check(
        dateigroesse <= MAX_UPLOAD_BYTES,
        f"Datei zu groß ({dateigroesse // 1024} KB). Maximum: {MAX_UPLOAD_BYTES // 1024} KB.",
    )
    return suffix


def validiere_tmp_pfad(pfad_str: str) -> Path:
    """
    Schützt vor Pfad-Traversal beim Import-Bestätigen.
    Nur Pfade innerhalb von /tmp sind erlaubt.
    """
    try:
        pfad = Path(pfad_str).resolve()
    except Exception:
        raise Validierungsfehler("Ungültiger Dateipfad.")
    _check(
        str(pfad).startswith(str(ERLAUBTER_TMP_ORDNER)),
        "Ungültiger temporärer Dateipfad.",
    )
    _check(pfad.exists(), "Temporäre Datei nicht mehr vorhanden – bitte erneut hochladen.")
    return pfad
