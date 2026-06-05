"""
Pflegra – CSRF-Schutz
Double-Submit-Cookie-Pattern via Request-Body.
"""
from __future__ import annotations

import hmac
import os
import logging
from fastapi import Request
from fastapi.responses import RedirectResponse

log = logging.getLogger(__name__)

CSRF_COOKIE = "pn_csrf"


def generiere_csrf_token() -> str:
    return os.urandom(24).hex()


def get_csrf_token(request: Request) -> str:
    return request.cookies.get(CSRF_COOKIE) or generiere_csrf_token()


async def pruefe_csrf_request(request: Request) -> bool:
    """Liest den Body und vergleicht csrf_token mit Cookie."""
    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    if not cookie_token:
        return False
    try:
        form = await request.form()
        form_token = form.get("csrf_token", "")
        return hmac.compare_digest(str(cookie_token), str(form_token))
    except Exception:
        return False


def csrf_fehler(request: Request) -> RedirectResponse:
    log.warning("CSRF-Fehler bei %s %s", request.method, request.url.path)
    return RedirectResponse("/?fehler=csrf", status_code=303)
