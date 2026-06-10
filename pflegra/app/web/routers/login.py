"""
Router: Login / Logout (Multiuser)
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict

log = logging.getLogger(__name__)
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from web.auth import (
    COOKIE_NAME, SESSION_MAX_AGE, HTTPS_ENABLED,
    erstelle_session_cookie, pruefe_passwort,
    get_aktueller_user_id, hash_passwort,
)
from db.audit import AuditRepo, AuditEvent
from web.routers.deps import redirect,\
     TEMPLATES, base_ctx
from models import User

router = APIRouter(tags=["Auth"])

_fehlversuche: dict = defaultdict(list)
MAX_VERSUCHE    = 5
SPERRE_SEKUNDEN = 300


def _ip_gesperrt(ip: str) -> bool:
    jetzt = time.time()
    versuche = [t for t in _fehlversuche[ip] if jetzt - t < SPERRE_SEKUNDEN]
    _fehlversuche[ip] = versuche
    return len(versuche) >= MAX_VERSUCHE


def _fehlversuch_registrieren(ip: str):
    _fehlversuche[ip].append(time.time())


@router.get("/login", response_class=HTMLResponse)
async def login_seite(request: Request, next: str = "/", fehler: str = ""):
    if get_aktueller_user_id(request):
        return redirect(request, "/", 303)

    # Erststart: kein User in DB → Setup-Seite
    db = request.app.state.db
    if db.user_anzahl() == 0:
        return redirect(request, "/setup", 303)

    return TEMPLATES.TemplateResponse(request, "login.html", {
        **base_ctx(request),
        "next":   next,
        "fehler": fehler,
        "multiuser": True,
    })


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    passwort: str = Form(...),
    next:     str = Form("/"),
):
    ip = request.client.host if request.client else "unknown"

    if _ip_gesperrt(ip):
        return TEMPLATES.TemplateResponse(request, "login.html", {
            **base_ctx(request),
            "next": next, "fehler": "gesperrt", "multiuser": True,
        }, status_code=429)

    db = request.app.state.db
    user = db.user_laden_by_username(username.strip())

    if not user or not pruefe_passwort(passwort, user.passwort):
        _fehlversuch_registrieren(ip)
        # Audit: Login fehlgeschlagen
        try:
            if user:
                audit = AuditRepo(request.app.state.db._schema)
                audit.loggen(AuditEvent.LOGIN_FEHLGESCHLAGEN, user.id,
                             details=f"Fehlgeschlagener Login für '{username.strip()}'",
                             ip_adresse=ip)
        except Exception:
            pass
        return redirect(request, f"/login?next={next}&fehler=1", 303)

    token = erstelle_session_cookie(user.id)
    # Audit: Login erfolgreich
    try:
        audit = AuditRepo(request.app.state.db._schema)
        audit.loggen(AuditEvent.LOGIN_OK, user.id,
                     details=f"Login erfolgreich",
                     ip_adresse=ip)
    except Exception:
        pass
    # Ingress-Prefix für korrekte Weiterleitung
    root = request.scope.get("root_path", "")
    if not root:
        try:
            root = open("/tmp/ingress_entry").read().strip()
        except Exception:
            root = ""
    cookie_path = root if root else "/"
    ziel_raw = next if (next.startswith("/") and not next.startswith("//")) else "/"
    ziel = root + ziel_raw
    from fastapi.responses import RedirectResponse as _RR
    response = _RR(url=ziel, status_code=303)
    response.set_cookie(
        COOKIE_NAME, token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=HTTPS_ENABLED and (
            request.url.scheme == "https" or
            request.headers.get("x-forwarded-proto") == "https"
        ),
        path=cookie_path,
    )
    return response


@router.get("/logout")
async def logout(request: Request):
    # Demo-User: Daten sofort zurücksetzen
    from web.auth import get_aktueller_user
    user = get_aktueller_user(request)
    if user and user.username == "demo":
        try:
            from demo_reset import demo_reset
            demo_reset(request.app.state.db)
        except Exception:
            pass
    root = request.scope.get("root_path", "")
    if not root:
        try:
            root = open("/tmp/ingress_entry").read().strip()
        except Exception:
            root = ""
    cookie_path = root if root else "/"
    from fastapi.responses import RedirectResponse as _RR
    response = _RR(url=root + "/login", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value="",
        max_age=0,
        expires=0,
        path=cookie_path,
        httponly=True,
        samesite="lax",
    )
    return response


# ── Erststart Setup ───────────────────────────────────────────────────────────

@router.get("/setup", response_class=HTMLResponse)
async def setup_seite(request: Request):
    db = request.app.state.db
    if db.user_anzahl() > 0:
        return redirect(request, "/login", 303)
    return TEMPLATES.TemplateResponse(request, "setup.html", {
        **base_ctx(request),
    })


@router.post("/setup")
async def setup_submit(
    request:  Request,
    username: str = Form(...),
    passwort: str = Form(...),
    passwort2: str = Form(...),
):
    db = request.app.state.db
    if db.user_anzahl() > 0:
        return redirect(request, "/login", 303)

    if passwort != passwort2:
        return TEMPLATES.TemplateResponse(request, "setup.html", {
            **base_ctx(request),
            "fehler": "Passwörter stimmen nicht überein.",
        })
    if len(passwort) < 8:
        return TEMPLATES.TemplateResponse(request, "setup.html", {
            **base_ctx(request),
            "fehler": "Passwort muss mindestens 8 Zeichen haben.",
        })

    admin = User(
        username=username.strip(),
        passwort=hash_passwort(passwort),
        rolle="admin",
        aktiv=True,
    )
    db.user_speichern(admin)
    return redirect(request, "/login?ok=setup", 303)
