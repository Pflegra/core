"""
Router: Pflege-Kalender
Monatsansicht aller Termine: eigene Fristen, Pflegeberatung, automatische Fristen.
Keine eigene Tabelle — reine Aggregationsansicht über bestehende Quellen.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from web.routers.deps import TEMPLATES, base_ctx, get_db, get_owner_id

router = APIRouter(prefix="/kalender", tags=["Kalender"])


@router.get("/", response_class=HTMLResponse)
async def kalender_uebersicht(request: Request, monat: int = 0, jahr: int = 0, person: str = ""):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    heute = date.today()
    monat = monat or heute.month
    jahr = jahr or heute.year
    # Grenzen absichern
    if monat < 1:
        monat, jahr = 12, jahr - 1
    elif monat > 12:
        monat, jahr = 1, jahr + 1

    owner_id = get_owner_id(request)
    db = get_db(request)

    # Eigene Fristen
    from web.routers.fristen import _lade_fristen
    eigene_fristen = _lade_fristen(request, owner_id, person, nur_offen=False)

    # Pflegeberatung: neuester Eintrag pro Person
    from web.routers.pflegeberatung import _lade_eintraege
    alle_beratungen = _lade_eintraege(request, owner_id, person)
    neueste_beratung_pro_person = {}
    for b in alle_beratungen:
        if b.person not in neueste_beratung_pro_person:
            neueste_beratung_pro_person[b.person] = b
    beratungen = list(neueste_beratung_pro_person.values())

    # Automatische Fristen (Entlastungsbetrag-Übertrag etc.)
    fristen_aus_service = []
    try:
        from services.fristen_service import berechne_fristen
        with db._schema.connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT person FROM pflege_eintraege WHERE owner_id=? ORDER BY person",
                (owner_id,)
            ).fetchall()
        personen_namen = [r["person"] for r in rows if r["person"]]
        if person:
            personen_namen = [p for p in personen_namen if p == person]

        personen_daten = []
        budget_service = request.app.state.budget_service
        konfig = request.app.state.konfig
        regelwerk = konfig.regelwerk if hasattr(konfig, "regelwerk") else None
        sichtbarer_stichtag = date(jahr, monat, 1)
        aktuelles_jahr = jahr
        alle_eintraege = db.alle(owner_id)
        for p in personen_namen:
            try:
                bericht = budget_service.bericht_fuer_person(p, aktuelles_jahr, owner_id, eintraege=alle_eintraege)
            except Exception:
                bericht = None
            vers = db.versicherter_laden(p, owner_id) if hasattr(db, "versicherter_laden") else None
            personen_daten.append({
                "name": p,
                "bericht": bericht,
                "vers": vers,
                "entlastung_verbrauch_gesamt": 0.0,
            })
        if regelwerk is not None:
            fristen_aus_service = berechne_fristen(
                personen_daten, aktuelles_jahr, regelwerk, stichtag=sichtbarer_stichtag
            )
    except Exception:
        fristen_aus_service = []

    from services.kalender_service import baue_kalender, MONATSNAMEN, monat_navigation

    # Dokumente (für "Dokument hochgeladen" Anzeige)
    dokumente_liste = []
    try:
        with db._schema.connect() as conn:
            if person:
                rows = conn.execute(
                    "SELECT * FROM dokumente WHERE owner_id=? AND person=?",
                    (owner_id, person)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM dokumente WHERE owner_id=?",
                    (owner_id,)
                ).fetchall()
        from web.routers.dokumente import Dokument
        dokumente_liste = [Dokument(**dict(r)) for r in rows]
    except Exception:
        dokumente_liste = []

    # Tagebucheinträge
    tagebuch_liste = []
    try:
        if person:
            tagebuch_liste = db.tagebuch_alle(owner_id, person)
        else:
            tagebuch_liste = db.tagebuch_alle(owner_id, "")
    except Exception:
        tagebuch_liste = []

    # Eigene Termine: Stammtermine laden und nur fuer den sichtbaren Monat expandieren
    from web.routers.termine import _lade_termine
    from services.termine_service import alle_vorkommen_im_monat
    termine_liste = _lade_termine(request, owner_id, person)
    termin_vorkommen = alle_vorkommen_im_monat(termine_liste, jahr, monat)

    tage = baue_kalender(eigene_fristen, beratungen, fristen_aus_service, monat, jahr,
                          dokumente=dokumente_liste, tagebuch_eintraege=tagebuch_liste,
                          termin_vorkommen=termin_vorkommen)

    prev, nxt = monat_navigation(monat, jahr)

    # Kalendergrid berechnen (Montag = 0)
    import calendar
    cal = calendar.Calendar(firstweekday=0)
    wochen = cal.monthdayscalendar(jahr, monat)

    personen_namen_alle = db.personen(owner_id)

    return TEMPLATES.TemplateResponse(request, "kalender/index.html", {
        **base_ctx(request),
        "monat": monat,
        "jahr": jahr,
        "monatsname": MONATSNAMEN.get(monat, ""),
        "wochen": wochen,
        "tage": tage,
        "heute": heute,
        "prev_monat": prev[0], "prev_jahr": prev[1],
        "next_monat": nxt[0], "next_jahr": nxt[1],
        "personen": personen_namen_alle,
        "filter_person": person,
    })
