"""
Router: Budgetbersicht
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from web.routers.deps import TEMPLATES, base_ctx, get_db, get_budget_service, get_owner_id
from calculations import MAX_TAGE_TAGEWEISE, BUDGET_JAHRESBETRAG
from pflege_rules import get_regelwerk

router = APIRouter(prefix="/budget", tags=["Budget"])


@router.get("/", response_class=HTMLResponse)
async def budget_uebersicht(request: Request, jahr: int = 0):
    db = get_db(request)
    service = get_budget_service(request)
    if not jahr:
        jahr = date.today().year

    jahre    = db.jahre(get_owner_id(request)) or [jahr]
    owner_id = get_owner_id(request)
    eintraege = db.alle(owner_id)
    berichte = service.alle_berichte(jahr, eintraege=eintraege)
    from i18n import get_lang, make_t
    _t = make_t(get_lang(request))
    warnungen_raw = service.warnung_fuer_alle(jahr, eintraege=eintraege)
    warnungen = []
    for w in warnungen_raw:
        typ = w["typ"]
        p   = w["person"]
        v   = w["werte"]
        if typ == "ausgeschoepft":
            warnungen.append(_t("budget.warn_ausgeschoepft", person=p,
                verbraucht=f"{v['verbraucht']:.2f}", budget=f"{v['budget']:.2f}"))
        elif typ == "prognose":
            warnungen.append(_t("budget.warn_prognose", person=p,
                differenz=f"{v['differenz']:.2f}"))
        elif typ == "prozent":
            warnungen.append(_t("budget.warn_prozent", person=p,
                prozent=f"{v['prozent']:.0f}"))
        elif typ == "tage_grenze":
            warnungen.append(_t("budget.warn_tage_grenze", person=p,
                tage=v['tage'], max=v['max']))
        elif typ == "tage_fast":
            warnungen.append(_t("budget.warn_tage_fast", person=p,
                tage=v['tage'], max=v['max'], rest=v['rest']))
    regeln   = get_regelwerk(jahr)

    heute = date.today()
    vorjahr_nutzbar = (heute.month <= 6 and heute.year == jahr)

    return TEMPLATES.TemplateResponse(request, "budget/uebersicht.html", {
        **base_ctx(request),
        "berichte":              berichte,
        "warnungen":             warnungen,
        "aktuelles_jahr":        jahr,
        "jahre":                 jahre,
        "max_tage_tageweise":    MAX_TAGE_TAGEWEISE,
        "budget_gesamt":         service.budget_gesamt,
        "entlastung_monatlich":  regeln.entlastungsbetrag_monatlich,
        "entlastung_jahresmax":  regeln.entlastungsbetrag_monatlich * 12,
        "vorjahr_nutzbar":       vorjahr_nutzbar,
        "vorjahr_jahr":          jahr - 1,
    })


@router.get("/person/{person}", response_class=HTMLResponse)
async def budget_person_detail(request: Request, person: str, jahr: int = 0):
    db = get_db(request)
    service = get_budget_service(request)
    if not jahr:
        jahr = date.today().year

    bericht = service.bericht_fuer_person(person, jahr)
    return TEMPLATES.TemplateResponse(request, "budget/person_detail.html", {
        **base_ctx(request),
        "bericht": bericht,
        "aktuelles_jahr": jahr,
        "max_tage_tageweise": MAX_TAGE_TAGEWEISE,
        "budget_gesamt": service.budget_gesamt,
    })
