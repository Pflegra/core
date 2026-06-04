"""
Router: Leistungsfinder
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from web.routers.deps import TEMPLATES, base_ctx
from leistungsfinder import berechne_leistungen

router = APIRouter(prefix="/leistungsfinder", tags=["Leistungsfinder"])


@router.get("/", response_class=HTMLResponse)
async def leistungsfinder_seite(request: Request):
    return TEMPLATES.TemplateResponse(request, "leistungsfinder/index.html", {
        **base_ctx(request),
    })


@router.get("/berechnen", response_class=JSONResponse)
async def leistungsfinder_berechnen(
    request: Request,
    pflegegrad: int = 0,
    setting: str = "haeuslich",
    art: str = "pflegegeld",
    jahr: int = 0,
):
    ergebnis = berechne_leistungen(pflegegrad, setting, art, jahr)
    return {
        "pflegegrad":    ergebnis.pflegegrad,
        "setting":       ergebnis.pflegesetting,
        "art":           ergebnis.leistungsart,
        "zusammenfassung": ergebnis.zusammenfassung,
        "summe_monatlich": ergebnis.summe_monatlich,
        "summe_jaehrlich": ergebnis.summe_jaehrlich,
        "monatlich": [_posten(p) for p in ergebnis.monatlich],
        "jaehrlich":  [_posten(p) for p in ergebnis.jaehrlich],
        "einmalig":   [_posten(p) for p in ergebnis.einmalig],
        "kombinations_hinweise": ergebnis.kombinations_hinweise,
    }


def _posten(p) -> dict:
    return {
        "titel":     p.titel,
        "betrag":    p.betrag,
        "einheit":   p.einheit,
        "paragraf":  p.paragraf,
        "info":      p.info,
        "kategorie": p.kategorie,
        "hinweis":   p.hinweis,
    }
