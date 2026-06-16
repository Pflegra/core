"""
Router: Dokumentenarchiv
Persönliches Archiv pro versicherter Person.
"""
from __future__ import annotations

import logging
from pathlib import Path
from datetime import date
from dataclasses import dataclass
from typing import Optional

from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse

from web.routers.deps import TEMPLATES, base_ctx, get_db, get_owner_id, redirect, audit_log
from db.audit import AuditEvent

log = logging.getLogger(__name__)

router = APIRouter(prefix="/dokumente", tags=["Dokumente"])

MAX_DATEI_MB = 50

KATEGORIEN = {
    "gutachten":      "📋 Gutachten",
    "pflegekasse":    "🏥 Pflegekasse",
    "pflegeberatung": "🤝 Pflegeberatung",
    "widerspruch":    "⚖️ Widerspruch",
    "arztbericht":    "🩺 Arztbericht",
    "antrag":         "📝 Antrag",
    "sonstiges":      "📁 Sonstiges",
}


@dataclass
class Dokument:
    id: int
    owner_id: int
    person: str
    kategorie: str
    titel: str
    datei_pfad: str
    datei_name: str
    datei_groesse: int
    notiz: str
    datum: str
    created_at: str

    @property
    def kategorie_label(self) -> str:
        return KATEGORIEN.get(self.kategorie, "📁 Sonstiges")

    @property
    def groesse_str(self) -> str:
        if self.datei_groesse < 1024:
            return f"{self.datei_groesse} B"
        elif self.datei_groesse < 1024 * 1024:
            return f"{self.datei_groesse / 1024:.1f} KB"
        else:
            return f"{self.datei_groesse / 1024 / 1024:.1f} MB"

    @property
    def datum_de(self) -> str:
        if self.datum and len(self.datum) == 10:
            return f"{self.datum[8:10]}.{self.datum[5:7]}.{self.datum[0:4]}"
        return self.datum


def _dok_dir(request: Request, owner_id: int) -> Path:
    data_dir = request.app.state.data_dir
    d = Path(data_dir) / "dokumente" / str(owner_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _lade_dokumente(request: Request, owner_id: int, person: str = "", kategorie: str = "") -> list[Dokument]:
    db = get_db(request)
    with db._schema.connect() as conn:
        if person and kategorie:
            rows = conn.execute(
                "SELECT * FROM dokumente WHERE owner_id=? AND person=? AND kategorie=? ORDER BY datum DESC, created_at DESC",
                (owner_id, person, kategorie)
            ).fetchall()
        elif person:
            rows = conn.execute(
                "SELECT * FROM dokumente WHERE owner_id=? AND person=? ORDER BY datum DESC, created_at DESC",
                (owner_id, person)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM dokumente WHERE owner_id=? ORDER BY datum DESC, created_at DESC",
                (owner_id,)
            ).fetchall()
    return [Dokument(**dict(r)) for r in rows]


def _lade_dokument(request: Request, owner_id: int, dok_id: int) -> Optional[Dokument]:
    db = get_db(request)
    with db._schema.connect() as conn:
        row = conn.execute(
            "SELECT * FROM dokumente WHERE id=? AND owner_id=?",
            (dok_id, owner_id)
        ).fetchone()
    if not row:
        return None
    return Dokument(**dict(row))


# ── Übersicht ─────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def dokumente_uebersicht(request: Request, person: str = "", kategorie: str = ""):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    db = get_db(request)

    with db._schema.connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT person FROM pflege_eintraege WHERE owner_id=? ORDER BY person",
            (owner_id,)
        ).fetchall()
        personen = [r["person"] for r in rows]

    dokumente = _lade_dokumente(request, owner_id, person, kategorie)

    # Gruppieren nach Kategorie
    nach_kategorie = {}
    for d in dokumente:
        k = d.kategorie
        if k not in nach_kategorie:
            nach_kategorie[k] = []
        nach_kategorie[k].append(d)

    return TEMPLATES.TemplateResponse(request, "dokumente/index.html", {
        **base_ctx(request),
        "dokumente":      dokumente,
        "nach_kategorie": nach_kategorie,
        "personen":       personen,
        "filter_person":  person,
        "filter_kat":     kategorie,
        "kategorien":     KATEGORIEN,
    })


# ── Upload ────────────────────────────────────────────────────────────────────

@router.get("/neu", response_class=HTMLResponse)
async def dokument_neu(request: Request, person: str = ""):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    db = get_db(request)

    with db._schema.connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT person FROM pflege_eintraege WHERE owner_id=? ORDER BY person",
            (owner_id,)
        ).fetchall()
        personen = [r["person"] for r in rows]

    return TEMPLATES.TemplateResponse(request, "dokumente/formular.html", {
        **base_ctx(request),
        "personen":      personen,
        "person_vorwahl": person,
        "kategorien":    KATEGORIEN,
        "heute":         date.today().isoformat(),
    })


@router.post("/neu")
async def dokument_neu_post(
    request:   Request,
    person:    str = Form(...),
    kategorie: str = Form("sonstiges"),
    titel:     str = Form(...),
    datum:     str = Form(""),
    notiz:     str = Form(""),
    datei:     UploadFile = File(...),
):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)

    if not datei or not datei.filename:
        return redirect(request, "/dokumente/neu?fehler=keine_datei", 303)

    inhalt = await datei.read()
    if len(inhalt) > MAX_DATEI_MB * 1024 * 1024:
        return redirect(request, "/dokumente/neu?fehler=zu_gross", 303)

    d = _dok_dir(request, owner_id)
    import uuid
    ext = Path(datei.filename).suffix
    datei_id = str(uuid.uuid4())[:8]
    sicherer_name = f"{datei_id}{ext}"
    pfad = d / sicherer_name
    pfad.write_bytes(inhalt)

    db = get_db(request)
    with db._schema.connect() as conn:
        conn.execute("""
            INSERT INTO dokumente (owner_id, person, kategorie, titel, datei_pfad, datei_name, datei_groesse, notiz, datum)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (owner_id, person.strip(), kategorie, titel.strip(), str(pfad), datei.filename, len(inhalt), notiz.strip(), datum))

    audit_log(request, AuditEvent.DOKUMENT_HOCHGELADEN,
              f"{titel.strip()} · {kategorie} · {person.strip()}")
    return redirect(request, f"/dokumente/?person={person}", 303)


# ── Download ──────────────────────────────────────────────────────────────────

@router.get("/{dok_id}/herunterladen")
async def dokument_herunterladen(request: Request, dok_id: int):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    dok = _lade_dokument(request, owner_id, dok_id)

    if not dok or not dok.datei_pfad:
        return redirect(request, "/dokumente/?fehler=nicht_gefunden", 303)

    p = Path(dok.datei_pfad)
    if not p.exists():
        return redirect(request, "/dokumente/?fehler=datei_fehlt", 303)

    return FileResponse(
        path=str(p),
        filename=dok.datei_name or p.name,
        media_type="application/octet-stream"
    )


# ── Löschen ───────────────────────────────────────────────────────────────────

@router.post("/{dok_id}/loeschen")
async def dokument_loeschen(request: Request, dok_id: int):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    dok = _lade_dokument(request, owner_id, dok_id)

    if dok and dok.datei_pfad:
        try:
            Path(dok.datei_pfad).unlink(missing_ok=True)
        except Exception:
            pass

    db = get_db(request)
    person = dok.person if dok else ""
    with db._schema.connect() as conn:
        conn.execute("DELETE FROM dokumente WHERE id=? AND owner_id=?", (dok_id, owner_id))

    audit_log(request, AuditEvent.DOKUMENT_GELOESCHT,
              f"{dok.titel if dok else dok_id} · {person}")
    return redirect(request, f"/dokumente/?person={person}", 303)
