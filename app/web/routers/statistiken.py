"""
Router: Statistiken & Auswertungen
"""
from __future__ import annotations

from datetime import date
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from web.routers.deps import TEMPLATES, base_ctx, get_db, get_owner_id

router = APIRouter(prefix="/statistiken", tags=["Statistiken"])

MONATE_DE = ["", "Jan", "Feb", "Mär", "Apr", "Mai", "Jun",
             "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]


@router.get("/", response_class=HTMLResponse)
async def statistiken(request: Request, person: str = "", jahr: int = 0):
    db = get_db(request)
    owner_id = get_owner_id(request)

    if not jahr:
        jahr = date.today().year

    personen = db.personen(owner_id)
    alle_eintraege = db.alle(owner_id)
    jahre = db.jahre(owner_id) or [jahr]

    # Filter nach Person
    if person:
        eintraege = [e for e in alle_eintraege if e.person == person]
    else:
        eintraege = alle_eintraege

    # ── Stunden pro Monat (laufendes Jahr) ────────────────────────
    stunden_monat = [0.0] * 13  # Index 1-12
    eintraege_monat = [0] * 13
    for e in eintraege:
        if e.jahr == jahr:
            stunden_monat[e.monat] += e.stunden
            eintraege_monat[e.monat] += 1

    # ── Stunden pro Jahr ──────────────────────────────────────────
    stunden_jahr = {}
    for e in eintraege:
        stunden_jahr[e.jahr] = stunden_jahr.get(e.jahr, 0.0) + e.stunden

    # ── Art-Verteilung ────────────────────────────────────────────
    art_stats = {}
    for e in eintraege:
        if e.jahr == jahr:
            art_stats[e.art] = art_stats.get(e.art, 0) + 1

    # ── Top Personen ──────────────────────────────────────────────
    personen_stats = {}
    for e in eintraege:
        if e.jahr == jahr:
            p = e.person
            if p not in personen_stats:
                personen_stats[p] = {"stunden": 0.0, "eintraege": 0}
            personen_stats[p]["stunden"] += e.stunden
            personen_stats[p]["eintraege"] += 1

    # ── Pflegegrad-Verlauf ────────────────────────────────────────
    pg_verlauf = []
    try:
        verlauf = db.pg_verlauf_alle(owner_id, person)
        pg_verlauf = [
            {"datum": v.datum, "pflegegrad": v.pflegegrad,
             "gesamtpunkte": v.gesamtpunkte, "person": v.person}
            for v in reversed(verlauf)  # chronologisch
        ]
    except Exception:
        pass

    # ── Tagebuch-Stimmung pro Monat ───────────────────────────────
    stimmung_monat = {}
    stimmung_count = {}
    try:
        tb_eintraege = db.tagebuch_alle(owner_id, person)
        for e in tb_eintraege:
            if e.stimmung and e.datum[:4] == str(jahr):
                m = int(e.datum[5:7])
                stimmung_monat[m] = stimmung_monat.get(m, 0) + e.stimmung
                stimmung_count[m] = stimmung_count.get(m, 0) + 1
    except Exception:
        pass

    avg_stimmung_monat = {
        m: round(stimmung_monat[m] / stimmung_count[m], 1)
        for m in stimmung_monat
    }

    # ── Gesamt-Statistik ──────────────────────────────────────────
    gesamt = db.statistik(owner_id)

    return TEMPLATES.TemplateResponse(request, "statistiken/index.html", {
        **base_ctx(request),
        "personen":           personen,
        "jahre":              sorted(jahre, reverse=True),
        "filter_person":      person,
        "filter_jahr":        jahr,
        "stunden_monat":      stunden_monat,
        "eintraege_monat":    eintraege_monat,
        "stunden_jahr":       stunden_jahr,
        "art_stats":          art_stats,
        "personen_stats":     personen_stats,
        "pg_verlauf":         pg_verlauf,
        "avg_stimmung_monat": avg_stimmung_monat,
        "gesamt":             gesamt,
        "monate_kurz":        MONATE_DE,
    })
