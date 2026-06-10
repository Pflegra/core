"""
Router: Pflegetagebuch
"""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from web.routers.deps import redirect,\
     TEMPLATES, base_ctx, get_db, get_owner_id
from db.tagebuch import TagebuchEintrag, KATEGORIEN, KATEGORIEN_LABELS, STIMMUNG_LABELS

router = APIRouter(prefix="/tagebuch", tags=["Tagebuch"])


@router.get("/", response_class=HTMLResponse)
async def tagebuch_liste(request: Request, person: str = "", kategorie: str = ""):
    db = get_db(request)
    owner_id = get_owner_id(request)
    eintraege = db.tagebuch_alle(owner_id, person, kategorie)
    personen = db.personen(owner_id)
    statistik = db.tagebuch_statistik(owner_id, person)
    return TEMPLATES.TemplateResponse(request, "tagebuch/liste.html", {
        **base_ctx(request),
        "eintraege":        eintraege,
        "personen":         personen,
        "kategorien":       KATEGORIEN,
        "kategorien_labels": KATEGORIEN_LABELS,
        "stimmung_labels":  STIMMUNG_LABELS,
        "filter_person":    person,
        "filter_kategorie": kategorie,
        "statistik":        statistik,
    })


@router.get("/neu", response_class=HTMLResponse)
async def tagebuch_neu(request: Request, person: str = ""):
    db = get_db(request)
    owner_id = get_owner_id(request)
    personen = db.personen(owner_id)
    return TEMPLATES.TemplateResponse(request, "tagebuch/form.html", {
        **base_ctx(request),
        "eintrag":          None,
        "personen":         personen,
        "kategorien":       KATEGORIEN,
        "kategorien_labels": KATEGORIEN_LABELS,
        "stimmung_labels":  STIMMUNG_LABELS,
        "heute":            date.today().isoformat(),
        "vorauswahl_person": person,
    })


@router.post("/neu", response_class=RedirectResponse)
async def tagebuch_neu_speichern(request: Request):
    db = get_db(request)
    owner_id = get_owner_id(request)
    form = await request.form()

    stimmung = form.get("stimmung")
    e = TagebuchEintrag(
        id=None,
        owner_id=owner_id,
        person=str(form.get("person", "")).strip(),
        datum=str(form.get("datum", date.today().isoformat())),
        uhrzeit=str(form.get("uhrzeit", "")),
        kategorie=str(form.get("kategorie", "allgemein")),
        titel=str(form.get("titel", "")).strip(),
        inhalt=str(form.get("inhalt", "")).strip(),
        stimmung=int(stimmung) if stimmung and stimmung.isdigit() else None,
        tags=str(form.get("tags", "")).strip(),
    )
    db.tagebuch_speichern(e)
    return redirect(request, "/tagebuch/", 303)


@router.get("/{eintrag_id}/bearbeiten", response_class=HTMLResponse)
async def tagebuch_bearbeiten(request: Request, eintrag_id: int):
    db = get_db(request)
    owner_id = get_owner_id(request)
    eintrag = db.tagebuch_laden(eintrag_id, owner_id)
    if not eintrag:
        return redirect(request, "/tagebuch/", 303)
    personen = db.personen(owner_id)
    return TEMPLATES.TemplateResponse(request, "tagebuch/form.html", {
        **base_ctx(request),
        "eintrag":          eintrag,
        "personen":         personen,
        "kategorien":       KATEGORIEN,
        "kategorien_labels": KATEGORIEN_LABELS,
        "stimmung_labels":  STIMMUNG_LABELS,
        "heute":            date.today().isoformat(),
        "vorauswahl_person": eintrag.person,
    })


@router.post("/{eintrag_id}/bearbeiten", response_class=RedirectResponse)
async def tagebuch_bearbeiten_speichern(request: Request, eintrag_id: int):
    db = get_db(request)
    owner_id = get_owner_id(request)
    form = await request.form()
    stimmung = form.get("stimmung")
    e = TagebuchEintrag(
        id=eintrag_id,
        owner_id=owner_id,
        person=str(form.get("person", "")).strip(),
        datum=str(form.get("datum", date.today().isoformat())),
        uhrzeit=str(form.get("uhrzeit", "")),
        kategorie=str(form.get("kategorie", "allgemein")),
        titel=str(form.get("titel", "")).strip(),
        inhalt=str(form.get("inhalt", "")).strip(),
        stimmung=int(stimmung) if stimmung and stimmung.isdigit() else None,
        tags=str(form.get("tags", "")).strip(),
    )
    db.tagebuch_speichern(e)
    return redirect(request, "/tagebuch/", 303)


@router.post("/{eintrag_id}/loeschen", response_class=JSONResponse)
async def tagebuch_loeschen(request: Request, eintrag_id: int):
    db = get_db(request)
    owner_id = get_owner_id(request)
    ok = db.tagebuch_loeschen(eintrag_id, owner_id)
    return {"ok": ok}
