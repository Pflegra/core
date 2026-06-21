"""
Router: Pflege-Einträge (Liste, Neu, Bearbeiten, Löschen)
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from models import (
    ART_STUNDENWEISE, ERSATZ_PRIVAT, ERSATZ_ARTEN,
    GRUND_URLAUB, MONATE_DE, PFLEGE_ARTEN, PFLEGE_GRUENDE,
    PflegeEintrag,
)

from web.routers.deps import redirect,\
     TEMPLATES, base_ctx, get_db, get_konfig, get_owner_id, audit_log
from web.validation import Validierungsfehler, validiere_eintrag
from db.audit import AuditEvent

router = APIRouter(prefix="/eintraege", tags=["Einträge"])


def _personen_und_jahre(db, request=None):
    owner_id = get_owner_id(request) if request else 0
    personen = db.personen(owner_id)
    jahre    = db.jahre(owner_id) or [date.today().year]
    return personen, jahre


def _formular_ctx(request, titel, aktion, eintrag, personen, fehler=None, **extra):
    db = get_db(request)
    owner_id = get_owner_id(request)
    # Ersatzpflegekräfte für gewählte Person laden
    person = (eintrag.person if eintrag else "") or extra.get("person", "")
    ersatzliste = db.ersatz_alle(person, owner_id) if person else []
    letzten_ersatz = db.ersatz_letzten(person, owner_id) if person else None
    return {
        **base_ctx(request),
        "titel":          titel,
        "aktion":         aktion,
        "eintrag":        eintrag,
        "personen":       personen,
        "pflege_arten":   PFLEGE_ARTEN,
        "pflege_gruende": PFLEGE_GRUENDE,
        "ersatz_arten":   ERSATZ_ARTEN,
        "ersatzliste":    ersatzliste,
        "letzten_ersatz": letzten_ersatz,
        "fehler":         fehler,
        **extra,
    }


# ── Liste ─────────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def eintraege_liste(
    request: Request,
    person: str = "",
    jahr: int = 0,
    monat: int = 0,
    suche: str = "",
):
    db = get_db(request)
    personen, jahre = _personen_und_jahre(db, request)

    if suche:
        eintraege = db.suche(suche)
        # Suche + Person/Jahr filtern
        if person:
            eintraege = [e for e in eintraege if e.person == person]
        if jahr:
            eintraege = [e for e in eintraege if e.datum.year == jahr]
        if monat:
            eintraege = [e for e in eintraege if e.datum.month == monat]
    elif monat and person:
        eintraege = db.nach_monat(person, jahr or date.today().year, monat, get_owner_id(request))
    elif monat:
        # Monat ohne Person — alle Personen
        alle = db.alle(get_owner_id(request))
        j = jahr or date.today().year
        eintraege = [e for e in alle if e.datum.year == j and e.datum.month == monat]
    elif jahr and person:
        eintraege = db.nach_person_und_jahr(person, jahr, get_owner_id(request))
    elif jahr:
        alle = db.alle(get_owner_id(request))
        eintraege = [e for e in alle if e.datum.year == jahr]
    elif person:
        alle = db.alle(get_owner_id(request))
        eintraege = [e for e in alle if e.person == person]
    else:
        eintraege = db.alle(get_owner_id(request))

    return TEMPLATES.TemplateResponse(request, "eintraege/liste.html", {
        **base_ctx(request),
        "eintraege": eintraege,
        "personen": personen,
        "jahre": jahre,
        "monate": [(i, MONATE_DE[i]) for i in range(1, 13)],
        "filter_person": person,
        "filter_jahr": jahr,
        "filter_monat": monat,
        "suche": suche,
        "art_stundenweise": ART_STUNDENWEISE,
        "art_tageweise": "tageweise",
    })


# ── Neu ───────────────────────────────────────────────────────────────────────

@router.get("/neu", response_class=HTMLResponse)
async def eintrag_neu_form(request: Request, person: str = ""):
    db = get_db(request)
    personen = db.personen(get_owner_id(request))
    if person not in personen:
        person = personen[0] if personen else ""
    heute = date.today()
    return TEMPLATES.TemplateResponse(request, "eintraege/formular.html",
        _formular_ctx(request, "Neuer Eintrag", "/eintraege/neu", None, personen,
                      heute=heute.isoformat(), person=person))


@router.post("/neu", response_class=HTMLResponse)
async def eintrag_neu_speichern(
    request: Request,
    datum:          str = Form(...),
    von:            str = Form(...),
    bis:            str = Form(...),
    stunden:        str = Form(...),
    person:         str = Form(...),
    art:            str = Form(ART_STUNDENWEISE),
    grund:          str = Form(GRUND_URLAUB),
    ersatz_name:    str = Form(""),
    ersatz_art:     str = Form(ERSATZ_PRIVAT),
    ersatz_adresse: str = Form(""),
    notiz:          str = Form(""),
):
    db = get_db(request)
    personen = db.personen(get_owner_id(request))
    try:
        felder = validiere_eintrag(
            datum, von, bis, stunden, person, art, grund,
            ersatz_name, ersatz_art, ersatz_adresse, notiz,
        )
        eintrag = PflegeEintrag.from_datum(**felder)
        eintrag.owner_id = get_owner_id(request)
        db.insert(eintrag)
        audit_log(request, AuditEvent.EINTRAG_ERSTELLT,
                  f"{eintrag.art} · {eintrag.person} · {eintrag.datum}")
        return redirect(request, "/eintraege/?ok=1", 303)
    except (Validierungsfehler, ValueError) as exc:
        return TEMPLATES.TemplateResponse(request, "eintraege/formular.html",
            _formular_ctx(request, "Neuer Eintrag", "/eintraege/neu", None, personen,
                          fehler=str(exc), heute=datum,
                          datum=datum, von=von, bis=bis, stunden=stunden,
                          person=person, art=art, grund=grund,
                          ersatz_name=ersatz_name, ersatz_art=ersatz_art,
                          ersatz_adresse=ersatz_adresse, notiz=notiz),
            status_code=422)


# ── Bearbeiten ────────────────────────────────────────────────────────────────

@router.get("/{eintrag_id}/bearbeiten", response_class=HTMLResponse)
async def eintrag_bearbeiten_form(request: Request, eintrag_id: int):
    db = get_db(request)
    alle = db.alle(get_owner_id(request))
    eintrag = next((e for e in alle if e.id == eintrag_id), None)
    if not eintrag:
        raise HTTPException(404, "Eintrag nicht gefunden")
    personen = db.personen(get_owner_id(request))
    return TEMPLATES.TemplateResponse(request, "eintraege/formular.html",
        _formular_ctx(request, "Eintrag bearbeiten",
                      f"/eintraege/{eintrag_id}/bearbeiten",
                      eintrag, personen, heute=eintrag.datum.isoformat()))


@router.post("/{eintrag_id}/bearbeiten", response_class=HTMLResponse)
async def eintrag_bearbeiten_speichern(
    request: Request,
    eintrag_id:     int,
    datum:          str = Form(...),
    von:            str = Form(...),
    bis:            str = Form(...),
    stunden:        str = Form(...),
    person:         str = Form(...),
    art:            str = Form(ART_STUNDENWEISE),
    grund:          str = Form(GRUND_URLAUB),
    ersatz_name:    str = Form(""),
    ersatz_art:     str = Form(ERSATZ_PRIVAT),
    ersatz_adresse: str = Form(""),
    notiz:          str = Form(""),
):
    db = get_db(request)
    personen = db.personen(get_owner_id(request))
    try:
        felder = validiere_eintrag(
            datum, von, bis, stunden, person, art, grund,
            ersatz_name, ersatz_art, ersatz_adresse, notiz,
        )
        eintrag = PflegeEintrag.from_datum(**felder)
        eintrag.id = eintrag_id
        db.update(eintrag)
        audit_log(request, AuditEvent.EINTRAG_BEARBEITET,
                  f"{eintrag.art} · {eintrag.person} · {eintrag.datum} (ID {eintrag_id})")
        return redirect(request, "/eintraege/?ok=1", 303)
    except (Validierungsfehler, ValueError) as exc:
        alle = db.alle(get_owner_id(request))
        orig = next((e for e in alle if e.id == eintrag_id), None)
        return TEMPLATES.TemplateResponse(request, "eintraege/formular.html",
            _formular_ctx(request, "Eintrag bearbeiten",
                          f"/eintraege/{eintrag_id}/bearbeiten",
                          orig, personen, fehler=str(exc), heute=datum),
            status_code=422)


from typing import List

# ── Bulk-Löschen ──────────────────────────────────────────────────────────────

@router.post("/bulk-loeschen")
async def eintraege_bulk_loeschen(
    request: Request,
    ids: List[int] = Form(default=[]),
):
    if not ids:
        return redirect(request, "/eintraege/?fehler=keine_auswahl", 303)
    db = get_db(request)
    n = db.bulk_loeschen(ids)
    return redirect(request, f"/eintraege/?geloescht={n}", 303)

@router.post("/{eintrag_id}/loeschen")
async def eintrag_loeschen(request: Request, eintrag_id: int):
    db = get_db(request)
    audit_log(request, AuditEvent.EINTRAG_GELOESCHT, f"Eintrag ID {eintrag_id}")
    db.loeschen(eintrag_id)
    return redirect(request, "/eintraege/?geloescht=1", 303)
