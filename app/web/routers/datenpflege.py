"""
Router: Datenpflege
Duplikat-Erkennung, Datenqualität.
"""
from __future__ import annotations

import logging
from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List

from web.routers.deps import redirect,\
     TEMPLATES, base_ctx, get_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/datenpflege", tags=["Datenpflege"])


@router.get("/", response_class=HTMLResponse)
async def datenpflege_uebersicht(request: Request, ok: str = "", fehler: str = ""):
    db = get_db(request)
    duplikate = db.duplikate_finden()
    return TEMPLATES.TemplateResponse(request, "datenpflege/uebersicht.html", {
        **base_ctx(request),
        "duplikate": duplikate,
        "ok": ok,
        "fehler": fehler,
    })


@router.post("/duplikat-loeschen")
async def duplikat_loeschen(request: Request, ids: List[int] = Form(default=[])):
    if not ids:
        return redirect(request, "/datenpflege/?fehler=keine_auswahl", 303)
    db = get_db(request)
    n = db.bulk_loeschen(ids)
    log.info("Duplikate gelöscht: %d Einträge", n)
    return redirect(request, f"/datenpflege/?ok={n}_duplikate_geloescht", 303)
