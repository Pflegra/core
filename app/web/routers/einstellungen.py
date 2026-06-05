"""
Router: Einstellungen lesen und speichern
Globale Einstellungen (config.json) + benutzerspezifische (user_settings DB).
"""
from __future__ import annotations

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from web.routers.deps import redirect,\
     TEMPLATES, base_ctx, get_konfig, get_db, get_user_settings

router = APIRouter(prefix="/einstellungen", tags=["Einstellungen"])


@router.get("/", response_class=HTMLResponse)
async def einstellungen_seite(request: Request, ok: str = ""):
    konfig   = get_konfig(request)
    settings = get_user_settings(request)
    return TEMPLATES.TemplateResponse(request, "einstellungen/formular.html", {
        **base_ctx(request),
        "konfig":   konfig,
        "settings": settings,
        "ok":       ok,
    })


@router.post("/speichern")
async def einstellungen_speichern(
    request:              Request,
    # Globale Einstellungen (nur Admin)
    pflegedienst_name:    str   = Form(""),
    pflegedienst_adresse: str   = Form(""),
    budget_basis:         float = Form(3539.0),
    archiv_basis:         str   = Form("Archiv"),
    datenbank_pfad:       str   = Form("pflegra.db"),
    # Benutzerspezifische Einstellungen
    absender_name:        str   = Form(""),
    absender_adresse:     str   = Form(""),
    absender_mail:        str   = Form(""),
    absender_geburtsdatum: str  = Form(""),
    stundensatz:          float = Form(20.0),
    # Passwort
    neues_passwort:       str   = Form(""),
):
    from web.auth import get_aktueller_user, hash_passwort
    from models import UserSettings

    user   = get_aktueller_user(request)
    konfig = get_konfig(request)
    db     = get_db(request)

    # Globale Einstellungen nur für Admin
    if user and user.ist_admin:
        konfig.pflegedienst_name    = pflegedienst_name
        konfig.pflegedienst_adresse = pflegedienst_adresse
        konfig.budget_basis         = budget_basis
        konfig.archiv_basis         = archiv_basis
        konfig.datenbank_pfad       = datenbank_pfad
        konfig_pfad = getattr(request.app.state, "konfig_pfad", None)
        konfig.speichere(konfig_pfad)
        try:
            request.app.state.budget_service._konfig = konfig
            request.app.state.export_service._konfig = konfig
            request.app.state.konfig = konfig
        except Exception:
            pass

    # Passwort ändern
    if neues_passwort and user:
        u = db.user_laden(user.id)
        if u:
            u.passwort = hash_passwort(neues_passwort)
            db.user_speichern(u)

    # Benutzerspezifische Einstellungen für alle User
    if user:
        s = UserSettings(
            user_id=user.id,
            absender_name=absender_name,
            absender_adresse=absender_adresse,
            absender_mail=absender_mail,
            absender_geburtsdatum=absender_geburtsdatum,
            stundensatz=stundensatz,
        )
        db.user_settings_speichern(s)

    return redirect(request, "/einstellungen/?ok=1", 303)
