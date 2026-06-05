"""
Router: Backup & Restore
Erstellen, Auflisten und Wiederherstellen von Datenbank-Backups.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse


from web.csrf import pruefe_csrf_request, csrf_fehler
from web.routers.deps import redirect,\
     TEMPLATES, base_ctx

router = APIRouter(prefix="/backup", tags=["Backup"])


def _get_backup_service(request: Request):
    return request.app.state.backup_service


# ── Übersicht ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def backup_uebersicht(request: Request, ok: str = "", fehler: str = ""):
    svc = _get_backup_service(request)
    backups = svc.liste_backups()

    backup_infos = []
    for p in backups:
        stat = p.stat()
        backup_infos.append({
            "name": p.name,
            "pfad": str(p),
            "groesse_kb": round(stat.st_size / 1024, 1),
            "datum": p.name.split("_")[1] if "_" in p.name else "",
            "uhrzeit": p.name.split("_")[2] if p.name.count("_") >= 2 else "",
            "grund": p.stem.split("_")[-1] if "_" in p.stem else "",
        })

    gesamt_kb = round(svc.backup_groesse() / 1024, 1)

    return TEMPLATES.TemplateResponse(request, "backup/uebersicht.html", {
        **base_ctx(request),
        "backups": backup_infos,
        "gesamt_kb": gesamt_kb,
        "ok": ok,
        "fehler": fehler,
    })


# ── Manuelles Backup erstellen ───────────────────────────────────────────────

@router.post("/erstellen")
async def backup_erstellen(request: Request):
    if not await pruefe_csrf_request(request):
        return csrf_fehler(request)
    svc = _get_backup_service(request)
    result = svc.erstelle_backup(grund="manuell")
    if result:
        return redirect(request, "/backup/?ok=erstellt", 303)
    return redirect(request, "/backup/?fehler=db_nicht_gefunden", 303)


# ── Backup herunterladen ─────────────────────────────────────────────────────

@router.get("/herunterladen")
async def backup_herunterladen(request: Request, pfad: str):
    p = Path(pfad)
    svc = _get_backup_service(request)
    erlaubte = [str(b) for b in svc.liste_backups()]
    if str(p) not in erlaubte or not p.exists():
        return redirect(request, "/backup/?fehler=nicht_gefunden", 303)
    return FileResponse(
        path=str(p),
        filename=p.name,
        media_type="application/octet-stream")


# ── Backup wiederherstellen ──────────────────────────────────────────────────

@router.post("/wiederherstellen")
async def backup_wiederherstellen(request: Request,
 pfad: str = Form(...)):
    p = Path(pfad)
    svc = _get_backup_service(request)
    erlaubte = [str(b) for b in svc.liste_backups()]
    if str(p) not in erlaubte:
        return redirect(request, "/backup/?fehler=nicht_gefunden", 303)

    # Vor Wiederherstellung: DB neu laden
    ok = svc.wiederherstellen(p)
    if ok:
        # DB-Verbindung neu initialisieren
        try:
            from models import PflegraDB
            db_pfad = request.app.state.backup_service._db_pfad
            request.app.state.db = PflegraDB(db_pfad)
            # Services mit neuer DB aktualisieren
            konfig = request.app.state.konfig
            from services.budget_service import BudgetService
            from services.export_service import ExportService
            from services.import_service import ImportService
            request.app.state.budget_service = BudgetService(request.app.state.db, konfig)
            request.app.state.export_service = ExportService(request.app.state.db, konfig)
            request.app.state.import_service = ImportService(request.app.state.db)
        except Exception:
            pass
        return redirect(request, "/backup/?ok=wiederhergestellt", 303)
    return redirect(request, "/backup/?fehler=wiederherstellung_fehlgeschlagen", 303)


# ── Backup löschen ───────────────────────────────────────────────────────────

@router.post("/loeschen")
async def backup_loeschen(request: Request,
 pfad: str = Form(...)):
    p = Path(pfad)
    svc = _get_backup_service(request)
    erlaubte = [str(b) for b in svc.liste_backups()]
    if str(p) not in erlaubte:
        return redirect(request, "/backup/?fehler=nicht_gefunden", 303)
    try:
        p.unlink()
        return redirect(request, "/backup/?ok=geloescht", 303)
    except Exception:
        return redirect(request, "/backup/?fehler=loeschen_fehlgeschlagen", 303)
