"""Router: Entlastungsbetrag-Buchungen (§ 45b SGB XI)"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse

from models import EntlastungBuchung
from pflege_rules import get_regelwerk
from web.routers.deps import redirect,\
     TEMPLATES, base_ctx, get_db, get_owner_id

log = logging.getLogger(__name__)
router = APIRouter(prefix="/entlastung", tags=["entlastung"])

MONATE = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
          "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

PLANER_PERSON = "__planer__"


def _vorjahr_guthaben(db, jahr: int, owner_id: int) -> float:
    """Liest das Entlastungsbetrag-Vorjahresguthaben aus dem Budgetplaner."""
    try:
        roh = db.planung_laden(PLANER_PERSON, jahr, owner_id)
        eintrag_0 = roh.get(0, {})
        extras = json.loads(eintrag_0.get("notiz", "{}") or "{}")
        return float(extras.get("vorjahr_guthaben", 0.0))
    except Exception:
        return 0.0


def _fehler(msg: str, person: str = "", jahr: int = date.today().year):
    return RedirectResponse(
        f"/entlastung/?person={person}&jahr={jahr}&fehler={msg}",
        status_code=303,
    )


@router.get("/", response_class=HTMLResponse)
async def entlastung_uebersicht(
    request: Request,
    person:  str = "",
    jahr:    int = 0,
    ok:      str = "",
    fehler:  str = "",
):
    db       = get_db(request)
    owner_id = get_owner_id(request)
    personen = db.personen(owner_id)
    jahr     = jahr or date.today().year
    regeln   = get_regelwerk(jahr)
    monatlich = regeln.entlastungsbetrag_monatlich  # 131 €

    # Vorjahresguthaben aus Budgetplaner
    vorjahr_guthaben = _vorjahr_guthaben(db, jahr, owner_id)
    vorjahr_nutzbar  = date.today() <= date(jahr, 6, 30)
    vorjahr_aktiv    = vorjahr_guthaben > 0 and vorjahr_nutzbar

    buchungen = db.entlastung_alle(person, owner_id, jahr) if person else []

    # Monatsübersicht aufbauen
    monate = []
    gesamt_verbraucht = 0.0
    for m in range(1, 13):
        verbraucht = db.entlastung_summe(person, owner_id, jahr, m) if person else 0.0
        rest = max(0.0, monatlich - verbraucht)
        gesamt_verbraucht += verbraucht
        monate.append({
            "nr":         m,
            "name":       MONATE[m - 1],
            "monatlich":  monatlich,
            "verbraucht": verbraucht,
            "rest":       rest,
            "voll":       verbraucht >= monatlich,
        })

    jahresmax        = monatlich * 12
    verfuegbar_gesamt = jahresmax + (vorjahr_guthaben if vorjahr_aktiv else 0.0)
    jahres_rest      = max(0.0, verfuegbar_gesamt - gesamt_verbraucht)

    return TEMPLATES.TemplateResponse(request, "entlastung/uebersicht.html", {
        **base_ctx(request),
        "personen":             personen,
        "gewaehlte_person":     person,
        "jahr":                 jahr,
        "jahre":                list(range(date.today().year, date.today().year - 4, -1)),
        "buchungen":            buchungen,
        "monate":               monate,
        "monatlich":            monatlich,
        "jahresmax":            jahresmax,
        "vorjahr_guthaben":     vorjahr_guthaben,
        "vorjahr_nutzbar":      vorjahr_nutzbar,
        "vorjahr_aktiv":        vorjahr_aktiv,
        "verfuegbar_gesamt":    verfuegbar_gesamt,
        "gesamt_verbraucht":    gesamt_verbraucht,
        "jahres_rest":          jahres_rest,
        "ok":                   ok,
        "fehler":               fehler,
        "heute":                date.today().isoformat(),
    })


@router.post("/buchen")
async def entlastung_buchen(
    request:     Request,
    person:      str   = Form(...),
    datum:       str   = Form(...),
    betrag:      str   = Form(...),
    anbieter:    str   = Form(default=""),
    beschreibung: str  = Form(default=""),
    beleg_nr:    str   = Form(default=""),
    jahr:        int   = Form(default=0),
):
    db       = get_db(request)
    owner_id = get_owner_id(request)

    try:
        betrag_f = float(betrag.replace(",", "."))
        if betrag_f <= 0:
            raise ValueError
    except ValueError:
        return _fehler("Ungültiger Betrag.", person, jahr or date.today().year)

    b = EntlastungBuchung(
        owner_id=owner_id,
        person=person,
        datum=datum,
        betrag=betrag_f,
        anbieter=anbieter.strip(),
        beschreibung=beschreibung.strip(),
        beleg_nr=beleg_nr.strip(),
    )
    db.entlastung_speichern(b)
    log.info("Entlastungsbuchung gespeichert: %s %s %.2f€", person, datum, betrag_f)

    j = int(datum[:4]) if datum else (jahr or date.today().year)
    return RedirectResponse(
        f"/entlastung/?person={person}&jahr={j}&ok=Buchung+gespeichert",
        status_code=303,
    )


@router.post("/{buchung_id}/loeschen")
async def entlastung_loeschen(
    request:    Request,
    buchung_id: int,
    person:     str = Form(...),
    jahr:       int = Form(default=0),
):
    db       = get_db(request)
    owner_id = get_owner_id(request)
    db.entlastung_loeschen(buchung_id, owner_id)
    return RedirectResponse(
        f"/entlastung/?person={person}&jahr={jahr}&ok=Buchung+gelöscht",
        status_code=303,
    )


@router.get("/pdf")
async def entlastung_pdf(
    request: Request,
    person:  str = "",
    jahr:    int = 0,
):
    import os
    from entlastung_export import erstelle_entlastung_pdf

    db       = get_db(request)
    owner_id = get_owner_id(request)
    jahr     = jahr or date.today().year

    if not person:
        return redirect(request, "/entlastung/", 303)

    regeln   = get_regelwerk(jahr)
    monatlich = regeln.entlastungsbetrag_monatlich

    vorjahr_guthaben = _vorjahr_guthaben(db, jahr, owner_id)
    vorjahr_nutzbar  = date.today() <= date(jahr, 6, 30)
    vorjahr_aktiv    = vorjahr_guthaben > 0 and vorjahr_nutzbar

    buchungen = db.entlastung_alle(person, owner_id, jahr)

    monate = []
    gesamt_verbraucht = 0.0
    for m in range(1, 13):
        verbraucht = db.entlastung_summe(person, owner_id, jahr, m)
        rest = max(0.0, monatlich - verbraucht)
        gesamt_verbraucht += verbraucht
        monate.append({
            "nr": m, "name": MONATE[m - 1],
            "monatlich": monatlich, "verbraucht": verbraucht, "rest": rest,
            "voll": verbraucht >= monatlich,
        })

    jahresmax         = monatlich * 12
    verfuegbar_gesamt = jahresmax + (vorjahr_guthaben if vorjahr_aktiv else 0.0)
    jahres_rest       = max(0.0, verfuegbar_gesamt - gesamt_verbraucht)

    data_dir = os.environ.get("PFLEGRA_DATA", "/share/pflegra")
    person_safe = person.replace(" ", "_").replace("/", "-")
    pfad = f"{data_dir}/Archiv/{jahr}/{person}/Entlastungsbetrag_{jahr}_{person_safe}.pdf"

    erstelle_entlastung_pdf(
        pfad=pfad,
        person=person,
        jahr=jahr,
        buchungen=buchungen,
        monatlich=monatlich,
        vorjahr_guthaben=vorjahr_guthaben,
        vorjahr_aktiv=vorjahr_aktiv,
        jahresmax=jahresmax,
        verfuegbar_gesamt=verfuegbar_gesamt,
        gesamt_verbraucht=gesamt_verbraucht,
        jahres_rest=jahres_rest,
        monate=monate,
    )

    log.info("Entlastungsbetrag PDF erstellt: %s", pfad)
    filename = f"Entlastungsbetrag_{jahr}_{person_safe}.pdf"
    return FileResponse(pfad, media_type="application/pdf", filename=filename)
