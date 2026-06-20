"""CRUD fuer eigene, optional wiederkehrende Termine."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

from db.audit import AuditEvent
from services.termine_service import WIEDERHOLUNGEN
from web.routers.deps import TEMPLATES, audit_log, base_ctx, get_db, get_owner_id, redirect

router = APIRouter(prefix="/termine", tags=["Termine"])

WIEDERHOLUNG_LABELS = {
    "einmalig": "Einmalig",
    "taeglich": "Täglich",
    "woechentlich": "Wöchentlich",
    "monatlich": "Monatlich",
    "jaehrlich": "Jährlich",
}


@dataclass
class EigenerTermin:
    id: int
    owner_id: int
    person: str
    titel: str
    datum: str
    ganztag: int
    uhrzeit_von: str
    uhrzeit_bis: str
    wiederholung: str
    notiz: str
    created_at: str

    @property
    def datum_date(self) -> Optional[date]:
        try:
            return date.fromisoformat(self.datum)
        except (TypeError, ValueError):
            return None

    @property
    def datum_str(self) -> str:
        return self.datum_date.strftime("%d.%m.%Y") if self.datum_date else self.datum

    @property
    def wiederholung_label(self) -> str:
        return WIEDERHOLUNG_LABELS.get(self.wiederholung, self.wiederholung)

    @property
    def zeit_text(self) -> str:
        if self.ganztag:
            return "Ganztägig"
        if self.uhrzeit_von and self.uhrzeit_bis:
            return f"{self.uhrzeit_von}–{self.uhrzeit_bis} Uhr"
        if self.uhrzeit_von:
            return f"ab {self.uhrzeit_von} Uhr"
        return "Ohne Uhrzeit"


def _lade_personen(request: Request, owner_id: int) -> list[str]:
    return get_db(request).personen(owner_id)


def _lade_termine(request: Request, owner_id: int, person: str = "") -> list[EigenerTermin]:
    db = get_db(request)
    with db._schema.connect() as conn:
        if person:
            rows = conn.execute(
                """SELECT * FROM eigene_termine
                   WHERE owner_id=? AND (person=? OR person='')
                   ORDER BY datum, ganztag DESC, uhrzeit_von, titel""",
                (owner_id, person),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM eigene_termine WHERE owner_id=?
                   ORDER BY datum, ganztag DESC, uhrzeit_von, titel""",
                (owner_id,),
            ).fetchall()
    return [EigenerTermin(**dict(row)) for row in rows]


def _lade_termin(request: Request, owner_id: int, termin_id: int) -> Optional[EigenerTermin]:
    db = get_db(request)
    with db._schema.connect() as conn:
        row = conn.execute(
            "SELECT * FROM eigene_termine WHERE id=? AND owner_id=?",
            (termin_id, owner_id),
        ).fetchone()
    return EigenerTermin(**dict(row)) if row else None


def _validiere(person: str, titel: str, datum: str, ganztag: int,
               uhrzeit_von: str, uhrzeit_bis: str, wiederholung: str,
               personen: list[str]) -> tuple[str, dict]:
    werte = {
        "person": person.strip(),
        "titel": titel.strip(),
        "datum": datum.strip(),
        "ganztag": 1 if ganztag else 0,
        "uhrzeit_von": uhrzeit_von.strip(),
        "uhrzeit_bis": uhrzeit_bis.strip(),
        "wiederholung": wiederholung.strip(),
    }
    if werte["person"] and werte["person"] not in personen:
        return "Die ausgewählte Person ist nicht verfügbar.", werte
    if not werte["titel"]:
        return "Bitte einen Titel eingeben.", werte
    try:
        date.fromisoformat(werte["datum"])
    except ValueError:
        return "Bitte ein gültiges Datum eingeben.", werte
    if werte["wiederholung"] not in WIEDERHOLUNGEN:
        return "Bitte eine gültige Wiederholung wählen.", werte
    if werte["ganztag"]:
        werte["uhrzeit_von"] = ""
        werte["uhrzeit_bis"] = ""
    else:
        for feld in ("uhrzeit_von", "uhrzeit_bis"):
            if werte[feld]:
                try:
                    datetime.strptime(werte[feld], "%H:%M")
                except ValueError:
                    return "Bitte gültige Uhrzeiten eingeben.", werte
        if werte["uhrzeit_bis"] and not werte["uhrzeit_von"]:
            return "Eine Endzeit benötigt eine Startzeit.", werte
        if werte["uhrzeit_von"] and werte["uhrzeit_bis"] < werte["uhrzeit_von"]:
            return "Die Endzeit darf nicht vor der Startzeit liegen.", werte
    return "", werte


def _formular(request: Request, owner_id: int, termin=None, fehler: str = ""):
    return TEMPLATES.TemplateResponse(request, "termine/formular.html", {
        **base_ctx(request),
        "termin": termin,
        "personen": _lade_personen(request, owner_id),
        "wiederholungen": WIEDERHOLUNG_LABELS,
        "fehler": fehler,
    }, status_code=400 if fehler else 200)


@router.get("/", response_class=HTMLResponse)
async def termine_uebersicht(request: Request, person: str = ""):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    return TEMPLATES.TemplateResponse(request, "termine/index.html", {
        **base_ctx(request),
        "termine": _lade_termine(request, owner_id, person),
        "personen": _lade_personen(request, owner_id),
        "filter_person": person,
    })


@router.get("/neu", response_class=HTMLResponse)
async def termin_neu(request: Request, person: str = ""):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    termin = EigenerTermin(0, owner_id, person, "", "", 1, "", "", "einmalig", "", "")
    return _formular(request, owner_id, termin)


@router.post("/neu")
async def termin_neu_post(request: Request, person: str = Form(""), titel: str = Form(...),
                          datum: str = Form(...), ganztag: int = Form(0),
                          uhrzeit_von: str = Form(""), uhrzeit_bis: str = Form(""),
                          wiederholung: str = Form("einmalig"), notiz: str = Form("")):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    personen = _lade_personen(request, owner_id)
    fehler, werte = _validiere(person, titel, datum, ganztag, uhrzeit_von, uhrzeit_bis, wiederholung, personen)
    if fehler:
        termin = EigenerTermin(0, owner_id, notiz=notiz.strip(), created_at="", **werte)
        return _formular(request, owner_id, termin, fehler)
    db = get_db(request)
    with db._schema.connect() as conn:
        conn.execute("""INSERT INTO eigene_termine
            (owner_id, person, titel, datum, ganztag, uhrzeit_von, uhrzeit_bis, wiederholung, notiz)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (owner_id, werte["person"], werte["titel"], werte["datum"], werte["ganztag"],
             werte["uhrzeit_von"], werte["uhrzeit_bis"], werte["wiederholung"], notiz.strip()))
    audit_log(request, AuditEvent.TERMIN_ERSTELLT, f"Termin: {werte['titel']} · {werte['datum']}")
    return redirect(request, "/termine/")


@router.get("/{termin_id}/bearbeiten", response_class=HTMLResponse)
async def termin_bearbeiten(request: Request, termin_id: int):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    termin = _lade_termin(request, owner_id, termin_id)
    return _formular(request, owner_id, termin) if termin else redirect(request, "/termine/")


@router.post("/{termin_id}/bearbeiten")
async def termin_bearbeiten_post(request: Request, termin_id: int,
                                 person: str = Form(""), titel: str = Form(...), datum: str = Form(...),
                                 ganztag: int = Form(0), uhrzeit_von: str = Form(""),
                                 uhrzeit_bis: str = Form(""), wiederholung: str = Form("einmalig"),
                                 notiz: str = Form("")):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    if not _lade_termin(request, owner_id, termin_id):
        return redirect(request, "/termine/")
    personen = _lade_personen(request, owner_id)
    fehler, werte = _validiere(person, titel, datum, ganztag, uhrzeit_von, uhrzeit_bis, wiederholung, personen)
    if fehler:
        termin = EigenerTermin(termin_id, owner_id, notiz=notiz.strip(), created_at="", **werte)
        return _formular(request, owner_id, termin, fehler)
    db = get_db(request)
    with db._schema.connect() as conn:
        conn.execute("""UPDATE eigene_termine SET
            person=?, titel=?, datum=?, ganztag=?, uhrzeit_von=?, uhrzeit_bis=?, wiederholung=?, notiz=?
            WHERE id=? AND owner_id=?""",
            (werte["person"], werte["titel"], werte["datum"], werte["ganztag"],
             werte["uhrzeit_von"], werte["uhrzeit_bis"], werte["wiederholung"],
             notiz.strip(), termin_id, owner_id))
    audit_log(request, AuditEvent.TERMIN_BEARBEITET, f"Termin: {werte['titel']} (ID {termin_id})")
    return redirect(request, "/termine/")


@router.post("/{termin_id}/loeschen")
async def termin_loeschen(request: Request, termin_id: int):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard
    owner_id = get_owner_id(request)
    termin = _lade_termin(request, owner_id, termin_id)
    if termin:
        db = get_db(request)
        with db._schema.connect() as conn:
            conn.execute("DELETE FROM eigene_termine WHERE id=? AND owner_id=?", (termin_id, owner_id))
        audit_log(request, AuditEvent.TERMIN_GELOESCHT, f"Termin: {termin.titel} (ID {termin_id})")
    return redirect(request, "/termine/")
