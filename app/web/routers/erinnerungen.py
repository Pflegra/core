"""
Router: Erinnerungen
Admin: SMTP + Push + Vorlaufzeiten konfigurieren
User:  E-Mail / Push aktivieren, SMTP testen
"""
from __future__ import annotations

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse

from web.routers.deps import TEMPLATES, base_ctx, get_db, get_owner_id, redirect

router = APIRouter(prefix="/erinnerungen", tags=["Erinnerungen"])


def _cfg(request: Request):
    from services.erinnerungen_service import ErinnerungenConfig
    return ErinnerungenConfig.aus_db(get_db(request))


@router.get("/", response_class=HTMLResponse)
async def erinnerungen_einstellungen(request: Request, ok: str = "", fehler: str = ""):
    from web.auth import login_erforderlich, get_aktueller_user
    guard = login_erforderlich(request)
    if guard:
        return guard
    user = get_aktueller_user(request)
    db = get_db(request)
    settings = db.user_settings_laden(user.id)
    cfg = _cfg(request)
    return TEMPLATES.TemplateResponse(request, "erinnerungen/einstellungen.html", {
        **base_ctx(request),
        "cfg": cfg,
        "settings": settings,
        "ist_admin": user.ist_admin,
        "ok": ok,
        "fehler": fehler,
    })


@router.post("/speichern")
async def erinnerungen_speichern(
    request: Request,
    # User-Einstellungen
    benachrichtigung_email: int = Form(0),
    benachrichtigung_push:  int = Form(0),
    # Admin-Einstellungen
    vorlauf_pflegeberatung:    int  = Form(14),
    vorlauf_entlastungsbetrag: int  = Form(30),
    vorlauf_fristen:           int  = Form(14),
    erinnerung_stunde:         int  = Form(8),
    smtp_host:     str  = Form(""),
    smtp_port:     int  = Form(587),
    smtp_user:     str  = Form(""),
    smtp_passwort: str  = Form(""),
    smtp_absender: str  = Form(""),
    smtp_tls:      int  = Form(1),
    push_aktiv:    int  = Form(0),
    push_vapid_public:  str = Form(""),
    push_vapid_private: str = Form(""),
):
    from web.auth import get_aktueller_user
    from db.settings import UserSettings
    user = get_aktueller_user(request)
    db = get_db(request)

    # User-Einstellungen speichern
    s = db.user_settings_laden(user.id)
    s.benachrichtigung_email = benachrichtigung_email
    s.benachrichtigung_push  = benachrichtigung_push
    db.user_settings_speichern(s)

    # Admin-Einstellungen speichern
    if user.ist_admin:
        from services.erinnerungen_service import ErinnerungenConfig
        cfg = ErinnerungenConfig(
            vorlauf_pflegeberatung=vorlauf_pflegeberatung,
            vorlauf_entlastungsbetrag=vorlauf_entlastungsbetrag,
            vorlauf_fristen=vorlauf_fristen,
            erinnerung_stunde=erinnerung_stunde,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_passwort=smtp_passwort or _cfg(request).smtp_passwort,  # leer = nicht überschreiben
            smtp_absender=smtp_absender,
            smtp_tls=bool(smtp_tls),
            push_aktiv=bool(push_aktiv),
            push_vapid_public=push_vapid_public,
            push_vapid_private=push_vapid_private or _cfg(request).push_vapid_private,
        )
        cfg.speichern(db)

    return redirect(request, "/erinnerungen/?ok=1", 303)


@router.post("/smtp-test")
async def smtp_test(request: Request):
    """Sendet eine Test-E-Mail an den aktuellen Nutzer."""
    from web.auth import get_aktueller_user
    from services.erinnerungen_service import Erinnerung, versende_email
    from datetime import date

    user = get_aktueller_user(request)
    db = get_db(request)
    settings = db.user_settings_laden(user.id)
    cfg = _cfg(request)

    if not settings.absender_mail:
        return JSONResponse({"ok": False, "fehler": "Keine E-Mail-Adresse in den Einstellungen hinterlegt."})

    test_erinnerung = Erinnerung(
        typ="test",
        person="Max Mustermann",
        titel="Test-Erinnerung von Pflegra",
        datum=date.today(),
        tage=0,
    )
    ok = versende_email(cfg, settings.absender_mail, settings.absender_name, [test_erinnerung])
    if ok:
        return JSONResponse({"ok": True, "nachricht": f"Test-E-Mail an {settings.absender_mail} versendet."})
    else:
        return JSONResponse({"ok": False, "fehler": "Versand fehlgeschlagen. SMTP-Einstellungen prüfen."})


@router.post("/push-subscribe")
async def push_subscribe(request: Request):
    """Speichert eine Web-Push-Subscription."""
    from web.auth import get_aktueller_user
    from web.routers.deps import get_owner_id
    import json

    user = get_aktueller_user(request)
    owner_id = get_owner_id(request)
    db = get_db(request)

    try:
        body = await request.json()
        endpoint = body.get("endpoint", "")
        keys = body.get("keys", {})
        p256dh = keys.get("p256dh", "")
        auth = keys.get("auth", "")

        if not endpoint:
            return JSONResponse({"ok": False}, status_code=400)

        with db._schema.connect() as conn:
            conn.execute("""
                INSERT INTO push_subscriptions (owner_id, endpoint, p256dh, auth)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(endpoint) DO UPDATE SET
                    p256dh=excluded.p256dh,
                    auth=excluded.auth
                WHERE push_subscriptions.owner_id=excluded.owner_id
            """, (owner_id, endpoint, p256dh, auth))

        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "fehler": str(e)}, status_code=500)


@router.post("/push-unsubscribe")
async def push_unsubscribe(request: Request):
    """Entfernt eine Web-Push-Subscription."""
    db = get_db(request)
    owner_id = get_owner_id(request)
    try:
        body = await request.json()
        endpoint = body.get("endpoint", "")
        with db._schema.connect() as conn:
            conn.execute(
                "DELETE FROM push_subscriptions WHERE endpoint=? AND owner_id=?",
                (endpoint, owner_id),
            )
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "fehler": str(e)}, status_code=500)


@router.get("/verlauf", response_class=HTMLResponse)
async def erinnerungen_verlauf(request: Request):
    from web.auth import login_erforderlich
    from web.routers.deps import get_owner_id
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    db = get_db(request)

    try:
        with db._schema.connect() as conn:
            rows = conn.execute("""
                SELECT zeitpunkt, kanal, person, typ, titel, datum, erfolg
                FROM erinnerungen_log
                WHERE owner_id=?
                ORDER BY zeitpunkt DESC
                LIMIT 100
            """, (owner_id,)).fetchall()
        verlauf = [dict(r) for r in rows]
    except Exception:
        verlauf = []

    return TEMPLATES.TemplateResponse(request, "erinnerungen/verlauf.html", {
        **base_ctx(request),
        "verlauf": verlauf,
    })
