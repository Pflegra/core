"""
Router: PDF- und CSV-Export
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
     TEMPLATES, base_ctx, get_db, get_export_service, get_konfig, get_owner_id

log = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["Export"])

# Kurzbezeichnungen für Dateinamen (kein Umlaut-Problem im FS)
MONATE_KURZ = [
    "", "Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
    "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
]


def _zielordner(request: Request, sub: str = "") -> Path:
    """Gibt DATA_DIR/Archiv[/sub] zurück — immer absolut."""
    data_dir = getattr(request.app.state, "data_dir", Path("."))
    basis = data_dir / "Archiv"
    return (basis / sub) if sub else basis


def _fehler_redirect(msg: str, status: int = 303) -> RedirectResponse:
    """Redirect mit URL-sicherem Fehlertext."""
    return redirect(request, f"/export/?fehler={quote(msg, safe='')}", status_code=status)


# ── Übersicht ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def export_uebersicht(request: Request, ok: str = "", fehler: str = ""):
    from i18n import get_lang, make_t
    db = get_db(request)
    personen = db.personen(get_owner_id(request))
    jahre = db.jahre(get_owner_id(request)) or [date.today().year]
    lang = get_lang(request)
    t = make_t(lang)
    monate_keys = ["januar","februar","maerz","april","mai","juni",
                   "juli","august","september","oktober","november","dezember"]
    monate = [(i+1, t(f"export.{monate_keys[i]}")) for i in range(12)]
    return TEMPLATES.TemplateResponse(request, "export/uebersicht.html", {
        **base_ctx(request),
        "personen": personen,
        "jahre": jahre,
        "monate": monate,
        "ok": ok,
        "fehler": fehler,
    })


# ── Monats-PDF ───────────────────────────────────────────────────────────────

@router.post("/pdf/monat")
async def export_pdf_monat(
    request: Request,
    person: str = Form(...),
    jahr: int = Form(...),
    monat: int = Form(...),
):
    if not (1 <= monat <= 12):
        return _fehler_redirect("Ungültiger Monat")
    service = get_export_service(request)
    try:
        zielordner = _zielordner(request, f"{jahr}/{person}")
        pfad = service.pdf_monat(person, jahr, monat, zielordner=zielordner)
        return FileResponse(str(pfad), media_type="application/pdf", filename=pfad.name)
    except ValueError as exc:
        return _fehler_redirect(str(exc))
    except Exception as exc:
        log.error("PDF-Monat Fehler: %s", exc, exc_info=True)
        return _fehler_redirect("PDF-Erstellung fehlgeschlagen – Details im Log")


# ── Mehrmonats-PDF ───────────────────────────────────────────────────────────

@router.post("/pdf/monate")
async def export_pdf_monate(
    request: Request,
    person: str = Form(...),
    jahr: int = Form(...),
    monate: List[int] = Form(default=[]),
):
    if not monate:
        return _fehler_redirect("Bitte mindestens einen Monat auswählen")
    ungueltige = [m for m in monate if not (1 <= m <= 12)]
    if ungueltige:
        return _fehler_redirect("Ungültige Monatswerte")

    service = get_export_service(request)
    try:
        zielordner = _zielordner(request, f"{jahr}/{person}")
        # Lesbarer Dateiname: Jan-Mrz oder Jan_Mai_Sep
        monate_s = sorted(monate)
        if monate_s == list(range(monate_s[0], monate_s[-1] + 1)):
            # zusammenhängend → Bereich
            monate_str = f"{MONATE_KURZ[monate_s[0]]}-{MONATE_KURZ[monate_s[-1]]}"
        else:
            monate_str = "_".join(MONATE_KURZ[m] for m in monate_s)
        sicherer_name = person.replace(",", "").replace(" ", "_")
        dateiname = f"Nachweis_{monate_str}_{jahr}_{sicherer_name}.pdf"

        # Service mit explizitem Dateinamen aufrufen
        alle_eintraege = []
        from models import PflegraDB
        db = get_db(request)
        for monat in monate_s:
            alle_eintraege.extend(db.nach_monat(person, jahr, monat), get_owner_id(request))
        if not alle_eintraege:
            return _fehler_redirect(f"Keine Einträge für {person} in den gewählten Monaten")

        from pdf_export import exportiere_mehrere_monate_pdf
        konfig = get_konfig(request)
        zielordner.mkdir(parents=True, exist_ok=True)
        pfad = zielordner / dateiname
        exportiere_mehrere_monate_pdf(
            alle_eintraege, pfad, person, jahr, monate_s,
            pflegedienst=konfig.pflegedienst_name,
        )
        return FileResponse(str(pfad), media_type="application/pdf", filename=dateiname)
    except ValueError as exc:
        return _fehler_redirect(str(exc))
    except Exception as exc:
        log.error("PDF-Monate Fehler: %s", exc, exc_info=True)
        return _fehler_redirect("Mehrmonats-PDF fehlgeschlagen – Details im Log")


# ── Jahres-PDF ────────────────────────────────────────────────────────────────

@router.post("/pdf/jahr")
async def export_pdf_jahr(
    request: Request,
    person: str = Form(...),
    jahr: int = Form(...),
):
    service = get_export_service(request)
    try:
        zielordner = _zielordner(request, f"{jahr}/{person}")
        pfad = service.pdf_jahr(person, jahr, zielordner=zielordner)
        return FileResponse(str(pfad), media_type="application/pdf", filename=pfad.name)
    except ValueError as exc:
        return _fehler_redirect(str(exc))
    except Exception as exc:
        log.error("PDF-Jahr Fehler: %s", exc, exc_info=True)
        return _fehler_redirect("Jahres-PDF fehlgeschlagen – Details im Log")


# ── CSV-Export ────────────────────────────────────────────────────────────────

@router.post("/csv")
async def export_csv(
    request: Request,
    person: str = Form(""),
    jahr: int = Form(0),
):
    service = get_export_service(request)
    try:
        zielordner = _zielordner(request)
        zielordner.mkdir(parents=True, exist_ok=True)
        name_teil = f"_{person.replace(' ', '_')}" if person else ""
        jahr_teil = f"_{jahr}" if jahr else ""
        dateiname = f"pflegra{name_teil}{jahr_teil}.csv"
        pfad = zielordner / dateiname
        service.csv_export(pfad, person=person or None, jahr=jahr or None)
        return FileResponse(
            str(pfad),
            media_type="text/csv; charset=utf-8",
            filename=dateiname,
        )
    except ValueError as exc:
        return _fehler_redirect(str(exc))
    except Exception as exc:
        log.error("CSV-Export Fehler: %s", exc, exc_info=True)
        return _fehler_redirect("CSV-Export fehlgeschlagen – Details im Log")
