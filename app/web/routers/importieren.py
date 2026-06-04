"""
Router: CSV/XLSX/ODS-Import mit Vorschau
"""
from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse

from web.routers.deps import redirect,\
     TEMPLATES, base_ctx, get_db, get_import_service, get_owner_id
from web.validation import (
    MAX_UPLOAD_BYTES,
    Validierungsfehler,
    validiere_tmp_pfad,
    validiere_upload_datei,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/import", tags=["Import"])


def _fehler(msg: str) -> RedirectResponse:
    return redirect(request, f"/import/?fehler={quote(msg, 303)}", status_code=303)


@router.get("/", response_class=HTMLResponse)
async def import_seite(request: Request, ok: str = "", fehler: str = ""):
    db = get_db(request)
    personen = db.personen(get_owner_id(request))
    return TEMPLATES.TemplateResponse(request, "import/upload.html", {
        **base_ctx(request),
        "personen": personen,
        "ok": ok,
        "fehler": fehler,
        "max_mb": MAX_UPLOAD_BYTES // (1024 * 1024),
    })


@router.post("/vorschau", response_class=HTMLResponse)
async def import_vorschau(
    request: Request,
    datei: UploadFile = File(...),
    person_fallback: str = Form(""),
):
    service = get_import_service(request)
    db = get_db(request)
    personen = db.personen(get_owner_id(request))

    # Dateiname und Größe prüfen
    try:
        # Größe: erst lesen, dann prüfen (UploadFile hat keine size-Property vor dem Lesen)
        inhalt = await datei.read()
        suffix = validiere_upload_datei(datei.filename or "", len(inhalt))
    except Validierungsfehler as exc:
        return _fehler(str(exc))

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(inhalt)
            tmp_path = Path(tmp.name)

        if suffix == ".csv":
            vorschau = service.analysiere(tmp_path, person_fallback=person_fallback or None)
        else:
            vorschau = service.analysiere_tabelle(tmp_path, person_fallback=person_fallback or None)

        return TEMPLATES.TemplateResponse(request, "import/vorschau.html", {
            **base_ctx(request),
            "vorschau": vorschau,
            "personen": personen,
            "dateiname": datei.filename,
            "tmp_pfad": str(tmp_path),
            "suffix": suffix,
            "person_fallback": person_fallback,
        })
    except Validierungsfehler as exc:
        return _fehler(str(exc))
    except Exception as exc:
        log.error("Import-Vorschau Fehler: %s", exc, exc_info=True)
        return _fehler(f"Datei konnte nicht gelesen werden: {exc}")


@router.post("/durchfuehren")
async def import_durchfuehren(
    request: Request,
    tmp_pfad:        str = Form(...),
    suffix:          str = Form(".csv"),
    person_fallback: str = Form(""),
    auch_duplikate:  bool = Form(False),
):
    service = get_import_service(request)
    try:
        # Pfad-Traversal-Schutz
        tmp_path = validiere_tmp_pfad(tmp_pfad)

        # Suffix whitelist
        if suffix not in {".csv", ".xlsx", ".ods"}:
            raise Validierungsfehler(f"Ungültiges Format: {suffix!r}")

        if suffix == ".csv":
            vorschau = service.analysiere(tmp_path, person_fallback=person_fallback or None)
        else:
            vorschau = service.analysiere_tabelle(tmp_path, person_fallback=person_fallback or None)

        ergebnis = service.importiere(vorschau, auch_duplikate=auch_duplikate)
        tmp_path.unlink(missing_ok=True)
        return redirect(request, f"/import/?ok={quote(str(ergebnis, 303))}", status_code=303)
    except Validierungsfehler as exc:
        return _fehler(str(exc))
    except Exception as exc:
        log.error("Import-Durchführung Fehler: %s", exc, exc_info=True)
        return _fehler(f"Import fehlgeschlagen – Details im Log")
