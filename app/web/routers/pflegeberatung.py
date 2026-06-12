"""
Router: Pflegeberatung § 37.3 SGB XI
Dokumentation von Beratungsbesuchen, Nachweis-Upload, Fristüberwachung.
"""
from __future__ import annotations

import os
import shutil
import logging
from pathlib import Path
from datetime import date, datetime, timedelta
from dataclasses import dataclass
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse

from web.routers.deps import TEMPLATES, base_ctx, get_db, get_owner_id, redirect

log = logging.getLogger(__name__)

router = APIRouter(prefix="/pflegeberatung", tags=["Pflegeberatung"])

MAX_DATEI_MB = 20


@dataclass
class Beratungseintrag:
    id: int
    owner_id: int
    person: str
    datum: str
    berater: str
    notiz: str
    datei_pfad: str
    datei_name: str
    created_at: str

    @property
    def datum_obj(self) -> Optional[date]:
        try:
            return date.fromisoformat(self.datum)
        except Exception:
            return None

    @property
    def naechster_termin(self) -> Optional[date]:
        d = self.datum_obj
        if not d:
            return None
        return d + timedelta(days=183)  # ca. 6 Monate

    @property
    def naechster_termin_str(self) -> str:
        t = self.naechster_termin
        return t.strftime("%d.%m.%Y") if t else ""

    @property
    def tage_bis_termin(self) -> Optional[int]:
        t = self.naechster_termin
        if not t:
            return None
        return (t - date.today()).days

    @property
    def status(self) -> str:
        d = self.tage_bis_termin
        if d is None:
            return "unbekannt"
        if d < 0:
            return "überfällig"
        if d <= 30:
            return "bald"
        return "ok"


def _beratung_dir(request: Request, owner_id: int) -> Path:
    data_dir = request.app.state.data_dir
    d = Path(data_dir) / "pflegeberatung" / str(owner_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _lade_eintraege(request: Request, owner_id: int, person: str = "") -> list[Beratungseintrag]:
    db = get_db(request)
    with db._schema.connect() as conn:
        if person:
            rows = conn.execute(
                "SELECT * FROM pflegeberatung WHERE owner_id=? AND person=? ORDER BY datum DESC",
                (owner_id, person)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM pflegeberatung WHERE owner_id=? ORDER BY datum DESC",
                (owner_id,)
            ).fetchall()
    return [Beratungseintrag(**dict(r)) for r in rows]


def _lade_eintrag(request: Request, owner_id: int, eintrag_id: int) -> Optional[Beratungseintrag]:
    db = get_db(request)
    with db._schema.connect() as conn:
        row = conn.execute(
            "SELECT * FROM pflegeberatung WHERE id=? AND owner_id=?",
            (eintrag_id, owner_id)
        ).fetchone()
    if not row:
        return None
    return Beratungseintrag(**dict(row))


def _naechste_frist(eintraege: list[Beratungseintrag], person: str) -> Optional[date]:
    """Berechnet die nächste Pflichtfrist basierend auf dem letzten Eintrag."""
    person_eintraege = [e for e in eintraege if e.person == person]
    if not person_eintraege:
        return None
    letzter = person_eintraege[0]
    return letzter.naechster_termin


# ── Übersicht ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def pflegeberatung_uebersicht(request: Request, person: str = ""):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    db = get_db(request)
    # Versicherte aus versicherte-Tabelle + personen aus Einträgen
    versicherte = []
    with db._schema.connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT person as name FROM pflege_eintraege WHERE owner_id=? ORDER BY person",
            (owner_id,)
        ).fetchall()
        versicherte = [dict(r) for r in rows]

    eintraege = _lade_eintraege(request, owner_id, person)

    return TEMPLATES.TemplateResponse(request, "pflegeberatung/index.html", {
        **base_ctx(request),
        "eintraege":    eintraege,
        "personen":     versicherte,
        "filter_person": person,
    })


# ── Neuer Eintrag ─────────────────────────────────────────────────────────────

@router.get("/neu", response_class=HTMLResponse)
async def pflegeberatung_neu(request: Request, person: str = ""):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    db = get_db(request)
    with db._schema.connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT person as name FROM pflege_eintraege WHERE owner_id=? ORDER BY person",
            (owner_id,)
        ).fetchall()
        personen = [dict(r) for r in rows]

    return TEMPLATES.TemplateResponse(request, "pflegeberatung/formular.html", {
        **base_ctx(request),
        "personen":      personen,
        "eintrag":       None,
        "person_vorwahl": person,
        "heute":         date.today().isoformat(),
    })


@router.post("/neu")
async def pflegeberatung_neu_post(
    request: Request,
    person:   str = Form(...),
    datum:    str = Form(...),
    berater:  str = Form(""),
    notiz:    str = Form(""),
    nachweis: UploadFile = File(None),
):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    db = get_db(request)

    datei_pfad = ""
    datei_name = ""

    if nachweis and nachweis.filename:
        inhalt = await nachweis.read()
        if len(inhalt) > MAX_DATEI_MB * 1024 * 1024:
            return redirect(request, "/pflegeberatung/neu?fehler=zu_gross", 303)
        d = _beratung_dir(request, owner_id)
        sicherer_name = f"{datum}_{nachweis.filename.replace(' ', '_')}"
        pfad = d / sicherer_name
        pfad.write_bytes(inhalt)
        datei_pfad = str(pfad)
        datei_name = nachweis.filename

    with db._schema.connect() as conn:
        conn.execute("""
            INSERT INTO pflegeberatung (owner_id, person, datum, berater, notiz, datei_pfad, datei_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (owner_id, person.strip(), datum, berater.strip(), notiz.strip(), datei_pfad, datei_name))

    return redirect(request, "/pflegeberatung/", 303)


# ── Nachweis herunterladen ────────────────────────────────────────────────────

@router.get("/{eintrag_id}/nachweis")
async def pflegeberatung_nachweis(request: Request, eintrag_id: int):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    eintrag = _lade_eintrag(request, owner_id, eintrag_id)

    if not eintrag or not eintrag.datei_pfad:
        return redirect(request, "/pflegeberatung/?fehler=kein_nachweis", 303)

    p = Path(eintrag.datei_pfad)
    if not p.exists():
        return redirect(request, "/pflegeberatung/?fehler=datei_nicht_gefunden", 303)

    return FileResponse(
        path=str(p),
        filename=eintrag.datei_name or p.name,
        media_type="application/octet-stream"
    )


# ── Löschen ───────────────────────────────────────────────────────────────────

@router.post("/{eintrag_id}/loeschen")
async def pflegeberatung_loeschen(request: Request, eintrag_id: int):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    eintrag = _lade_eintrag(request, owner_id, eintrag_id)

    if eintrag and eintrag.datei_pfad:
        try:
            Path(eintrag.datei_pfad).unlink(missing_ok=True)
        except Exception:
            pass

    db = get_db(request)
    with db._schema.connect() as conn:
        conn.execute("DELETE FROM pflegeberatung WHERE id=? AND owner_id=?", (eintrag_id, owner_id))

    return redirect(request, "/pflegeberatung/", 303)
