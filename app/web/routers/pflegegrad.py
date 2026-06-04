"""
Router: Pflegegradrechner (NBA)
"""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from web.routers.deps import TEMPLATES, base_ctx, get_user_settings, get_owner_id
from pflegegrad_rechner import ALLE_MODULE, berechne_pflegegrad

router = APIRouter(prefix="/pflegegrad", tags=["Pflegegrad"])


def _parse_antworten(form) -> dict:
    antworten: dict[str, int] = {}
    for key, val in form.items():
        if key.startswith(("1.", "2.", "3.", "4.", "5.", "6.")):
            try:
                antworten[key] = int(val)
            except (ValueError, TypeError):
                antworten[key] = 0
    return antworten


@router.get("/", response_class=HTMLResponse)
async def pflegegrad_rechner(request: Request):
    return TEMPLATES.TemplateResponse(request, "pflegegrad/rechner.html", {
        **base_ctx(request),
        "module": ALLE_MODULE,
    })


@router.post("/berechnen", response_class=JSONResponse)
async def pflegegrad_berechnen(request: Request):
    form = await request.form()
    ergebnis = berechne_pflegegrad(_parse_antworten(form))
    return {
        "gesamtpunkte": ergebnis.gesamtpunkte,
        "pflegegrad": ergebnis.pflegegrad,
        "pflegegrad_bezeichnung": ergebnis.pflegegrad_bezeichnung,
        "begruendung": ergebnis.begruendung,
        "hinweise": ergebnis.hinweise,
        "haupttreiber": ergebnis.haupttreiber,
        "dokumentations_tipps": ergebnis.dokumentations_tipps,
        "module": [
            {
                "modul_id": m.modul_id,
                "bezeichnung": m.bezeichnung,
                "rohpunkte": m.rohpunkte,
                "gewichtete_punkte": m.gewichtete_punkte,
                "schweregrad": m.schweregrad,
            }
            for m in ergebnis.modul_ergebnisse
        ],
    }


@router.get("/leistungen/{pflegegrad}", response_class=JSONResponse)
async def pflegegrad_leistungen(pflegegrad: int, jahr: int = 0):
    from pflege_rules import leistungen_fuer_pflegegrad
    return leistungen_fuer_pflegegrad(pflegegrad, jahr)


@router.post("/pdf", response_class=Response)
async def pflegegrad_pdf(request: Request):
    from pdf_export import exportiere_pflegegrad_pdf

    form = await request.form()
    ergebnis = berechne_pflegegrad(_parse_antworten(form))

    settings = get_user_settings(request)
    versicherter_name = str(form.get("versicherter_name", "") or "")
    if not versicherter_name and hasattr(settings, "standard_person"):
        versicherter_name = settings.standard_person or ""
    absender_name = settings.absender_name if hasattr(settings, "absender_name") else ""

    pdf_bytes = exportiere_pflegegrad_pdf(
        ergebnis=ergebnis,
        versicherter_name=versicherter_name,
        absender_name=absender_name,
        datum=date.today().strftime("%d.%m.%Y"),
    )

    dateiname = f"pflegegrad_einschaetzung_{date.today().isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'},
    )


@router.post("/verlauf/speichern", response_class=JSONResponse)
async def verlauf_speichern(request: Request):
    import json as _json
    from datetime import date
    from db.pflegegrad_verlauf import PflegegradEintrag

    form = await request.form()
    antworten = _parse_antworten(form)
    ergebnis = berechne_pflegegrad(antworten)

    db = request.app.state.db
    owner_id = get_owner_id(request)
    person = str(form.get("person", "")).strip()
    notiz = str(form.get("notiz", "")).strip()

    eintrag = PflegegradEintrag(
        id=None,
        owner_id=owner_id,
        person=person,
        datum=date.today().isoformat(),
        pflegegrad=ergebnis.pflegegrad,
        gesamtpunkte=ergebnis.gesamtpunkte,
        notiz=notiz,
        antworten_json=_json.dumps(antworten),
    )
    new_id = db.pg_verlauf_speichern(eintrag)
    return {"ok": True, "id": new_id, "pflegegrad": ergebnis.pflegegrad, "gesamtpunkte": ergebnis.gesamtpunkte}


@router.get("/verlauf", response_class=HTMLResponse)
async def verlauf_uebersicht(request: Request, person: str = ""):
    db = request.app.state.db
    owner_id = get_owner_id(request)
    eintraege = db.pg_verlauf_alle(owner_id, person)
    personen = db.pg_verlauf_personen(owner_id)
    return TEMPLATES.TemplateResponse(request, "pflegegrad/verlauf.html", {
        **base_ctx(request),
        "eintraege": eintraege,
        "personen": personen,
        "aktueller_person_filter": person,
    })


@router.post("/verlauf/loeschen/{eintrag_id}", response_class=JSONResponse)
async def verlauf_loeschen(request: Request, eintrag_id: int):
    db = request.app.state.db
    owner_id = get_owner_id(request)
    ok = db.pg_verlauf_loeschen(eintrag_id, owner_id)
    return {"ok": ok}
