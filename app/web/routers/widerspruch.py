"""
Router: Widerspruchshilfe
"""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, Response, RedirectResponse

from web.routers.deps import TEMPLATES, base_ctx, get_db, get_owner_id, get_user_settings

router = APIRouter(prefix="/widerspruch", tags=["Widerspruch"])

MODUL_NAMEN = {
    1: "Mobilität",
    2: "Kognitive und kommunikative Fähigkeiten",
    3: "Verhaltensweisen und psychische Problemlagen",
    4: "Selbstversorgung",
    5: "Umgang mit krankheits-/therapiebedingten Anforderungen",
    6: "Gestaltung des Alltagslebens und sozialer Kontakte",
}

HAEUFIGE_KRITIKPUNKTE = {
    1: "Die Mobilität wurde zu positiv bewertet. Am Begutachtungstag war die Person "
       "ungewöhnlich fit — dies entspricht nicht dem alltäglichen Bild.",
    2: "Kognitive Einschränkungen wurden nicht ausreichend erfasst. "
       "Die Begutachtung fand zu einer günstigen Tageszeit statt.",
    3: "Verhaltensauffälligkeiten wurden unterschätzt. "
       "Nächtliche Unruhe und Abwehrverhalten bei der Pflege wurden nicht korrekt bewertet.",
    4: "Der Hilfebedarf bei der Selbstversorgung wurde zu niedrig eingestuft. "
       "Waschen, Anziehen und Toilettengänge erfordern täglich vollständige Unterstützung.",
    5: "Der Aufwand für Medikamentengabe und medizinische Versorgung wurde unterschätzt.",
    6: "Die Einschränkungen in der Alltagsgestaltung und sozialen Teilhabe "
       "wurden nicht vollständig berücksichtigt.",
}


@router.get("/", response_class=HTMLResponse)
async def widerspruch_start(request: Request):
    db = get_db(request)
    owner_id = get_owner_id(request)
    personen = db.personen(owner_id)
    settings = get_user_settings(request)
    return TEMPLATES.TemplateResponse(request, "widerspruch/index.html", {
        **base_ctx(request),
        "personen":          personen,
        "modul_namen":       MODUL_NAMEN,
        "haeufige_kritik":   HAEUFIGE_KRITIKPUNKTE,
        "heute":             date.today().strftime("%d.%m.%Y"),
        "heute_iso":         date.today().isoformat(),
        "settings":          settings,
    })


@router.post("/pdf", response_class=Response)
async def widerspruch_pdf(request: Request):
    from pdf_export import erstelle_widerspruch_pdf

    form = await request.form()
    db = get_db(request)
    owner_id = get_owner_id(request)
    settings = get_user_settings(request)

    person = str(form.get("person", ""))
    versicherter = db.versicherter_laden(person, get_owner_id(request)) if person else None

    # Modul-Kritik sammeln
    module_kritik = []
    for mid in range(1, 7):
        kritik = str(form.get(f"modul_{mid}_kritik", "")).strip()
        if kritik:
            module_kritik.append({
                "modul_id": mid,
                "modul_name": MODUL_NAMEN[mid],
                "kritik": kritik,
            })

    absender_adresse = ""
    if settings and hasattr(settings, "absender_name"):
        absender_adresse = (
            f"{settings.absender_name}\n{settings.absender_adresse}"
            if settings.absender_adresse else settings.absender_name
        )

    # Bescheid-Datum formatieren
    bescheid_datum_raw = str(form.get("bescheid_datum", ""))
    try:
        from datetime import datetime
        bd = datetime.strptime(bescheid_datum_raw, "%Y-%m-%d")
        bescheid_datum = bd.strftime("%d.%m.%Y")
    except Exception:
        bescheid_datum = bescheid_datum_raw

    pdf_bytes = erstelle_widerspruch_pdf(
        absender_name=settings.absender_name if settings and hasattr(settings, "absender_name") else "",
        absender_adresse=absender_adresse,
        versicherter=versicherter,
        bescheid_datum=bescheid_datum,
        bescheid_az=str(form.get("bescheid_az", "")),
        aktueller_pg=int(form.get("aktueller_pg", 0) or 0),
        beantragter_pg=int(form.get("beantragter_pg", 0) or 0),
        widerspruch_typ=str(form.get("widerspruch_typ", "fristsichernd")),
        begruendung=str(form.get("begruendung", "")),
        module_kritik=module_kritik,
        datum_heute=date.today().strftime("%d.%m.%Y"),
    )

    dateiname = f"widerspruch_pflegegrad_{date.today().isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{dateiname}"'},
    )
