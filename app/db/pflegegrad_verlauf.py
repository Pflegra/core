"""
db/pflegegrad_verlauf.py — Verlauf von Pflegegrad-Einschätzungen
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional

from db.schema import DbSchema


@dataclass
class PflegegradEintrag:
    id:             Optional[int]
    owner_id:       int
    person:         str
    datum:          str    # ISO-Format YYYY-MM-DD
    pflegegrad:     int
    gesamtpunkte:   float
    notiz:          str = ""
    antworten_json: str = ""   # gespeicherte Antworten für spätere Auswertung
    created_at:     str = ""

    @classmethod
    def from_row(cls, r) -> "PflegegradEintrag":
        return cls(
            id=r["id"], owner_id=r["owner_id"], person=r["person"],
            datum=r["datum"], pflegegrad=r["pflegegrad"],
            gesamtpunkte=r["gesamtpunkte"], notiz=r["notiz"],
            antworten_json=r["antworten_json"], created_at=r["created_at"],
        )

    def antworten(self) -> dict:
        try:
            return json.loads(self.antworten_json) if self.antworten_json else {}
        except Exception:
            return {}


class PflegegradVerlaufRepo:
    """CRUD für pflegegrad_verlauf-Tabelle."""

    def __init__(self, schema: DbSchema) -> None:
        self._s = schema

    def _c(self):
        return self._s.connect()

    def speichern(self, eintrag: PflegegradEintrag) -> int:
        with self._c() as conn:
            cur = conn.execute("""
                INSERT INTO pflegegrad_verlauf
                    (owner_id, person, datum, pflegegrad, gesamtpunkte, notiz, antworten_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                eintrag.owner_id, eintrag.person, eintrag.datum,
                eintrag.pflegegrad, eintrag.gesamtpunkte,
                eintrag.notiz, eintrag.antworten_json,
            ))
        return cur.lastrowid

    def alle(self, owner_id: int, person: str = "") -> List[PflegegradEintrag]:
        with self._c() as conn:
            if person:
                rows = conn.execute("""
                    SELECT * FROM pflegegrad_verlauf
                    WHERE owner_id=? AND person=?
                    ORDER BY datum DESC, created_at DESC
                """, (owner_id, person)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM pflegegrad_verlauf
                    WHERE owner_id=?
                    ORDER BY datum DESC, created_at DESC
                """, (owner_id,)).fetchall()
        return [PflegegradEintrag.from_row(r) for r in rows]

    def loeschen(self, eintrag_id: int, owner_id: int) -> bool:
        with self._c() as conn:
            cur = conn.execute(
                "DELETE FROM pflegegrad_verlauf WHERE id=? AND owner_id=?",
                (eintrag_id, owner_id)
            )
        return cur.rowcount > 0

    def personen(self, owner_id: int) -> List[str]:
        with self._c() as conn:
            rows = conn.execute("""
                SELECT DISTINCT person FROM pflegegrad_verlauf
                WHERE owner_id=? ORDER BY person
            """, (owner_id,)).fetchall()
        return [r["person"] for r in rows]
