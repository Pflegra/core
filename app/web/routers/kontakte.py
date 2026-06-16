"""
Router: Kontaktverwaltung
Pro versicherter Person: Hausarzt, Pflegekasse, Pflegedienst, Beratungsstelle, Sonstiges.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse

from web.routers.deps import TEMPLATES, base_ctx, get_db, get_owner_id, redirect, audit_log
from db.audit import AuditEvent

log = logging.getLogger(__name__)

router = APIRouter(prefix="/kontakte", tags=["Kontakte"])

KONTAKT_TYPEN = {
    "hausarzt":       "🩺 Hausarzt",
    "pflegekasse":    "🏥 Pflegekasse",
    "pflegedienst":   "🤝 Pflegedienst",
    "beratungsstelle": "💬 Beratungsstelle",
    "sonstiges":      "📋 Sonstiger Kontakt",
}


@dataclass
class Kontakt:
    id: int
    owner_id: int
    person: str
    typ: str
    name: str
    ansprechpartner: str
    telefon: str
    email: str
    adresse: str
    kundennummer: str
    notiz: str
    created_at: str

    @property
    def typ_label(self) -> str:
        return KONTAKT_TYPEN.get(self.typ, "📋 Sonstiges")


def _lade_kontakte(request: Request, owner_id: int, person: str = "") -> list[Kontakt]:
    db = get_db(request)
    with db._schema.connect() as conn:
        if person:
            rows = conn.execute(
                "SELECT * FROM kontakte WHERE owner_id=? AND person=? ORDER BY typ, name",
                (owner_id, person)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM kontakte WHERE owner_id=? ORDER BY person, typ, name",
                (owner_id,)
            ).fetchall()
    return [Kontakt(**dict(r)) for r in rows]


def _lade_kontakt(request: Request, owner_id: int, kontakt_id: int) -> Optional[Kontakt]:
    db = get_db(request)
    with db._schema.connect() as conn:
        row = conn.execute(
            "SELECT * FROM kontakte WHERE id=? AND owner_id=?",
            (kontakt_id, owner_id)
        ).fetchone()
    return Kontakt(**dict(row)) if row else None


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
async def kontakte_uebersicht(request: Request, person: str = ""):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    kontakte = _lade_kontakte(request, owner_id, person)
    personen = _lade_personen(request, owner_id)

    # Gruppiert nach Typ
    nach_typ: dict[str, list[Kontakt]] = {}
    for k in kontakte:
        nach_typ.setdefault(k.typ, []).append(k)

    return TEMPLATES.TemplateResponse(request, "kontakte/index.html", {
        **base_ctx(request),
        "kontakte": kontakte,
        "nach_typ": nach_typ,
        "personen": personen,
        "filter_person": person,
        "typen": KONTAKT_TYPEN,
    })


# ── Neu ────────────────────────────────────────────────────────────────────────

@router.get("/neu", response_class=HTMLResponse)
async def kontakt_neu(request: Request, person: str = "", typ: str = ""):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    personen = _lade_personen(request, owner_id)
    return TEMPLATES.TemplateResponse(request, "kontakte/formular.html", {
        **base_ctx(request),
        "kontakt": None,
        "personen": personen,
        "typen": KONTAKT_TYPEN,
        "vorauswahl_person": person,
        "vorauswahl_typ": typ,
    })


@router.post("/neu")
async def kontakt_neu_post(
    request:         Request,
    person:          str = Form(...),
    typ:             str = Form("sonstiges"),
    name:            str = Form(...),
    ansprechpartner: str = Form(""),
    telefon:         str = Form(""),
    email:           str = Form(""),
    adresse:         str = Form(""),
    kundennummer:    str = Form(""),
    notiz:           str = Form(""),
):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    db = get_db(request)
    with db._schema.connect() as conn:
        conn.execute(
            """INSERT INTO kontakte
               (owner_id, person, typ, name, ansprechpartner, telefon, email, adresse, kundennummer, notiz)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (owner_id, person.strip(), typ, name.strip(), ansprechpartner.strip(),
             telefon.strip(), email.strip(), adresse.strip(), kundennummer.strip(), notiz.strip())
        )
    audit_log(request, AuditEvent.KONTAKT_ERSTELLT,
              f"{KONTAKT_TYPEN.get(typ, typ)} · {name.strip()} · {person.strip()}")
    return redirect(request, f"/kontakte/?person={person}")


# ── Bearbeiten ─────────────────────────────────────────────────────────────────

@router.get("/{kontakt_id}/bearbeiten", response_class=HTMLResponse)
async def kontakt_bearbeiten(request: Request, kontakt_id: int):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    kontakt = _lade_kontakt(request, owner_id, kontakt_id)
    if not kontakt:
        return redirect(request, "/kontakte/")
    personen = _lade_personen(request, owner_id)
    return TEMPLATES.TemplateResponse(request, "kontakte/formular.html", {
        **base_ctx(request),
        "kontakt": kontakt,
        "personen": personen,
        "typen": KONTAKT_TYPEN,
        "vorauswahl_person": kontakt.person,
        "vorauswahl_typ": kontakt.typ,
    })


@router.post("/{kontakt_id}/bearbeiten")
async def kontakt_bearbeiten_post(
    request:         Request,
    kontakt_id:      int,
    person:          str = Form(...),
    typ:             str = Form("sonstiges"),
    name:            str = Form(...),
    ansprechpartner: str = Form(""),
    telefon:         str = Form(""),
    email:           str = Form(""),
    adresse:         str = Form(""),
    kundennummer:    str = Form(""),
    notiz:           str = Form(""),
):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    db = get_db(request)
    with db._schema.connect() as conn:
        conn.execute(
            """UPDATE kontakte SET
               person=?, typ=?, name=?, ansprechpartner=?, telefon=?,
               email=?, adresse=?, kundennummer=?, notiz=?
               WHERE id=? AND owner_id=?""",
            (person.strip(), typ, name.strip(), ansprechpartner.strip(), telefon.strip(),
             email.strip(), adresse.strip(), kundennummer.strip(), notiz.strip(),
             kontakt_id, owner_id)
        )
    audit_log(request, AuditEvent.KONTAKT_BEARBEITET,
              f"{KONTAKT_TYPEN.get(typ, typ)} · {name.strip()} · {person.strip()} (ID {kontakt_id})")
    return redirect(request, f"/kontakte/?person={person}")


# ── Löschen ────────────────────────────────────────────────────────────────────

@router.post("/{kontakt_id}/loeschen")
async def kontakt_loeschen(request: Request, kontakt_id: int):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    db = get_db(request)
    kontakt = _lade_kontakt(request, owner_id, kontakt_id)
    person = kontakt.person if kontakt else ""
    with db._schema.connect() as conn:
        conn.execute("DELETE FROM kontakte WHERE id=? AND owner_id=?", (kontakt_id, owner_id))
    audit_log(request, AuditEvent.KONTAKT_GELOESCHT,
              f"{kontakt.name if kontakt else kontakt_id} · {person}")
    return redirect(request, f"/kontakte/?person={person}")
