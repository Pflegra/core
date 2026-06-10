"""
Router: Gutachten-Analyse
PDF-Upload, Analyse und Anzeige von MD/MDK-Gutachten.
"""
from __future__ import annotations

import os
import json
import shutil
import logging
import tempfile
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from web.routers.deps import TEMPLATES, base_ctx, get_owner_id, redirect

log = logging.getLogger(__name__)

router = APIRouter(prefix="/gutachten", tags=["Gutachten"])

# Max Upload-Größe: 20 MB
MAX_SIZE_MB = 50


@router.get("/", response_class=HTMLResponse)
async def gutachten_uebersicht(request: Request):
    """Übersicht: alle gespeicherten Analysen + Upload-Formular."""
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    analysen = _lade_analysen(request, owner_id)

    return TEMPLATES.TemplateResponse(request, "gutachten/index.html", {
        **base_ctx(request),
        "analysen": analysen,
    })


@router.post("/analysieren")
async def gutachten_analysieren(
    request: Request,
    pdf_datei: UploadFile = File(...),
    person: str = Form(""),
):
    """PDF hochladen und analysieren."""
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)

    # Datei prüfen
    if not pdf_datei.filename.lower().endswith(".pdf"):
        return redirect(request, "/gutachten/?fehler=kein_pdf", 303)

    # Temporäre Datei
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_pfad = tmp.name
        inhalt = await pdf_datei.read()

        if len(inhalt) > MAX_SIZE_MB * 1024 * 1024:
            os.unlink(tmp_pfad)
            return redirect(request, "/gutachten/?fehler=zu_gross", 303)

        tmp.write(inhalt)

    try:
        from gutachten_parser import gutachten_analysieren as parse
        ergebnis = parse(tmp_pfad)
    except Exception as e:
        log.error("Gutachten-Analyse fehlgeschlagen: %s", e, exc_info=True)
        os.unlink(tmp_pfad)
        return redirect(request, "/gutachten/?fehler=analyse_fehler", 303)
    finally:
        try:
            os.unlink(tmp_pfad)
        except Exception:
            pass

    # Person aus Formular oder Dateinamen
    if not person:
        person = pdf_datei.filename.replace(".pdf", "").replace("_", " ")

    # Ergebnis speichern
    analyse_id = _speichere_analyse(request, owner_id, person, ergebnis)

    # Audit-Log
    try:
        from db.audit import AuditRepo, AuditEvent
        from web.auth import get_aktueller_user_id
        actor_id = get_aktueller_user_id(request)
        ip = request.client.host if request.client else ""
        pg_info = f"PG {ergebnis.pflegegrad}" if ergebnis.pflegegrad else "PG unbekannt"
        audit = AuditRepo(request.app.state.db._schema)
        audit.loggen(
            aktion=AuditEvent.GUTACHTEN_ANALYSE,
            actor_user_id=actor_id,
            effective_user_id=owner_id,
            details=f"Gutachten analysiert: {person} · {pg_info} · {ergebnis.gutachten_typ or 'Typ unbekannt'}",
            ip_adresse=ip,
        )
    except Exception as e:
        log.warning("Audit-Log für Gutachten fehlgeschlagen: %s", e)

    return RedirectResponse(f"/gutachten/{analyse_id}", status_code=303)


@router.get("/neueste")
async def gutachten_neueste(request: Request):
    """Weiterleitung zur neuesten Analyse."""
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    analysen = _lade_analysen(request, owner_id)

    if analysen:
        return redirect(request, f"/gutachten/{analysen[0]['id']}", 303)
    return redirect(request, "/gutachten/", 303)



@router.get("/{analyse_id}", response_class=HTMLResponse)
async def gutachten_detail(request: Request, analyse_id: str):
    """Detailansicht einer Gutachten-Analyse."""
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    analyse = _lade_analyse(request, owner_id, analyse_id)

    if not analyse:
        return redirect(request, "/gutachten/?fehler=nicht_gefunden", 303)

    return TEMPLATES.TemplateResponse(request, "gutachten/detail.html", {
        **base_ctx(request),
        "analyse": analyse,
    })


@router.post("/{analyse_id}/loeschen")
async def gutachten_loeschen(request: Request, analyse_id: str):
    """Analyse löschen."""
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    _loesche_analyse(request, owner_id, analyse_id)
    return redirect(request, "/gutachten/", 303)


# ── Speicher-Hilfsfunktionen ──────────────────────────────────────────────────

def _gutachten_dir(request: Request, owner_id: int) -> Path:
    data_dir = request.app.state.data_dir
    d = Path(data_dir) / "gutachten" / str(owner_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _speichere_analyse(request, owner_id: int, person: str, ergebnis) -> str:
    """Speichert Analyse als JSON, gibt ID zurück."""
    import uuid
    analyse_id = str(uuid.uuid4())[:8]
    d = _gutachten_dir(request, owner_id)

    daten = {
        "id": analyse_id,
        "person": person,
        "erstellt_am": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "gutachten_datum": ergebnis.gutachten_datum,
        "gutachten_typ": ergebnis.gutachten_typ,
        "bisheriger_pflegegrad": ergebnis.bisheriger_pflegegrad,
        "pflegegrad": ergebnis.pflegegrad,
        "pflegegrad_seit": ergebnis.pflegegrad_seit,
        "gesamtpunkte": ergebnis.gesamtpunkte,
        "konfidenz": ergebnis.konfidenz,
        "ocr_verwendet": ergebnis.ocr_verwendet,
        "diagnosen": ergebnis.diagnosen,
        "module": [
            {
                "nummer": m.nummer,
                "name": m.name,
                "einzelpunkte": m.einzelpunkte,
                "gewichtete_punkte": m.gewichtete_punkte,
                "gewichtung_prozent": m.gewichtung_prozent,
            }
            for m in ergebnis.module
        ],
    }

    with open(d / f"{analyse_id}.json", "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2)

    return analyse_id


def _lade_analysen(request, owner_id: int) -> list[dict]:
    d = _gutachten_dir(request, owner_id)
    analysen = []
    for f in sorted(d.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(f, encoding="utf-8") as fh:
                analysen.append(json.load(fh))
        except Exception:
            pass
    return analysen


def _lade_analyse(request, owner_id: int, analyse_id: str) -> dict | None:
    d = _gutachten_dir(request, owner_id)
    pfad = d / f"{analyse_id}.json"
    if not pfad.exists():
        return None
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _loesche_analyse(request, owner_id: int, analyse_id: str):
    d = _gutachten_dir(request, owner_id)
    pfad = d / f"{analyse_id}.json"
    if pfad.exists():
        pfad.unlink()
