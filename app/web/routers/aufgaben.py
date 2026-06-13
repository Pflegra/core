"""
Router: Offene Aufgaben
Zentrale Übersicht aller offenen Aufgaben und Fristen.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from web.routers.deps import TEMPLATES, base_ctx, get_db, get_owner_id

router = APIRouter(prefix="/aufgaben", tags=["Aufgaben"])


@router.get("/", response_class=HTMLResponse)
async def aufgaben_uebersicht(request: Request):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    db = get_db(request)
    from datetime import date
    aktuelles_jahr = date.today().year

    # Fristen laden
    fristen = []
    try:
        from services.fristen_service import berechne_fristen
        personen_daten = []
        with db._schema.connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT person FROM pflege_eintraege WHERE owner_id=?", (owner_id,)
            ).fetchall()
            for row in rows:
                # Entlastungsverbrauch laden
                ev = conn.execute(
                    "SELECT COALESCE(SUM(betrag),0) as s FROM entlastung_buchungen WHERE owner_id=? AND strftime('%Y',datum)=?",
                    (owner_id, str(aktuelles_jahr))
                ).fetchone()
                personen_daten.append({
                    "name": row["person"],
                    "bericht": None,
                    "entlastung_verbrauch_gesamt": ev["s"] if ev else 0.0,
                    "entlastung_verbrauch_monat": 0.0,
                    "letztes_pg_datum": None,
                    "vers": None,
                })

        from pflege_rules import get_regelwerk
        regelwerk = get_regelwerk(aktuelles_jahr)
        fristen = berechne_fristen(personen_daten, aktuelles_jahr, regelwerk)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Fristen Fehler: %s", e, exc_info=True)

    # Pflegeberatungen laden
    alle_beratungen = []
    try:
        from web.routers.pflegeberatung import _lade_eintraege
        beratungen_raw = _lade_eintraege(request, owner_id)
        seen = set()
        for b in beratungen_raw:
            if b.person not in seen:
                seen.add(b.person)
                alle_beratungen.append(b)
    except Exception:
        pass

    # Aufgaben berechnen
    from services.aufgaben_service import berechne_aufgaben
    aufgaben = berechne_aufgaben(fristen, alle_beratungen)

    return TEMPLATES.TemplateResponse(request, "aufgaben/index.html", {
        **base_ctx(request),
        "aufgaben": aufgaben,
    })
