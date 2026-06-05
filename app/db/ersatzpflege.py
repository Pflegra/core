"""
db/ersatzpflege.py — Ersatzpflegekraft Dataclass + ErsatzRepo
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from db.schema import DbSchema


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

    def alle(self, person: str, owner_id: int = 0) -> List[Ersatzpflegekraft]:
        with self._c() as conn:
            if owner_id:
                rows = conn.execute(
                    "SELECT * FROM ersatzpflegekraefte WHERE person=? AND owner_id=? ORDER BY name",
                    (person, owner_id)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM ersatzpflegekraefte WHERE person=? ORDER BY name",
                    (person,)
                ).fetchall()
        return [Ersatzpflegekraft.from_row(r) for r in rows]

    def speichern(self, e: Ersatzpflegekraft) -> None:
        with self._c() as conn:
            if e.id:
                conn.execute("""
                    UPDATE ersatzpflegekraefte
                    SET name=?, geburtsdatum=?, adresse=?, art=?, notiz=?
                    WHERE id=? AND person=?
                """, (e.name, e.geburtsdatum, e.adresse, e.art, e.notiz, e.id, e.person))
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

    def loeschen(self, ersatz_id: int, person: str) -> bool:
        with self._c() as conn:
            cur = conn.execute(
                "DELETE FROM ersatzpflegekraefte WHERE id=? AND person=?",
                (ersatz_id, person)
            )
        return cur.rowcount > 0

    def laden(self, ersatz_id: int) -> Optional[Ersatzpflegekraft]:
        with self._c() as conn:
            row = conn.execute(
                "SELECT * FROM ersatzpflegekraefte WHERE id=?", (ersatz_id,)
            ).fetchone()
        return Ersatzpflegekraft.from_row(row) if row else None

    def letzten_fuer_person(self, person: str) -> Optional[Ersatzpflegekraft]:
        with self._c() as conn:
            row = conn.execute("""
                SELECT e.* FROM ersatzpflegekraefte e
                INNER JOIN pflege_eintraege p ON p.ersatz_name = e.name AND p.person = e.person
                WHERE e.person = ?
                ORDER BY p.datum DESC, p.von DESC
                LIMIT 1
            """, (person,)).fetchone()
        return Ersatzpflegekraft.from_row(row) if row else None
