"""
Router: Versicherten-Stammdaten
"""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from models import Versicherter, Ersatzpflegekraft
from web.routers.deps import redirect,\
     TEMPLATES, base_ctx, get_db, get_owner_id
from web.validation import Validierungsfehler, validiere_versicherter

router = APIRouter(prefix="/versicherte", tags=["Versicherte"])

KRANKENKASSEN = [
    "", "AOK Baden-Württemberg", "AOK Bayern", "AOK Bremen/Bremerhaven",
    "AOK Hessen", "AOK NordWest", "AOK Nordost", "AOK Plus",
    "AOK Rheinland-Pfalz/Saarland", "AOK Rheinland/Hamburg",
    "AOK Sachsen-Anhalt", "Barmer", "DAK-Gesundheit", "IKK classic",
    "IKK gesund plus", "Knappschaft", "KKH Kaufmännische Krankenkasse",
    "Techniker Krankenkasse (TK)", "VIACTIV Krankenkasse",
]


def _fehler(msg: str, person: str = "") -> RedirectResponse:
    params = f"fehler={quote(msg)}"
    if person:
        params += f"&person={quote(person)}"
    return redirect(request, f"/versicherte/?{params}", 303)


@router.get("/neu", response_class=HTMLResponse)
async def versicherter_neu(request: Request):
    db = get_db(request)
    personen = db.personen(get_owner_id(request))
    return TEMPLATES.TemplateResponse(request, "versicherte/neu.html", {
        **base_ctx(request),
        "personen":      personen,
        "krankenkassen": KRANKENKASSEN,
        "pflegegrade":   list(range(6)),
    })


@router.get("/", response_class=HTMLResponse)
async def versicherte_liste(request: Request, person: str = "", ok: str = "", fehler: str = ""):
    db = get_db(request)
    personen = db.personen(get_owner_id(request))
    versicherter = db.versicherter_laden(person) if person else None
    ersatzliste  = db.ersatz_alle(person, get_owner_id(request)) if person else []
    return TEMPLATES.TemplateResponse(request, "versicherte/formular.html", {
        **base_ctx(request),
        "personen":        personen,
        "gewaehlte_person": person,
        "versicherter":    versicherter,
        "ersatzliste":     ersatzliste,
        "krankenkassen":   KRANKENKASSEN,
        "pflegegrade":     list(range(6)),
        "ersatz_arten":    ["Privatperson", "Pflegedienst", "Verwandter (bis 2. Grad)"],
        "ok":              ok,
        "fehler":          fehler,
    })


@router.post("/speichern")
async def versicherter_speichern(
    request: Request,
    person_name:          str = Form(...),
    adresse:              str = Form(""),
    versicherungsnr:      str = Form(""),
    krankenkasse:         str = Form(""),
    krankenkasse_adresse: str = Form(""),
    pflegegrad:           int = Form(0),
    geburtsdatum:         str = Form(""),
    mail:                 str = Form(""),
    notiz:                str = Form(""),
):
    try:
        felder = validiere_versicherter(
            person_name, adresse, versicherungsnr, krankenkasse,
            krankenkasse_adresse, pflegegrad, geburtsdatum, mail, notiz,
        )
        db = get_db(request)
        owner_id = get_owner_id(request)

        # Person automatisch anlegen falls nicht vorhanden
        db.person_anlegen(felder["person_name"], owner_id=owner_id)

        v = Versicherter(
            name=felder["person_name"],
            adresse=felder["adresse"],
            versicherungsnr=felder["versicherungsnr"],
            krankenkasse=felder["krankenkasse"],
            krankenkasse_adresse=felder["krankenkasse_adresse"],
            pflegegrad=felder["pflegegrad"],
            geburtsdatum=felder["geburtsdatum"],
            mail=felder["mail"],
            notiz=felder["notiz"],
            owner_id=owner_id,
        )
        db.versicherter_speichern(v)
    except (Validierungsfehler, ValueError) as exc:
        return _fehler(str(exc), person_name)
    return redirect(request, 
        f"/versicherte/?person={quote(felder['person_name'], safe='')}&ok=1",
        status_code=303,
    )


@router.post("/{person_name}/loeschen")
async def versicherter_loeschen(request: Request, person_name: str):
    db = get_db(request)
    owner_id = get_owner_id(request)
    # Versicherter löschen → CASCADE löscht Einträge automatisch
    db.versicherter_loeschen(person_name, owner_id)
    # Person auch löschen
    db.person_loeschen_mit_eintraegen(person_name, owner_id)
    return redirect(request, "/versicherte/?ok=1", 303)


# ── Ersatzpflegekräfte CRUD ───────────────────────────────────────────────────

@router.post("/ersatz/speichern")
async def ersatz_speichern(
    request:      Request,
    person:       str = Form(...),
    ersatz_id:    int = Form(0),
    name:         str = Form(...),
    geburtsdatum: str = Form(""),
    adresse:      str = Form(""),
    art:          str = Form("Privatperson"),
    notiz:        str = Form(""),
):
    if not name.strip():
        return _fehler("Name der Ersatzpflegekraft fehlt.", person)
    db = get_db(request)
    owner_id = get_owner_id(request)
    e = Ersatzpflegekraft(
        id=ersatz_id, person=person,
        name=name.strip(), geburtsdatum=geburtsdatum.strip(),
        adresse=adresse.strip(), art=art, notiz=notiz.strip(),
        owner_id=owner_id,
    )
    db.ersatz_speichern(e)
    return redirect(request, 
        f"/versicherte/?person={quote(person, safe='')}&ok=Ersatzpflegekraft+gespeichert",
        status_code=303,
    )


@router.post("/ersatz/{ersatz_id}/loeschen")
async def ersatz_loeschen(
    request:   Request,
    ersatz_id: int,
    person:    str = Form(...),
):
    db = get_db(request)
    db.ersatz_loeschen(ersatz_id, person)
    return redirect(request, 
        f"/versicherte/?person={quote(person, safe='')}&ok=Ersatzpflegekraft+gelöscht",
        status_code=303,
    )
