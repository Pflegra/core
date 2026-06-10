"""
Pflegra – Entlastungsbetrag Datenschicht (§ 45b SGB XI)
EntlastungBuchung Dataclass + EntlastungRepo CRUD
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List


@dataclass
class EntlastungBuchung:
    id:           int   = 0
    owner_id:     int   = 1
    person:       str   = ""
    datum:        str   = ""
    betrag:       float = 0.0
    anbieter:     str   = ""
    beschreibung: str   = ""
    beleg_nr:     str   = ""
    created_at:   str   = ""

    @classmethod
    def from_row(cls, r) -> "EntlastungBuchung":
        keys = r.keys()
        return cls(
            id=r["id"], owner_id=r["owner_id"], person=r["person"],
            datum=r["datum"], betrag=r["betrag"], anbieter=r["anbieter"],
            beschreibung=r["beschreibung"], beleg_nr=r["beleg_nr"],
            created_at=r["created_at"] if "created_at" in keys else "",
        )


class EntlastungRepo:
    """CRUD für entlastung_buchungen-Tabelle."""

    def __init__(self, schema) -> None:
        self._s = schema

    def _c(self):
        return self._s.connect()

    def alle(self, person: str, owner_id: int, jahr: int = None) -> List[EntlastungBuchung]:
        with self._c() as conn:
            if jahr:
                rows = conn.execute("""
                    SELECT * FROM entlastung_buchungen
                    WHERE person=? AND owner_id=? AND substr(datum,1,4)=?
                    ORDER BY datum DESC
                """, (person, owner_id, str(jahr))).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM entlastung_buchungen
                    WHERE person=? AND owner_id=?
                    ORDER BY datum DESC
                """, (person, owner_id)).fetchall()
        return [EntlastungBuchung.from_row(r) for r in rows]

    def speichern(self, b: EntlastungBuchung) -> None:
        with self._c() as conn:
            if b.id:
                conn.execute("""
                    UPDATE entlastung_buchungen
                    SET datum=?, betrag=?, anbieter=?, beschreibung=?, beleg_nr=?
                    WHERE id=? AND owner_id=?
                """, (b.datum, b.betrag, b.anbieter, b.beschreibung, b.beleg_nr, b.id, b.owner_id))
            else:
                conn.execute("""
                    INSERT INTO entlastung_buchungen
                        (owner_id, person, datum, betrag, anbieter, beschreibung, beleg_nr)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (b.owner_id, b.person, b.datum, b.betrag, b.anbieter, b.beschreibung, b.beleg_nr))

    def loeschen(self, buchung_id: int, owner_id: int) -> bool:
        with self._c() as conn:
            cur = conn.execute(
                "DELETE FROM entlastung_buchungen WHERE id=? AND owner_id=?",
                (buchung_id, owner_id)
            )
        return cur.rowcount > 0

    def summe(self, person: str, owner_id: int, jahr: int, monat: int = None) -> float:
        with self._c() as conn:
            if monat:
                row = conn.execute("""
                    SELECT COALESCE(SUM(betrag), 0) as s FROM entlastung_buchungen
                    WHERE person=? AND owner_id=?
                    AND substr(datum,1,4)=? AND substr(datum,6,2)=?
                """, (person, owner_id, str(jahr), f"{monat:02d}")).fetchone()
            else:
                row = conn.execute("""
                    SELECT COALESCE(SUM(betrag), 0) as s FROM entlastung_buchungen
                    WHERE person=? AND owner_id=? AND substr(datum,1,4)=?
                """, (person, owner_id, str(jahr))).fetchone()
        return float(row["s"]) if row else 0.0
