"""
Router: Personen verwalten
"""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse


from web.routers.deps import redirect,\
     TEMPLATES, base_ctx, get_db, get_owner_id
from web.validation import Validierungsfehler, validiere_person_name

router = APIRouter(prefix="/personen", tags=["Personen"])


def _fehler(msg: str) -> RedirectResponse:
    return redirect(request, f"/personen/?fehler={quote(msg, 303)}", status_code=303)


@router.get("/", response_class=HTMLResponse)
async def personen_liste(request: Request, fehler: str = "", ok: str = ""):
    db = get_db(request)
    personen = db.personen_liste(get_owner_id(request))
    return TEMPLATES.TemplateResponse(request, "personen/liste.html", {
        **base_ctx(request),
        "personen": personen,
        "fehler": fehler,
        "ok": ok,
    })


@router.post("/neu")
async def person_anlegen(request: Request, name: str = Form(...), notiz: str = Form("")):
    db = get_db(request)
    try:
        name_s = validiere_person_name(name)
        ok = db.person_anlegen(name_s, notiz.strip(), get_owner_id(request))
        if not ok:
            return _fehler("Person bereits vorhanden.")
    except (Validierungsfehler, ValueError) as exc:
        return _fehler(str(exc))
    return redirect(request, "/personen/?ok=1", 303)


@router.post("/{name}/umbenennen")
async def person_umbenennen(request: Request, name: str, neuer_name: str = Form(...)):
    db = get_db(request)
    try:
        neuer_name_s = validiere_person_name(neuer_name)
        ok = db.person_umbenennen(name, neuer_name_s)
        if not ok:
            return _fehler("Umbenennung fehlgeschlagen.")
    except (Validierungsfehler, ValueError) as exc:
        return _fehler(str(exc))
    return redirect(request, "/personen/?ok=1", 303)


@router.post("/{name}/loeschen")
async def person_loeschen(request: Request, name: str, mit_eintraegen: bool = Form(False)):
    db = get_db(request)
    owner_id = get_owner_id(request)
    if mit_eintraegen:
        db.person_loeschen_mit_eintraegen(name, owner_id)
    else:
        ok, n = db.person_loeschen(name, owner_id)
        if not ok:
            return _fehler(f"Person hat {n} Einträge – bitte mit Einträgen löschen.")
    return redirect(request, "/personen/?ok=1", 303)
