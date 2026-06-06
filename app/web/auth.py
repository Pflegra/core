"""
Pflegra – Authentifizierung und Autorisierung
Vollständige Version mit allen benötigten Exports für Ingress-Kompatibilität.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import Request
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

# ── Secret Key ────────────────────────────────────────────────────────────────

def _load_or_generate_secret() -> str:
    data_dir = Path(os.environ.get("PFLEGRA_DATA", "/share/pflegra"))
    key_file = data_dir / ".secret_key"
    try:
        if key_file.exists():
            return key_file.read_text().strip()
        key = os.urandom(32).hex()
        key_file.write_text(key)
        key_file.chmod(0o600)
        return key
    except Exception:
        return os.urandom(32).hex()

SECRET_KEY        = _load_or_generate_secret()
SESSION_COOKIE    = "pflegra_session"
COOKIE_NAME       = SESSION_COOKIE          # Alias – wird von login.py importiert
SESSION_MAX_AGE   = 60 * 60 * 24 * 30      # 30 Tage
HTTPS_ENABLED     = os.environ.get("PFLEGRA_HTTPS", "0") == "1"
SERIALIZER        = URLSafeTimedSerializer(SECRET_KEY)

# ── Ingress Root Path ──────────────────────────────────────────────────────────

def _get_ingress_root() -> str:
    """Liest den Ingress-Pfad aus /tmp/ingress_entry (geschrieben von run.sh)."""
    try:
        return open("/tmp/ingress_entry").read().strip()
    except Exception:
        return ""

def _get_root(request: Request) -> str:
    """Root-Path für Ingress-kompatible Redirects."""
    root = request.scope.get("root_path", "")
    if root:
        return root
    return _get_ingress_root()

# ── Session ───────────────────────────────────────────────────────────────────

def erstelle_session_token(user_id: int) -> str:
    return SERIALIZER.dumps({"user_id": user_id})

# Alias – wird von login.py importiert
erstelle_session_cookie = erstelle_session_token

def lese_session_token(token: str) -> Optional[int]:
    try:
        daten = SERIALIZER.loads(token, max_age=SESSION_MAX_AGE)
        return daten.get("user_id")
    except (BadSignature, SignatureExpired):
        return None

# ── User aus Request ───────────────────────────────────────────────────────────

def get_aktueller_user_id(request: Request) -> Optional[int]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return lese_session_token(token)

def get_aktueller_user(request: Request):
    user_id = get_aktueller_user_id(request)
    if user_id is None:
        return None
    try:
        return request.app.state.db.user_laden(user_id)
    except Exception:
        return None

# ── Auth Guards ───────────────────────────────────────────────────────────────

def login_erforderlich(request: Request) -> Optional[RedirectResponse]:
    """Gibt RedirectResponse zurück wenn nicht eingeloggt, sonst None."""
    if get_aktueller_user_id(request) is None:
        root = _get_root(request)
        return RedirectResponse(root + "/login", status_code=303)
    return None

def admin_erforderlich(request: Request) -> Optional[RedirectResponse]:
    """Gibt RedirectResponse zurück wenn nicht Admin."""
    user = get_aktueller_user(request)
    root = _get_root(request)
    if user is None:
        return RedirectResponse(root + "/login", status_code=303)
    if not user.ist_admin:
        return RedirectResponse(root + "/?fehler=kein_zugriff", status_code=303)
    return None

# ── Passwort ──────────────────────────────────────────────────────────────────

def hash_passwort(passwort: str) -> str:
    import bcrypt
    return bcrypt.hashpw(passwort.encode(), bcrypt.gensalt()).decode()

def passwort_korrekt(passwort: str, gespeicherter_hash: str) -> bool:
    import bcrypt
    try:
        return bcrypt.checkpw(passwort.encode(), gespeicherter_hash.encode())
    except Exception:
        return False

# Alias – wird von login.py importiert
pruefe_passwort = passwort_korrekt

# ── Impersonation ─────────────────────────────────────────────────────────────

IMPERSONATION_COOKIE = "pflegra_impersonation"

def starte_impersonation(response, target_user_id: int) -> None:
    """Setzt den Impersonation-Cookie (target_user_id)."""
    token = SERIALIZER.dumps({"impersonate": target_user_id})
    response.set_cookie(
        IMPERSONATION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 8,  # 8 Stunden max
    )

def beende_impersonation(response) -> None:
    """Löscht den Impersonation-Cookie."""
    response.delete_cookie(IMPERSONATION_COOKIE)

def get_impersonation_target(request: Request) -> Optional[int]:
    """Gibt die user_id zurück für die der Admin gerade handelt, oder None."""
    token = request.cookies.get(IMPERSONATION_COOKIE)
    if not token:
        return None
    try:
        daten = SERIALIZER.loads(token, max_age=60 * 60 * 8)
        return daten.get("impersonate")
    except Exception:
        return None

def get_effective_user_id(request: Request) -> Optional[int]:
    """
    Gibt die effective user_id zurück:
    - Bei aktiver Impersonation: die Ziel-User-ID
    - Sonst: die eigene User-ID
    """
    impersonation = get_impersonation_target(request)
    if impersonation is not None:
        return impersonation
    return get_aktueller_user_id(request)

def get_effective_user(request: Request):
    """
    Gibt den effective User zurück (impersoniert oder eigener).
    """
    user_id = get_effective_user_id(request)
    if user_id is None:
        return None
    try:
        return request.app.state.db.user_laden(user_id)
    except Exception:
        return None

def ist_impersonation_aktiv(request: Request) -> bool:
    """True wenn Admin gerade als anderer User agiert."""
    return get_impersonation_target(request) is not None
