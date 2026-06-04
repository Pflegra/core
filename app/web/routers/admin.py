"""
Router: Admin / Benutzerverwaltung / Systemstatus
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from web.routers.deps import redirect,\
     TEMPLATES, base_ctx, get_konfig, get_db

router = APIRouter(prefix="/admin", tags=["Admin"])

_start_zeit = time.time()


def _groesse_kb(pfad: Path) -> float:
    try:
        return round(pfad.stat().st_size / 1024, 1)
    except Exception:
        return 0.0


def _groesse_mb(pfad: Path) -> float:
    try:
        return round(pfad.stat().st_size / 1024 / 1024, 2)
    except Exception:
        return 0.0


def _uptime_str() -> str:
    sek = int(time.time() - _start_zeit)
    h, rest = divmod(sek, 3600)
    m, s = divmod(rest, 60)
    if h > 0:
        return f"{h}h {m}min"
    return f"{m}min {s}s"


def _letzte_log_fehler(log_pfad: Path, n: int = 5) -> list[str]:
    """Liest die letzten n ERROR-Zeilen aus dem Log."""
    fehler = []
    try:
        lines = log_pfad.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            if "ERROR" in line or "CRITICAL" in line:
                fehler.append(line.strip())
                if len(fehler) >= n:
                    break
    except Exception:
        pass
    return fehler


@router.get("/", response_class=HTMLResponse)
async def admin_uebersicht(request: Request):
    konfig = get_konfig(request)
    data_dir = getattr(request.app.state, "data_dir", Path("/share/pflegra"))

    # DB-Info
    db_pfad = data_dir / "pflegra.db"
    db_groesse = _groesse_kb(db_pfad)

    # Backup-Info
    backup_ordner = data_dir / "backups"
    backups = sorted(backup_ordner.glob("*.db"), reverse=True) if backup_ordner.exists() else []
    backup_anzahl = len(backups)
    letztes_backup = backups[0].name if backups else None
    backup_gesamt_kb = round(sum(b.stat().st_size for b in backups) / 1024, 1)

    # Log-Info
    log_pfad = data_dir / "logs" / "pflegra.log"
    log_groesse = _groesse_kb(log_pfad)
    letzte_fehler = _letzte_log_fehler(log_pfad)

    # Archiv-Info
    archiv_ordner = data_dir / "Archiv"
    archiv_groesse = 0.0
    archiv_dateien = 0
    if archiv_ordner.exists():
        for f in archiv_ordner.rglob("*"):
            if f.is_file():
                archiv_groesse += f.stat().st_size
                archiv_dateien += 1
    archiv_groesse_mb = round(archiv_groesse / 1024 / 1024, 2)

    # DB-Statistik
    db = request.app.state.db
    statistik = db.statistik()

    return TEMPLATES.TemplateResponse(request, "admin/uebersicht.html", {
        **base_ctx(request),
        "konfig": konfig,
        "uptime": _uptime_str(),
        "db_groesse_kb": db_groesse,
        "backup_anzahl": backup_anzahl,
        "letztes_backup": letztes_backup,
        "backup_gesamt_kb": backup_gesamt_kb,
        "log_groesse_kb": log_groesse,
        "letzte_fehler": letzte_fehler,
        "archiv_dateien": archiv_dateien,
        "archiv_groesse_mb": archiv_groesse_mb,
        "statistik": statistik,
        "jetzt": datetime.now().strftime("%d.%m.%Y %H:%M"),
    })


@router.get("/log", response_class=HTMLResponse)
async def admin_log(request: Request, zeilen: int = 100):
    data_dir = getattr(request.app.state, "data_dir", Path("/share/pflegra"))
    log_pfad = data_dir / "logs" / "pflegra.log"
    log_inhalt = []
    try:
        lines = log_pfad.read_text(encoding="utf-8", errors="replace").splitlines()
        log_inhalt = lines[-zeilen:]
    except Exception:
        pass
    return TEMPLATES.TemplateResponse(request, "admin/log.html", {
        **base_ctx(request),
        "log_inhalt": log_inhalt,
        "zeilen": zeilen,
    })


@router.post("/vacuum")
async def admin_vacuum(request: Request):
    """DB komprimieren (VACUUM)."""
    db = get_db(request)
    db._schema.vacuum()
    return redirect(request, "/admin/?ok=vacuum", 303)


@router.get("/integrity")
async def admin_integrity(request: Request):
    """DB-Integritätscheck."""
    from fastapi.responses import JSONResponse
    db = get_db(request)
    ok = db._schema.integrity_check()
    return JSONResponse({"integrity": "ok" if ok else "error", "ok": ok})


# ── User-Verwaltung ───────────────────────────────────────────────────────────

from models import User as UserModel
from web.auth import hash_passwort, admin_erforderlich

@router.get("/users", response_class=HTMLResponse)
async def user_liste(request: Request, ok: str = "", fehler: str = ""):
    weiter = admin_erforderlich(request)
    if weiter: return weiter
    db = get_db(request)
    return TEMPLATES.TemplateResponse(request, "admin/users.html", {
        **base_ctx(request),
        "users":  db.user_alle(),
        "ok":     ok,
        "fehler": fehler,
    })


@router.post("/users/neu")
async def user_neu(
    request:   Request,
    username:  str = Form(...),
    passwort:  str = Form(...),
    rolle:     str = Form("user"),
):
    weiter = admin_erforderlich(request)
    if weiter: return weiter
    db = get_db(request)
    if db.user_laden_by_username(username.strip()):
        return redirect(request, "/admin/users?fehler=Benutzername+bereits+vergeben", 303)
    if len(passwort) < 8:
        return redirect(request, "/admin/users?fehler=Passwort+zu+kurz+(min.+8+Zeichen, 303)", status_code=303)
    u = UserModel(
        username=username.strip(),
        passwort=hash_passwort(passwort),
        rolle=rolle if rolle in ("admin", "user") else "user",
        aktiv=True,
    )
    db.user_speichern(u)
    return redirect(request, f"/admin/users?ok=User+{username}+angelegt", 303)


@router.post("/users/{user_id}/passwort")
async def user_passwort_reset(
    request:  Request,
    user_id:  int,
    passwort: str = Form(...),
):
    weiter = admin_erforderlich(request)
    if weiter: return weiter
    db = get_db(request)
    u = db.user_laden(user_id)
    if not u:
        return redirect(request, "/admin/users?fehler=User+nicht+gefunden", 303)
    if len(passwort) < 8:
        return redirect(request, "/admin/users?fehler=Passwort+zu+kurz", 303)
    u.passwort = hash_passwort(passwort)
    db.user_speichern(u)
    return redirect(request, f"/admin/users?ok=Passwort+für+{u.username}+geändert", 303)


@router.post("/users/{user_id}/toggle")
async def user_toggle(request: Request, user_id: int):
    weiter = admin_erforderlich(request)
    if weiter: return weiter
    db = get_db(request)
    u = db.user_laden(user_id)
    if not u:
        return redirect(request, "/admin/users?fehler=User+nicht+gefunden", 303)
    # Letzten Admin nicht deaktivieren
    from web.auth import get_aktueller_user_id
    if u.rolle == "admin" and u.id == get_aktueller_user_id(request):
        return redirect(request, "/admin/users?fehler=Eigenen+Account+nicht+deaktivieren", 303)
    u.aktiv = not u.aktiv
    db.user_speichern(u)
    status = "aktiviert" if u.aktiv else "deaktiviert"
    return redirect(request, f"/admin/users?ok={u.username}+{status}", 303)


@router.post("/users/{user_id}/loeschen")
async def user_loeschen(request: Request, user_id: int):
    weiter = admin_erforderlich(request)
    if weiter: return weiter
    db = get_db(request)
    from web.auth import get_aktueller_user_id
    if user_id == get_aktueller_user_id(request):
        return redirect(request, "/admin/users?fehler=Eigenen+Account+nicht+löschen", 303)
    u = db.user_laden(user_id)
    db.user_loeschen(user_id)
    return redirect(request, f"/admin/users?ok=User+{u.username if u else user_id}+gelöscht", 303)
