"""
Gemeinsame FastAPI-Dependencies fr alle Routers.
Werden von web.app injiziert (App-State-Muster).
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from fastapi import Request
from fastapi.templating import Jinja2Templates

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


def _fmt_eur(value, dez=2) -> str:
    """Deutsches Währungsformat: 1.234,56 €"""
    try:
        v = float(value)
        formatted = f"{v:_.{dez}f}".replace("_", "X").replace(".", ",").replace("X", ".")
        return f"{formatted} €"
    except (ValueError, TypeError):
        return f"{value} €"


import json as _json

TEMPLATES.env.filters["eur"]    = lambda v: _fmt_eur(v, 2)
TEMPLATES.env.filters["eur0"]   = lambda v: _fmt_eur(v, 0)
TEMPLATES.env.filters["tojson"] = lambda v: _json.dumps(v, ensure_ascii=False)

# i18n
from i18n import get_lang, make_t, SUPPORTED_LANGS
TEMPLATES.env.globals["SUPPORTED_LANGS"] = SUPPORTED_LANGS


def get_db(request: Request):
    return request.app.state.db


def get_konfig(request: Request):
    return request.app.state.konfig


def get_budget_service(request: Request):
    return request.app.state.budget_service


def get_export_service(request: Request):
    return request.app.state.export_service


def get_import_service(request: Request):
    return request.app.state.import_service


def get_owner_id(request: Request) -> int:
    """
    Gibt die effective owner_id zurück.
    Bei aktiver Impersonation: ID des Ziel-Users (Admin handelt als User).
    Sonst: ID des eingeloggten Users.
    """
    from web.auth import get_effective_user_id
    uid = get_effective_user_id(request)
    if not uid:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Owner-Kontext fehlt")
    return int(uid)


def get_user_settings(request: Request):
    """Gibt die benutzerspezifischen Einstellungen zurück."""
    from web.auth import get_aktueller_user
    user = get_aktueller_user(request)
    if not user:
        return get_konfig(request)
    db = get_db(request)
    return db.user_settings_laden(user.id)


def base_ctx(request: Request) -> dict:
    """Basis-Kontext für alle Templates."""
    try:
        pflegedienst = request.app.state.konfig.pflegedienst_name
    except AttributeError:
        pflegedienst = ""
    from web.csrf import get_csrf_token
    from web.auth import get_aktueller_user, ist_impersonation_aktiv, get_effective_user
    user = get_aktueller_user(request)
    lang = get_lang(request)
    impersonation = ist_impersonation_aktiv(request)
    effective_user = get_effective_user(request) if impersonation else user
    return {
        "request":              request,
        "pflegedienst_name":    pflegedienst,
        "csrf_token":           get_csrf_token(request),
        "current_user":         user,
        "is_admin":             user.ist_admin if user else False,
        "lang":                 lang,
        "_":                    make_t(lang),
        "impersonation_aktiv":  impersonation,
        "effective_user":       effective_user,
    }


def audit_log(request: Request, aktion: str, details: str = "") -> None:
    """Schreibt einen Audit-Eintrag mit actor + effective_user aus dem Request."""
    from db.audit import AuditRepo
    from web.auth import get_aktueller_user_id, get_effective_user_id
    actor_id    = get_aktueller_user_id(request) or 0
    effective_id = get_effective_user_id(request) or actor_id
    ip = request.client.host if request.client else ""
    AuditRepo(get_db(request)._schema).loggen(
        aktion=aktion,
        actor_user_id=actor_id,
        effective_user_id=effective_id,
        details=details,
        ip_adresse=ip,
    )


def redirect(request: Request, path: str, status_code: int = 303):
    """RedirectResponse mit automatischem root_path Prefix für Ingress-Kompatibilität."""
    from fastapi.responses import RedirectResponse
    root = request.scope.get("root_path", "")
    if not root:
        try:
            root = open("/tmp/ingress_entry").read().strip()
        except Exception:
            root = ""
    return RedirectResponse(root + path, status_code=status_code)
