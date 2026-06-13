"""
Router: Zeitachse / Jahresübersicht
Chronologische Übersicht aller Ereignisse pro versicherter Person.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from web.routers.deps import TEMPLATES, base_ctx, get_db, get_owner_id

log = logging.getLogger(__name__)

router = APIRouter(prefix="/zeitachse", tags=["Zeitachse"])

EREIGNIS_TYPEN = {
    "pflegeberatung": {"label": "Pflegeberatung",    "emoji": "🤝", "farbe": "#0891b2"},
    "gutachten":      {"label": "Gutachten-Analyse",  "emoji": "📋", "farbe": "#7c3aed"},
    "pflegegrad":     {"label": "Pflegegrad",          "emoji": "🏥", "farbe": "#dc2626"},
    "dokument":       {"label": "Dokument",            "emoji": "📄", "farbe": "#d97706"},
    "entlastung":     {"label": "Entlastungsbetrag",   "emoji": "💶", "farbe": "#16a34a"},
    "eintrag":        {"label": "Pflegeeinsatz",       "emoji": "🕐", "farbe": "#6b7280"},
    "frist":          {"label": "Frist",               "emoji": "⏰", "farbe": "#ea580c"},
}


@dataclass
class Ereignis:
    datum:   str        # ISO: 2026-06-13
    typ:     str        # key aus EREIGNIS_TYPEN
    titel:   str
    person:  str
    notiz:   str = ""
    link:    str = ""
    zukunft: bool = False

    @property
    def datum_de(self) -> str:
        if len(self.datum) == 10 and self.datum[4] == '-':
            return f"{self.datum[8:10]}.{self.datum[5:7]}.{self.datum[0:4]}"
        return self.datum

    @property
    def monat_jahr(self) -> str:
        try:
            if len(self.datum) >= 7 and self.datum[4] == '-':
                monate = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
                          "Juli", "August", "September", "Oktober", "November", "Dezember"]
                m = int(self.datum[5:7])
                y = self.datum[0:4]
                return f"{monate[m]} {y}"
        except Exception:
            pass
        return self.datum[:7] if len(self.datum) >= 7 else self.datum

    @property
    def info(self):
        return EREIGNIS_TYPEN.get(self.typ, {"label": self.typ, "emoji": "•", "farbe": "#6b7280"})


def _lade_ereignisse(request: Request, owner_id: int, person: str = "", jahr: int = 0) -> list[Ereignis]:
    db = get_db(request)
    ereignisse = []
    heute = date.today()
    jahr_filter = str(jahr) if jahr else None

    with db._schema.connect() as conn:

        # ── Pflegeberatungen ──────────────────────────────────────────────
        q = "SELECT * FROM pflegeberatung WHERE owner_id=?"
        params = [owner_id]
        if person:
            q += " AND person=?"
            params.append(person)
        if jahr_filter:
            q += " AND strftime('%Y', datum)=?"
            params.append(jahr_filter)
        for r in conn.execute(q, params).fetchall():
            ereignisse.append(Ereignis(
                datum=r["datum"],
                typ="pflegeberatung",
                titel=f"Pflegeberatung · {r['berater'] or 'Pflegedienst'}",
                person=r["person"],
                notiz=r["notiz"] or "",
                link="/pflegeberatung/",
            ))
            # Nächster Termin als Zukunfts-Ereignis
            try:
                from datetime import timedelta
                d = date.fromisoformat(r["datum"])
                naechster = d + timedelta(days=183)
                if naechster >= heute:
                    if not jahr_filter or naechster.strftime("%Y") == jahr_filter:
                        ereignisse.append(Ereignis(
                            datum=naechster.isoformat(),
                            typ="frist",
                            titel="Pflegeberatung fällig",
                            person=r["person"],
                            notiz="Halbjährlicher Pflichtnachweis § 37.3 SGB XI",
                            link="/pflegeberatung/neu",
                            zukunft=True,
                        ))
            except Exception:
                pass

        # ── Pflegegrad-Verlauf ────────────────────────────────────────────
        q = "SELECT * FROM pflegegrad_verlauf WHERE owner_id=?"
        params = [owner_id]
        if person:
            q += " AND person=?"
            params.append(person)
        if jahr_filter:
            q += " AND strftime('%Y', datum)=?"
            params.append(jahr_filter)
        for r in conn.execute(q, params).fetchall():
            ereignisse.append(Ereignis(
                datum=r["datum"],
                typ="pflegegrad",
                titel=f"Pflegegrad {r['pflegegrad']} · {r['gesamtpunkte']} Punkte",
                person=r["person"],
                notiz=r["notiz"] or "",
                link="/pflegegrad/verlauf",
            ))

        # ── Dokumente ─────────────────────────────────────────────────────
        q = "SELECT * FROM dokumente WHERE owner_id=?"
        params = [owner_id]
        if person:
            q += " AND person=?"
            params.append(person)
        if jahr_filter:
            q += " AND (strftime('%Y', datum)=? OR (datum='' AND strftime('%Y', created_at)=?))"
            params.extend([jahr_filter, jahr_filter])
        for r in conn.execute(q, params).fetchall():
            d = r["datum"] or r["created_at"][:10]
            ereignisse.append(Ereignis(
                datum=d,
                typ="dokument",
                titel=r["titel"],
                person=r["person"],
                notiz=r["notiz"] or "",
                link="/dokumente/",
            ))

        # ── Entlastungsbuchungen (nur Monatsweise zusammenfassen) ─────────
        q = """
            SELECT person, strftime('%Y-%m', datum) as ym,
                   strftime('%Y-%m-01', datum) as d,
                   SUM(betrag) as summe, COUNT(*) as anz
            FROM entlastung_buchungen WHERE owner_id=?
        """
        params = [owner_id]
        if person:
            q += " AND person=?"
            params.append(person)
        if jahr_filter:
            q += " AND strftime('%Y', datum)=?"
            params.append(jahr_filter)
        q += " GROUP BY person, ym ORDER BY ym"
        for r in conn.execute(q, params).fetchall():
            ereignisse.append(Ereignis(
                datum=r["d"],
                typ="entlastung",
                titel=f"Entlastungsbetrag · {r['summe']:.0f} € ({r['anz']} Buchungen)",
                person=r["person"],
                link="/entlastung/",
            ))

    # ── Gutachten-Analysen (aus JSON-Dateien) ─────────────────────────────
    try:
        data_dir = request.app.state.data_dir
        gut_dir = Path(data_dir) / "gutachten" / str(owner_id)
        if gut_dir.exists():
            for f in sorted(gut_dir.glob("*.json")):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    d = data.get("erstellt_am", "")[:10]
                    if not d:
                        continue
                    if person and data.get("person", "") != person:
                        continue
                    if jahr_filter and d[:4] != jahr_filter:
                        continue
                    pg = data.get("pflegegrad", "")
                    ereignisse.append(Ereignis(
                        datum=d,
                        typ="gutachten",
                        titel=f"Gutachten-Analyse · PG {pg}" if pg else "Gutachten-Analyse",
                        person=data.get("person", ""),
                        notiz=f"{data.get('gesamtpunkte', '')} Punkte" if data.get("gesamtpunkte") else "",
                        link="/gutachten/",
                    ))
                except Exception:
                    pass
    except Exception:
        pass

    # Sortieren: neueste zuerst, Zukunft oben
    ereignisse.sort(key=lambda e: (0 if e.zukunft else 1, e.datum), reverse=False)
    ereignisse.sort(key=lambda e: e.datum, reverse=True)
    # Zukunft ganz oben
    zukunft = [e for e in ereignisse if e.zukunft]
    vergangenheit = [e for e in ereignisse if not e.zukunft]
    return zukunft + vergangenheit


@router.get("/", response_class=HTMLResponse)
async def zeitachse(request: Request, person: str = "", jahr: str = ""):
    from web.auth import login_erforderlich
    guard = login_erforderlich(request)
    if guard:
        return guard

    owner_id = get_owner_id(request)
    db = get_db(request)

    # Personen laden
    with db._schema.connect() as conn:
        rows = conn.execute(
            "SELECT DISTINCT person FROM pflege_eintraege WHERE owner_id=? ORDER BY person",
            (owner_id,)
        ).fetchall()
        personen = [r["person"] for r in rows]

    # Verfügbare Jahre
    with db._schema.connect() as conn:
        jahre_raw = set()
        for tbl, col in [("pflegeberatung", "datum"), ("pflegegrad_verlauf", "datum"),
                          ("dokumente", "datum"), ("entlastung_buchungen", "datum")]:
            try:
                for r in conn.execute(
                    f"SELECT DISTINCT strftime('%Y', {col}) as y FROM {tbl} WHERE owner_id=? AND {col}!=''",
                    (owner_id,)
                ).fetchall():
                    if r["y"]:
                        jahre_raw.add(r["y"])
            except Exception:
                pass
        jahre = sorted(jahre_raw, reverse=True)

    jahr_int = int(jahr) if jahr.isdigit() else 0
    ereignisse = _lade_ereignisse(request, owner_id, person, jahr_int)

    # Nach Monat gruppieren
    nach_monat: dict[str, list] = {}
    for e in ereignisse:
        key = e.monat_jahr
        if key not in nach_monat:
            nach_monat[key] = []
        nach_monat[key].append(e)

    return TEMPLATES.TemplateResponse(request, "zeitachse/index.html", {
        **base_ctx(request),
        "ereignisse":    ereignisse,
        "nach_monat":   nach_monat,
        "personen":      personen,
        "jahre":         jahre,
        "filter_person": person,
        "filter_jahr":   jahr,
        "ereignis_typen": EREIGNIS_TYPEN,
    })
