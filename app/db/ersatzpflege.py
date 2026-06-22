"""
db/ersatzpflege.py — Ersatzpflegekraft Dataclass + ErsatzRepo
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from db.schema import DbSchema, require_owner_id


@dataclass
class Ersatzpflegekraft:
    """Eine gespeicherte Ersatz-/Verhinderungspflegekraft."""
    id:           int  = 0
    person:       str  = ""
    name:         str  = ""
    geburtsdatum: str  = ""
    adresse:      str  = ""
    art:          str  = "Privatperson"
    notiz:        str  = ""
    owner_id:     int  = 1

    @classmethod
    def from_row(cls, r) -> "Ersatzpflegekraft":
        return cls(
            id=r["id"], person=r["person"], name=r["name"],
            geburtsdatum=r["geburtsdatum"], adresse=r["adresse"],
            art=r["art"], notiz=r["notiz"],
            owner_id=r["owner_id"] if "owner_id" in r.keys() else 1,
        )


class ErsatzRepo:
    """CRUD für ersatzpflegekraefte-Tabelle."""

    def __init__(self, schema: DbSchema) -> None:
        self._s = schema

    def _c(self):
        return self._s.connect()

    def alle(self, person: str, owner_id: int) -> List[Ersatzpflegekraft]:
        owner_id = require_owner_id(owner_id)
        with self._c() as conn:
            rows = conn.execute(
                "SELECT * FROM ersatzpflegekraefte WHERE person=? AND owner_id=? ORDER BY name",
                (person, owner_id)
            ).fetchall()
        return [Ersatzpflegekraft.from_row(r) for r in rows]

    def speichern(self, e: Ersatzpflegekraft) -> None:
        e.owner_id = require_owner_id(e.owner_id)
        with self._c() as conn:
            if e.id:
                conn.execute("""
                    UPDATE ersatzpflegekraefte
                    SET name=?, geburtsdatum=?, adresse=?, art=?, notiz=?
                    WHERE id=? AND person=? AND owner_id=?
                """, (e.name, e.geburtsdatum, e.adresse, e.art, e.notiz, e.id, e.person, e.owner_id))
            else:
                conn.execute("""
                    INSERT INTO ersatzpflegekraefte (person, name, geburtsdatum, adresse, art, notiz, owner_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(person, name, owner_id) DO UPDATE SET
                        geburtsdatum=excluded.geburtsdatum,
                        adresse=excluded.adresse,
                        art=excluded.art,
                        notiz=excluded.notiz
                """, (e.person, e.name, e.geburtsdatum, e.adresse, e.art, e.notiz, e.owner_id))

    def loeschen(self, ersatz_id: int, person: str, owner_id: int) -> bool:
        owner_id = require_owner_id(owner_id)
        with self._c() as conn:
            cur = conn.execute(
                "DELETE FROM ersatzpflegekraefte WHERE id=? AND person=? AND owner_id=?",
                (ersatz_id, person, owner_id)
            )
        return cur.rowcount > 0

    def laden(self, ersatz_id: int, owner_id: int) -> Optional[Ersatzpflegekraft]:
        owner_id = require_owner_id(owner_id)
        with self._c() as conn:
            row = conn.execute(
                "SELECT * FROM ersatzpflegekraefte WHERE id=? AND owner_id=?", (ersatz_id, owner_id)
            ).fetchone()
        return Ersatzpflegekraft.from_row(row) if row else None

    def letzten_fuer_person(self, person: str, owner_id: int) -> Optional[Ersatzpflegekraft]:
        owner_id = require_owner_id(owner_id)
        with self._c() as conn:
            row = conn.execute("""
                SELECT e.* FROM ersatzpflegekraefte e
                INNER JOIN pflege_eintraege p
                    ON p.ersatz_name = e.name
                    AND p.person = e.person
                    AND p.owner_id = e.owner_id
                WHERE e.person = ? AND e.owner_id = ?
                ORDER BY p.datum DESC, p.von DESC
                LIMIT 1
            """, (person, owner_id)).fetchone()
        return Ersatzpflegekraft.from_row(row) if row else None
