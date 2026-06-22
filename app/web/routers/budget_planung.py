"""
Router: Budgetplanung (Simulator/Planer)
Reine Vorausplanung ohne Ist-Vergleich.
"""
from __future__ import annotations

import json
import logging
from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from pflege_rules import get_regelwerk
from web.routers.deps import TEMPLATES, base_ctx, get_db, get_konfig, get_owner_id

log = logging.getLogger(__name__)
router = APIRouter(prefix="/budget/planung", tags=["Budgetplanung"])

MONATE_KURZ = ["", "Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
               "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]

PLANER_PERSON = "__planer__"


def _lade_gespeicherte_planung(db, jahr: int, owner_id: int) -> dict:
    """
    Lädt gespeicherte Planungsdaten aus der DB.
    Gibt ein Dict mit allen Feldern zurück, Defaults wenn nichts gespeichert.
    """
    roh = db.planung_laden(PLANER_PERSON, jahr, owner_id)  # {monat: {stunden, notiz}}

    planung_vp  = {}
    planung_kzp = {}
    planung_sl  = {}
    planung_pg  = {}

    for m in range(1, 13):
        eintrag = roh.get(m, {})
        planung_vp[m] = eintrag.get("stunden", 0.0)
        try:
            zusatz = json.loads(eintrag.get("notiz", "{}") or "{}")
        except (ValueError, TypeError):
            zusatz = {}
        planung_kzp[m] = zusatz.get("kzp", 0.0)
        planung_sl[m]  = zusatz.get("sl_pct", 0)
        planung_pg[m]  = zusatz.get("pg", 3)

    # Jahres-Extras aus monat=0
    eintrag_0 = roh.get(0, {})
    try:
        extras = json.loads(eintrag_0.get("notiz", "{}") or "{}")
    except (ValueError, TypeError):
        extras = {}

    # entlastung_vbr als flaches Dict für Template: {entlastung_vbr_1: 0, ...}
    entlastung_vbr_raw = extras.get("entlastung_vbr", {})
    planung_data = {f"entlastung_vbr_{m}": entlastung_vbr_raw.get(str(m), 0) for m in range(1, 13)}

    return {
        "planung_vp":       planung_vp,
        "planung_kzp":      planung_kzp,
        "planung_sl":       planung_sl,
        "planung_pg":       planung_pg,
        "vorjahr_guthaben": extras.get("vorjahr_guthaben", 0.0),
        "entlastung_kzp":   extras.get("entlastung_kzp", False),
        "planung_data":     planung_data,
    }


@router.get("/", response_class=HTMLResponse)
async def planung_uebersicht(request: Request, jahr: int = 0):
    db     = get_db(request)
    konfig = get_konfig(request)
    owner_id = get_owner_id(request)
    jahre  = db.jahre(owner_id) or [date.today().year]
    aktuell = date.today().year
    for j in [aktuell, aktuell + 1]:
        if j not in jahre:
            jahre.append(j)
    jahre = sorted(set(jahre), reverse=True)
    if not jahr:
        jahr = aktuell

    regeln = get_regelwerk(jahr)

    pg_saetze = {pg: regeln.pflegegeld_monatlich(pg)   for pg in range(1, 6)}
    sl_saetze = {pg: regeln.sachleistung_monatlich(pg) for pg in range(1, 6)}
    tp_saetze = {pg: regeln.tagespflege_monatlich(pg)  for pg in range(1, 6)}

    gespeichert  = _lade_gespeicherte_planung(db, jahr, owner_id)
    personen     = db.personen(owner_id)
    standard_pflegegrad = 3
    if personen:
        v = db.versicherter_laden(personen[0], owner_id)
        if v and v.pflegegrad:
            standard_pflegegrad = v.pflegegrad

    from i18n import get_lang, make_t
    lang = get_lang(request)
    t = make_t(lang)
    monate_kurz_t = t("budgetplanung.monate_kurz")
    if not isinstance(monate_kurz_t, list):
        monate_kurz_t = MONATE_KURZ
    monate_liste = [{"nr": m, "name": monate_kurz_t[m]} for m in range(1, 13)]

    return TEMPLATES.TemplateResponse(request, "budget/planung.html", {
        **base_ctx(request),
        "jahre":               jahre,
        "jahr":                jahr,
        "budget_gesamt":       regeln.vp_budget_jahresbetrag,
        "pg_saetze":           pg_saetze,
        "sl_saetze":           sl_saetze,
        "tp_saetze":           tp_saetze,
        "entlastungsbetrag":   regeln.entlastungsbetrag_monatlich,
        "hilfsmittel":         regeln.pflegehilfsmittel_monatlich,
        "hausnotruf":          regeln.hausnotruf_monatlich,
        "wohnumfeld":          regeln.wohnumfeld_je_massnahme,
        "dipa_app":            regeln.dipa_app_monatlich,
        "dipa_unterstuetzung": regeln.dipa_unterstuetzung_monatlich,
        "standard_pflegegrad": standard_pflegegrad,
        "monate_liste":        monate_liste,
        "regeln":              regeln,
        "planung_vp":          gespeichert["planung_vp"],
        "planung_kzp":         gespeichert["planung_kzp"],
        "planung_sl":          gespeichert["planung_sl"],
        "planung_pg":          gespeichert["planung_pg"],
        "vorjahr_guthaben":    gespeichert["vorjahr_guthaben"],
        "entlastung_kzp":      gespeichert["entlastung_kzp"],
        "planung_data":        gespeichert.get("planung_data", {}),
    })


@router.post("/ajax-speichern")
async def planung_ajax_speichern(request: Request):
    try:
        body = await request.json()
        jahr     = int(body.get("jahr", date.today().year))
        db       = get_db(request)
        owner_id = get_owner_id(request)
        vp_data  = {int(k): float(v) for k, v in body.get("vp",  {}).items()}
        kzp_data = {int(k): float(v) for k, v in body.get("kzp", {}).items()}
        sl_data  = {int(k): int(v)   for k, v in body.get("sl",  {}).items()}
        pg_data  = {int(k): int(v)   for k, v in body.get("pg",  {}).items()}

        with db._schema.connect() as conn:
            for m in range(1, 13):
                zusatz = json.dumps({
                    "kzp":    kzp_data.get(m, 0.0),
                    "sl_pct": sl_data.get(m, 0),
                    "pg":     pg_data.get(m, 3),
                })
                conn.execute("""
                    INSERT INTO budget_planung (person, jahr, monat, stunden, notiz, owner_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(owner_id, person, jahr, monat) DO UPDATE SET
                        stunden=excluded.stunden, notiz=excluded.notiz
                """, (PLANER_PERSON, jahr, m, vp_data.get(m, 0.0), zusatz, owner_id))

            # Jahres-Extras in monat=0
            entlastung_vbr = body.get("entlastung_vbr", {})
            extras = json.dumps({
                "vorjahr_guthaben": float(body.get("vorjahr_guthaben", 0.0)),
                "entlastung_kzp":   bool(body.get("entlastung_kzp", False)),
                "entlastung_vbr":   {str(k): float(v) for k, v in entlastung_vbr.items()},
            })
            conn.execute("""
                INSERT INTO budget_planung (person, jahr, monat, stunden, notiz, owner_id)
                VALUES (?, ?, 0, 0.0, ?, ?)
                ON CONFLICT(owner_id, person, jahr, monat) DO UPDATE SET notiz=excluded.notiz
            """, (PLANER_PERSON, jahr, extras, owner_id))

        return JSONResponse({"ok": True})
    except Exception as exc:
        log.error("Planung AJAX Fehler: %s", exc, exc_info=True)
        return JSONResponse({"ok": False, "fehler": str(exc)}, status_code=500)
