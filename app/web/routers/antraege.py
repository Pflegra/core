"""
Router: Anträge & Dokumente
Übersicht aller generierbarer Dokumente.
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import List
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from models import MONATE_DE
from web.routers.deps import redirect,\
     TEMPLATES, base_ctx, get_db, get_konfig, get_owner_id, get_user_settings
from web.auth import get_aktueller_user


def _get_absender(request):
    """Gibt Absender-Daten zurück — user_settings aus DB, Fallback auf config.json."""
    settings = get_user_settings(request)
    # Wenn user_settings leer sind → Fallback auf config.json
    if not settings.absender_name:
        konfig = get_konfig(request)
        from models import UserSettings
        s = UserSettings(
            absender_name=konfig.absender_name,
            absender_adresse=konfig.absender_adresse,
            absender_mail=konfig.absender_mail,
            absender_geburtsdatum=konfig.absender_geburtsdatum,
            stundensatz=konfig.stundensatz,
        )
        return s
    return settings

log = logging.getLogger(__name__)
router = APIRouter(prefix="/antraege", tags=["Anträge"])

MONATE_KURZ = ["", "Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
               "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


def _fehler(msg: str) -> RedirectResponse:
    return redirect(request, f"/antraege/?fehler={quote(msg, safe='')}", status_code=303)


def _zielordner(request: Request, sub: str = "") -> Path:
    data_dir = getattr(request.app.state, "data_dir", Path("."))
    basis = data_dir / "Archiv"
    return (basis / sub) if sub else basis


# ── Übersicht ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def antraege_uebersicht(request: Request, ok: str = "", fehler: str = ""):
    db = get_db(request)
    konfig = _get_absender(request)
    personen = db.personen(get_owner_id(request))
    jahre = db.jahre(get_owner_id(request)) or [date.today().year]

    # Ersatzpflegekräfte je Person für Ausfüllhilfe-Dropdown
    owner_id = get_owner_id(request)
    ersatz_je_person = {
        p: [{"name": e.name, "art": e.art} for e in db.ersatz_alle(p, owner_id)]
        for p in personen
    }

    return TEMPLATES.TemplateResponse(request, "antraege/uebersicht.html", {
        **base_ctx(request),
        "personen":         personen,
        "jahre":            jahre,
        "monate":           [(i, MONATE_DE[i]) for i in range(1, 13)],
        "konfig":           konfig,
        "ersatz_je_person": ersatz_je_person,
        "ok":               ok,
        "fehler":           fehler,
    })


# ── Antrag VP ─────────────────────────────────────────────────────────────────

@router.post("/vp/erstellen")
async def antrag_vp_erstellen(
    request: Request,
    person:  str = Form(default=""),
    jahr:    int = Form(...),
    modus:   str = Form("vorsorglich"),
    monate:  List[int] = Form(default=[]),
):
    if not person:
        return _fehler("Bitte eine Person auswählen.")
    db = get_db(request)
    konfig = _get_absender(request)
    versicherter = db.versicherter_laden(person, get_owner_id(request))
    if not versicherter:
        return _fehler(f"Keine Versicherten-Daten für {person}.")
    if not konfig.absender_name or not konfig.absender_adresse:
        return _fehler("Absender fehlt – bitte Einstellungen ausfüllen.")
    if modus == "manuell" and not monate:
        return _fehler("Bitte mindestens einen Monat auswählen.")

    try:
        stunden_gesamt = betrag_gesamt = 0.0
        if modus == "manuell":
            alle = db.alle(get_owner_id(request))
            for monat in sorted(monate):
                stunden_gesamt += sum(e.stunden for e in alle
                                      if e.person == person and e.datum.year == jahr
                                      and e.datum.month == monat)
            betrag_gesamt = stunden_gesamt * konfig.stundensatz

        zielordner = _zielordner(request, f"{jahr}/{person}")
        zielordner.mkdir(parents=True, exist_ok=True)

        if modus == "vorsorglich":
            dateiname = f"Antrag_Verhinderungspflege_{jahr}_{person.replace(' ', '_')}.pdf"
        else:
            ms = sorted(monate)
            m_str = (f"{MONATE_KURZ[ms[0]]}-{MONATE_KURZ[ms[-1]]}"
                     if ms == list(range(ms[0], ms[-1]+1))
                     else "_".join(MONATE_KURZ[m] for m in ms))
            dateiname = f"Antrag_Verhinderungspflege_{m_str}_{jahr}_{person.replace(' ', '_')}.pdf"

        from antrag_vp import erstelle_antrag_pdf
        pfad = erstelle_antrag_pdf(
            pfad=zielordner / dateiname,
            absender_name=konfig.absender_name,
            absender_adresse=konfig.absender_adresse,
            absender_mail=konfig.absender_mail,
            kk_name=versicherter.krankenkasse,
            kk_adresse=versicherter.krankenkasse_adresse,
            versicherter_name=versicherter.name,
            versicherter_adresse=versicherter.adresse,
            versicherungsnr=versicherter.versicherungsnr,
            geburtsdatum=versicherter.geburtsdatum,
            modus=modus, jahr=jahr,
            monate=sorted(monate) if modus == "manuell" else None,
            stunden_gesamt=stunden_gesamt,
            betrag_gesamt=betrag_gesamt,
        )
        log.info("Antrag VP erstellt: %s", pfad)
        return FileResponse(str(pfad), media_type="application/pdf", filename=dateiname)
    except Exception as exc:
        log.error("Antrag VP Fehler: %s", exc, exc_info=True)
        return _fehler("Antrag VP fehlgeschlagen – Details im Log.")


# ── Ausfüllhilfe VP ───────────────────────────────────────────────────────────

@router.post("/ausfuellhilfe/erstellen")
async def ausfuellhilfe_erstellen(
    request: Request,
    person:              str  = Form(default=""),
    zeitraum_von:        str  = Form(default=""),
    zeitraum_bis:        str  = Form(default=""),
    grund:               str  = Form(default=""),
    ersatz_name:         str  = Form(default=""),
    ersatz_geburtsdatum: str  = Form(default=""),
    ersatz_adresse:      str  = Form(default=""),
    ersatz_art:          str  = Form(default="Privatperson"),
):
    if not person:
        return _fehler("Bitte eine Person auswählen.")
    db      = get_db(request)
    konfig  = _get_absender(request)
    versicherter = db.versicherter_laden(person, get_owner_id(request))
    if not versicherter:
        return _fehler(f"Keine Versicherten-Daten für {person}.")
    if not konfig.absender_name:
        return _fehler("Absender fehlt – bitte Einstellungen ausfüllen.")

    try:
        from datetime import datetime
        dt_von = datetime.strptime(zeitraum_von, "%Y-%m-%d").date()
        dt_bis = datetime.strptime(zeitraum_bis, "%Y-%m-%d").date()
    except ValueError:
        return _fehler("Ungültiges Datumsformat.")

    try:
        alle = db.alle(get_owner_id(request))
        eintraege = [
            e for e in alle
            if e.person == person
            and dt_von <= e.datum <= dt_bis
        ]

        zielordner = _zielordner(request, f"{dt_von.year}/{person}")
        zielordner.mkdir(parents=True, exist_ok=True)
        dateiname = (
            f"Nachweis_Verhinderungspflege_"
            f"{dt_von.strftime('%d%m%Y')}-{dt_bis.strftime('%d%m%Y')}_"
            f"{person.replace(' ', '_')}.pdf"
        )

        from ausfuellhilfe_vp import erstelle_ausfuellhilfe_pdf
        # Ersatzpflegekraft aus DB laden wenn Name angegeben
        # Ersatzpflegekraft aus DB laden wenn Name im Formular angegeben
        ersatz_obj = None
        if ersatz_name:
            for ep in db.ersatz_alle(person, get_owner_id(request)):
                if ep.name == ersatz_name:
                    ersatz_obj = ep
                    break

        pfad = erstelle_ausfuellhilfe_pdf(
            pfad=zielordner / dateiname,
            versicherter_name=versicherter.name,
            versicherter_adresse=versicherter.adresse,
            versicherter_geburtsdatum=versicherter.geburtsdatum,
            versicherungsnr=versicherter.versicherungsnr,
            kk_name=versicherter.krankenkasse,
            pflegeperson_name=konfig.absender_name,
            pflegeperson_adresse=konfig.absender_adresse,
            ersatz_name=ersatz_obj.name if ersatz_obj else ersatz_name,
            ersatz_geburtsdatum=ersatz_obj.geburtsdatum if ersatz_obj else ersatz_geburtsdatum,
            ersatz_adresse=ersatz_obj.adresse if ersatz_obj else ersatz_adresse,
            ersatz_art=ersatz_obj.art if ersatz_obj else ersatz_art,
            zeitraum_von=dt_von.strftime("%d.%m.%Y"),
            zeitraum_bis=dt_bis.strftime("%d.%m.%Y"),
            grund=grund,
            eintraege=eintraege,
            stundensatz=konfig.stundensatz,
        )
        log.info("VP-Nachweis erstellt: %s (%d Einträge)", pfad, len(eintraege))
        return FileResponse(str(pfad), media_type="application/pdf", filename=dateiname)
    except Exception as exc:
        log.error("VP-Nachweis Fehler: %s", exc, exc_info=True)
        return _fehler("VP-Nachweis fehlgeschlagen – Details im Log.")


# ── Vollmacht Pflegeversicherung ──────────────────────────────────────────────

@router.post("/vollmacht/erstellen")
async def vollmacht_erstellen(
    request: Request,
    person: str = Form(default=""),
):
    if not person:
        return _fehler("Bitte eine Person auswählen.")
    db = get_db(request)
    konfig = _get_absender(request)
    versicherter = db.versicherter_laden(person, get_owner_id(request))
    if not versicherter:
        return _fehler(f"Keine Versicherten-Daten für {person}.")
    if not konfig.absender_name or not konfig.absender_adresse:
        return _fehler("Absender fehlt – bitte Einstellungen ausfüllen.")

    try:
        zielordner = _zielordner(request, f"{date.today().year}/{person}")
        zielordner.mkdir(parents=True, exist_ok=True)
        dateiname = f"Vollmacht_PV_{person.replace(' ', '_')}.pdf"

        from vollmacht_pv import erstelle_vollmacht_pdf
        pfad = erstelle_vollmacht_pdf(
            pfad=zielordner / dateiname,
            versicherter_name=versicherter.name,
            versicherter_adresse=versicherter.adresse,
            versicherungsnr=versicherter.versicherungsnr,
            bevollmaechtigter_name=konfig.absender_name,
            bevollmaechtigter_adresse=konfig.absender_adresse,
            bevollmaechtigter_geburtsdatum=konfig.absender_geburtsdatum,
            kk_name=versicherter.krankenkasse,
            kk_adresse=versicherter.krankenkasse_adresse,
        )
        log.info("Vollmacht erstellt: %s", pfad)
        return FileResponse(str(pfad), media_type="application/pdf", filename=dateiname)
    except Exception as exc:
        log.error("Vollmacht Fehler: %s", exc, exc_info=True)
        return _fehler("Vollmacht fehlgeschlagen – Details im Log.")
