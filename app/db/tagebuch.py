"""
db/tagebuch.py — Pflegetagebuch Einträge
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from db.schema import DbSchema

KATEGORIEN = [
    "allgemein",
    "koerperpflege",
    "ernaehrung",
    "medikamente",
    "mobilitaet",
    "stimmung",
    "arzt",
    "vorfall",
    "soziales",
]

KATEGORIEN_LABELS = {
    "allgemein":    "Allgemein",
    "koerperpflege": "Körperpflege",
    "ernaehrung":   "Ernährung",
    "medikamente":  "Medikamente",
    "mobilitaet":   "Mobilität",
    "stimmung":     "Stimmung / Verhalten",
    "arzt":         "Arzt / Termin",
    "vorfall":      "Vorfall / Besonderheit",
    "soziales":     "Soziale Kontakte",
}

STIMMUNG_LABELS = {
    1: "😔 Sehr schlecht",
    2: "😟 Schlecht",
    3: "😐 Mittel",
    4: "🙂 Gut",
    5: "😊 Sehr gut",
}


@dataclass
class TagebuchEintrag:
    id:          Optional[int]
    owner_id:    int
    person:      str
    datum:       str
    uhrzeit:     str = ""
    kategorie:   str = "allgemein"
    titel:       str = ""
    inhalt:      str = ""
    stimmung:    Optional[int] = None
    tags:        str = ""
    created_at:  str = ""

    @classmethod
    def from_row(cls, r) -> "TagebuchEintrag":
        return cls(
            id=r["id"], owner_id=r["owner_id"], person=r["person"],
            datum=r["datum"], uhrzeit=r["uhrzeit"], kategorie=r["kategorie"],
            titel=r["titel"], inhalt=r["inhalt"],
            stimmung=r["stimmung"], tags=r["tags"],
            created_at=r["created_at"],
        )

    @property
    def kategorie_label(self) -> str:
        return KATEGORIEN_LABELS.get(self.kategorie, self.kategorie)

    @property
    def stimmung_label(self) -> str:
        return STIMMUNG_LABELS.get(self.stimmung, "") if self.stimmung else ""

    @property
    def tags_liste(self) -> List[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]


class TagebuchRepo:
    """CRUD für pflegetagebuch-Tabelle."""

    def __init__(self, schema: DbSchema) -> None:
        self._s = schema

    def _c(self):
        return self._s.connect()

    def speichern(self, e: TagebuchEintrag) -> int:
        with self._c() as conn:
            if e.id:
                conn.execute("""
                    UPDATE pflegetagebuch
                    SET datum=?, uhrzeit=?, kategorie=?, titel=?, inhalt=?,
                        stimmung=?, tags=?
                    WHERE id=? AND owner_id=?
                """, (e.datum, e.uhrzeit, e.kategorie, e.titel, e.inhalt,
                      e.stimmung, e.tags, e.id, e.owner_id))
                return e.id
            else:
                cur = conn.execute("""
                    INSERT INTO pflegetagebuch
                        (owner_id, person, datum, uhrzeit, kategorie, titel, inhalt, stimmung, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (e.owner_id, e.person, e.datum, e.uhrzeit, e.kategorie,
                      e.titel, e.inhalt, e.stimmung, e.tags))
                return cur.lastrowid

    def alle(self, owner_id: int, person: str = "", kategorie: str = "",
             limit: int = 0) -> List[TagebuchEintrag]:
        sql = "SELECT * FROM pflegetagebuch WHERE owner_id=?"
        params = [owner_id]
        if person:
            sql += " AND person=?"
            params.append(person)
        if kategorie:
            sql += " AND kategorie=?"
            params.append(kategorie)
        sql += " ORDER BY datum DESC, uhrzeit DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        with self._c() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [TagebuchEintrag.from_row(r) for r in rows]

    def laden(self, eintrag_id: int, owner_id: int) -> Optional[TagebuchEintrag]:
        with self._c() as conn:
            row = conn.execute(
                "SELECT * FROM pflegetagebuch WHERE id=? AND owner_id=?",
                (eintrag_id, owner_id)
            ).fetchone()
        return TagebuchEintrag.from_row(row) if row else None

    def loeschen(self, eintrag_id: int, owner_id: int) -> bool:
        with self._c() as conn:
            cur = conn.execute(
                "DELETE FROM pflegetagebuch WHERE id=? AND owner_id=?",
                (eintrag_id, owner_id)
            )
        return cur.rowcount > 0

    def personen(self, owner_id: int) -> List[str]:
        with self._c() as conn:
            rows = conn.execute(
                "SELECT DISTINCT person FROM pflegetagebuch WHERE owner_id=? ORDER BY person",
                (owner_id,)
            ).fetchall()
        return [r["person"] for r in rows]

    def statistik(self, owner_id: int, person: str = "") -> dict:
        sql_base = "FROM pflegetagebuch WHERE owner_id=?"
        params = [owner_id]
        if person:
            sql_base += " AND person=?"
            params.append(person)
        with self._c() as conn:
            gesamt = conn.execute(f"SELECT COUNT(*) {sql_base}", params).fetchone()[0]
            avg_stimmung = conn.execute(
                f"SELECT AVG(stimmung) {sql_base} AND stimmung IS NOT NULL", params
            ).fetchone()[0]
            letzter = conn.execute(
                f"SELECT datum {sql_base} ORDER BY datum DESC LIMIT 1", params
            ).fetchone()
        return {
            "gesamt": gesamt,
            "avg_stimmung": round(avg_stimmung, 1) if avg_stimmung else None,
            "letzter_eintrag": letzter["datum"] if letzter else None,
        }
