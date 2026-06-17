"""
Router: Eigene Fristen
Pro versicherter Person eigene Termine und Fristen verwalten.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse

from web.routers.deps import TEMPLATES, base_ctx, get_db, get_owner_id, redirect, audit_log
from db.audit import AuditEvent

router = APIRouter(prefix="/fristen", tags=["Fristen"])

KATEGORIEN = {
    "termin":       "📅 Termin",
    "dokument":     "📄 Dokument / Ausweis",
    "antrag":       "📋 Antrag / Frist",
    "arzt":         "🩺 Arzt / Therapie",
    "behoerde":     "🏛️ Behörde / Amt",
    "sonstiges":    "📌 Sonstiges",
}


@dataclass
class EigeneFrist:
    id: int
    owner_id: int
    person: str
    titel: str
    datum: str
    kategorie: str
    notiz: str
    erledigt: int
    created_at: str

    @property
    def datum_date(self) -> Optional[date]:
        try:
            return date.fromisoformat(self.datum)
        except Exception:
            return None

    @property
    def datum_str(self) -> str:
        d = self.datum_date
        return d.strftime("%d.%m.%Y") if d else self.datum

    @property
    def tage(self) -> Optional[int]:
        d = self.datum_date
        return (d - date.today()).days if d else None

    @property
    def ampel(self) -> str:
        t = self.tage
        if t is None:   return "gruen"
        if t < 0:       return "rot"
        if t <= 7:      return "orange"
        if t <= 30:     return "gelb"
        return "gruen"

    @property
    def ampel_emoji(self) -> str:
        return {"rot": "🔴", "orange": "🟠", "gelb": "🟡", "gruen": "🟢"}[self.ampel]

    @property
    def kategorie_label(self) -> str:
        return KATEGORIEN.get(self.kategorie, "📌 Sonstiges")

    @property
    def ist_erledigt(self) -> bool:
        return bool(self.erledigt)


def _lade_fristen(request: Request, owner_id: int, person: str = "", nur_offen: bool = False) -> list[EigeneFrist]:
    db = get_db(request)
    with db._schema.connect() as conn:
        if person and nur_offen:
            rows = conn.execute(
                "SELECT * FROM eigene_fristen WHERE owner_id=? AND person=? AND erledigt=0 ORDER BY datum",
                (owner_id, person)
            ).fetchall()
        elif person:
            rows = conn.execute(
                "SELECT * FROM eigene_fristen WHERE owner_id=? AND person=? ORDER BY erledigt, datum",
                (owner_id, person)
            ).fetchall()
        elif nur_offen:
            rows = conn.execute(
                "SELECT * FROM eigene_fristen WHERE owner_id=? AND erledigt=0 ORDER BY datum",
                (owner_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM eigene_fristen WHERE owner_id=? ORDER BY erledigt, datum",
                (owner_id,)
            ).fetchall()
    return [EigeneFrist(**dict(r)) for r in rows]


def _lade_frist(request: Request, owner_id: int, frist_id: int) -> Optional[EigeneFrist]:
    db = get_db(request)
    with db._schema.connect() as conn:
        row = conn.execute(
            "SELECT * FROM eigene_fristen WHERE id=? AND owner_id=?",
            (frist_id, owner_id)
        ).fetchone()
    return EigeneFrist(**dict(row)) if row else None


def _lade_personen(request: Request, owner_id: int) -> list[str]:
    db = get_db(request)
    with db._schema.connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT person FROM pflege_eintraege WHERE owner_id=? ORDER BY person",
            (owner_id,)
        ).fetchall()
    return [r["person"] for r in rows if r["person"]]


# ── Übersicht ──────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def fristen_uebersicht(request: Request, person: str = "", erledigt: str = ""):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    nur_offen = erledigt != "alle"
    fristen = _lade_fristen(request, owner_id, person, nur_offen=nur_offen)
    personen = _lade_personen(request, owner_id)
    return TEMPLATES.TemplateResponse(request, "fristen/index.html", {
        **base_ctx(request),
        "fristen": fristen,
        "personen": personen,
        "filter_person": person,
        "zeige_erledigt": erledigt == "alle",
        "kategorien": KATEGORIEN,
    })


# ── Neu ────────────────────────────────────────────────────────────────────────

@router.get("/neu", response_class=HTMLResponse)
async def frist_neu(request: Request, person: str = ""):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    personen = _lade_personen(request, owner_id)
    return TEMPLATES.TemplateResponse(request, "fristen/formular.html", {
        **base_ctx(request),
        "frist": None,
        "personen": personen,
        "kategorien": KATEGORIEN,
        "vorauswahl_person": person,
    })


@router.post("/neu")
async def frist_neu_post(
    request:   Request,
    person:    str = Form(...),
    titel:     str = Form(...),
    datum:     str = Form(...),
    kategorie: str = Form("sonstiges"),
    notiz:     str = Form(""),
):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    db = get_db(request)
    with db._schema.connect() as conn:
        conn.execute(
            "INSERT INTO eigene_fristen (owner_id, person, titel, datum, kategorie, notiz) VALUES (?,?,?,?,?,?)",
            (owner_id, person.strip(), titel.strip(), datum, kategorie, notiz.strip())
        )
    audit_log(request, AuditEvent.EINTRAG_ERSTELLT, f"Frist: {titel.strip()} · {person.strip()} · {datum}")
    return redirect(request, f"/fristen/?person={person}")


# ── Bearbeiten ─────────────────────────────────────────────────────────────────

@router.get("/{frist_id}/bearbeiten", response_class=HTMLResponse)
async def frist_bearbeiten(request: Request, frist_id: int):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    frist = _lade_frist(request, owner_id, frist_id)
    if not frist:
        return redirect(request, "/fristen/")
    personen = _lade_personen(request, owner_id)
    return TEMPLATES.TemplateResponse(request, "fristen/formular.html", {
        **base_ctx(request),
        "frist": frist,
        "personen": personen,
        "kategorien": KATEGORIEN,
        "vorauswahl_person": frist.person,
    })


@router.post("/{frist_id}/bearbeiten")
async def frist_bearbeiten_post(
    request:   Request,
    frist_id:  int,
    person:    str = Form(...),
    titel:     str = Form(...),
    datum:     str = Form(...),
    kategorie: str = Form("sonstiges"),
    notiz:     str = Form(""),
):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    db = get_db(request)
    with db._schema.connect() as conn:
        conn.execute(
            "UPDATE eigene_fristen SET person=?, titel=?, datum=?, kategorie=?, notiz=? WHERE id=? AND owner_id=?",
            (person.strip(), titel.strip(), datum, kategorie, notiz.strip(), frist_id, owner_id)
        )
    audit_log(request, AuditEvent.EINTRAG_BEARBEITET, f"Frist: {titel.strip()} · {person.strip()} (ID {frist_id})")
    return redirect(request, f"/fristen/?person={person}")


# ── Erledigt togglen ───────────────────────────────────────────────────────────

@router.post("/{frist_id}/erledigt")
async def frist_erledigt(request: Request, frist_id: int):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    db = get_db(request)
    frist = _lade_frist(request, owner_id, frist_id)
    neu = 0 if (frist and frist.erledigt) else 1
    with db._schema.connect() as conn:
        conn.execute(
            "UPDATE eigene_fristen SET erledigt=? WHERE id=? AND owner_id=?",
            (neu, frist_id, owner_id)
        )
    person = frist.person if frist else ""
    return redirect(request, f"/fristen/?person={person}")


# ── Löschen ────────────────────────────────────────────────────────────────────

@router.post("/{frist_id}/loeschen")
async def frist_loeschen(request: Request, frist_id: int):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    db = get_db(request)
    frist = _lade_frist(request, owner_id, frist_id)
    person = frist.person if frist else ""
    with db._schema.connect() as conn:
        conn.execute("DELETE FROM eigene_fristen WHERE id=? AND owner_id=?", (frist_id, owner_id))
    audit_log(request, AuditEvent.EINTRAG_GELOESCHT, f"Frist: {frist.titel if frist else frist_id} · {person}")
    return redirect(request, f"/fristen/?person={person}")
