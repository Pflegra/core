"""
db/eintraege.py — PflegeEintrag Dataclass + EintragsRepo
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from db.schema import DbSchema

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

ART_STUNDENWEISE = "stundenweise"
ART_TAGEWEISE    = "tageweise"
PFLEGE_ARTEN     = [ART_STUNDENWEISE, ART_TAGEWEISE]

GRUND_URLAUB    = "Erholungsurlaub"
GRUND_KRANKHEIT = "Krankheit"
GRUND_SONSTIGES = "Sonstiges"
PFLEGE_GRUENDE  = [GRUND_URLAUB, GRUND_KRANKHEIT, GRUND_SONSTIGES]

ERSATZ_PRIVAT = "Privatperson"
ERSATZ_DIENST = "Pflegedienst"
ERSATZ_ARTEN  = [ERSATZ_PRIVAT, ERSATZ_DIENST]


@dataclass
class PflegeEintrag:
    """Ein einzelner Verhinderungspflege-Nachweis-Eintrag."""

    datum: date
    von: str
    bis: str
    stunden: float
    person: str
    art:             str = ART_STUNDENWEISE
    grund:           str = GRUND_URLAUB
    ersatz_name:     str = ""
    ersatz_art:      str = ERSATZ_PRIVAT
    ersatz_adresse:  str = ""
    notiz:           str = ""
    id: Optional[int] = field(default=None, repr=False)
    owner_id: int = field(default=1, repr=False)

    @property
    def monat(self) -> int:
        return self.datum.month

    @property
    def jahr(self) -> int:
        return self.datum.year

    @property
    def wochentag(self) -> str:
        return WOCHENTAGE[self.datum.weekday()]

    @classmethod
    def from_datum(cls, datum, von, bis, stunden, person,
                   art=ART_STUNDENWEISE, grund=GRUND_URLAUB,
                   ersatz_name="", ersatz_art=ERSATZ_PRIVAT,
                   ersatz_adresse="", notiz="") -> "PflegeEintrag":
        return cls(datum=datum, von=von, bis=bis, stunden=stunden, person=person,
                   art=art, grund=grund, ersatz_name=ersatz_name,
                   ersatz_art=ersatz_art, ersatz_adresse=ersatz_adresse, notiz=notiz)

    @classmethod
    def from_dict(cls, d: dict) -> "PflegeEintrag":
        datum = d["datum"]
        if isinstance(datum, str):
            datum = datetime.strptime(datum, "%Y-%m-%d").date()
        return cls(
            datum=datum,
            von=str(d["von"]),
            bis=str(d["bis"]),
            stunden=float(str(d["stunden"]).replace(",", ".")),
            person=str(d["person"]).strip(),
            art=str(d.get("art") or ART_STUNDENWEISE),
            grund=str(d.get("grund") or GRUND_URLAUB),
            ersatz_name=str(d.get("ersatz_name") or ""),
            ersatz_art=str(d.get("ersatz_art") or ERSATZ_PRIVAT),
            ersatz_adresse=str(d.get("ersatz_adresse") or ""),
            notiz=str(d.get("notiz") or ""),
            id=d.get("id"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id, "datum": self.datum.isoformat(),
            "monat": self.monat, "jahr": self.jahr,
            "von": self.von, "bis": self.bis, "stunden": self.stunden,
            "person": self.person, "wochentag": self.wochentag,
            "art": self.art, "grund": self.grund,
            "ersatz_name": self.ersatz_name, "ersatz_art": self.ersatz_art,
            "ersatz_adresse": self.ersatz_adresse, "notiz": self.notiz,
        }

    def archiv_pfad(self, basis: Path = Path("Archiv")) -> Path:
        return basis / str(self.jahr) / self.person

    def __str__(self) -> str:
        return (f"{self.wochentag}, {self.datum.isoformat()} | "
                f"{self.von}–{self.bis} ({self.stunden}h) | {self.person}")


def _row_to_eintrag(row) -> PflegeEintrag:
    d = dict(row)
    d["datum"] = datetime.strptime(d["datum"], "%Y-%m-%d").date()
    d.pop("monat", None)
    d.pop("jahr", None)
    d.pop("wochentag", None)
    if "owner_id" not in d:
        d["owner_id"] = 1
    return PflegeEintrag(**d)


class EintragsRepo:
    """CRUD für pflege_eintraege."""

    def __init__(self, schema: DbSchema) -> None:
        self._s = schema

    def _c(self):
        return self._s.connect()

    def insert(self, e: PflegeEintrag) -> PflegeEintrag:
        with self._c() as conn:
            conn.execute("INSERT OR IGNORE INTO personen (name, owner_id) VALUES (?, ?)", (e.person, e.owner_id))
            cur = conn.execute(
                "INSERT INTO pflege_eintraege (datum,monat,jahr,von,bis,stunden,person,wochentag,art,grund,ersatz_name,ersatz_art,ersatz_adresse,notiz,owner_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (e.datum.isoformat(), e.monat, e.jahr, e.von, e.bis, e.stunden, e.person, e.wochentag, e.art, e.grund, e.ersatz_name, e.ersatz_art, e.ersatz_adresse, e.notiz, e.owner_id),
            )
            e.id = cur.lastrowid
        return e

    def insert_many(self, eintraege) -> list:
        with self._c() as conn:
            for name in {x.person for x in eintraege if x.person}:
                conn.execute("INSERT OR IGNORE INTO personen (name) VALUES (?)", (name,))
            for e in eintraege:
                cur = conn.execute(
                    "INSERT INTO pflege_eintraege (datum,monat,jahr,von,bis,stunden,person,wochentag,art,grund,ersatz_name,ersatz_art,ersatz_adresse,notiz) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (e.datum.isoformat(), e.monat, e.jahr, e.von, e.bis, e.stunden, e.person, e.wochentag, e.art, e.grund, e.ersatz_name, e.ersatz_art, e.ersatz_adresse, e.notiz),
                )
                e.id = cur.lastrowid
        return eintraege

    def alle(self, owner_id: int = 0) -> list:
        with self._c() as conn:
            if owner_id:
                rows = conn.execute("SELECT * FROM pflege_eintraege WHERE owner_id=? ORDER BY datum, von", (owner_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM pflege_eintraege ORDER BY datum, von").fetchall()
        return [_row_to_eintrag(r) for r in rows]

    def nach_person_und_jahr(self, person, jahr, owner_id: int = 0) -> list:
        with self._c() as conn:
            if owner_id:
                rows = conn.execute("SELECT * FROM pflege_eintraege WHERE person=? AND jahr=? AND owner_id=? ORDER BY datum,von", (person, jahr, owner_id)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM pflege_eintraege WHERE person=? AND jahr=? ORDER BY datum,von", (person, jahr)).fetchall()
        return [_row_to_eintrag(r) for r in rows]

    def nach_monat(self, person, jahr, monat, owner_id: int = 0) -> list:
        with self._c() as conn:
            if owner_id:
                rows = conn.execute("SELECT * FROM pflege_eintraege WHERE person=? AND jahr=? AND monat=? AND owner_id=? ORDER BY datum,von", (person, jahr, monat, owner_id)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM pflege_eintraege WHERE person=? AND jahr=? AND monat=? ORDER BY datum,von", (person, jahr, monat)).fetchall()
        return [_row_to_eintrag(r) for r in rows]

    def jahre(self, owner_id: int = 0) -> list:
        with self._c() as conn:
            if owner_id:
                rows = conn.execute("SELECT DISTINCT jahr FROM pflege_eintraege WHERE owner_id=? ORDER BY jahr", (owner_id,)).fetchall()
            else:
                rows = conn.execute("SELECT DISTINCT jahr FROM pflege_eintraege ORDER BY jahr").fetchall()
        return [r["jahr"] for r in rows]

    def update(self, e: PflegeEintrag) -> bool:
        with self._c() as conn:
            cur = conn.execute(
                "UPDATE pflege_eintraege SET datum=?,monat=?,jahr=?,von=?,bis=?,stunden=?,person=?,wochentag=?,art=?,grund=?,ersatz_name=?,ersatz_art=?,ersatz_adresse=?,notiz=? WHERE id=?",
                (e.datum.isoformat(), e.monat, e.jahr, e.von, e.bis, e.stunden, e.person, e.wochentag, e.art, e.grund, e.ersatz_name, e.ersatz_art, e.ersatz_adresse, e.notiz, e.id),
            )
        return cur.rowcount > 0

    def loeschen(self, eintrag_id: int) -> bool:
        with self._c() as conn:
            cur = conn.execute("DELETE FROM pflege_eintraege WHERE id=?", (eintrag_id,))
        return cur.rowcount > 0

    def bulk_loeschen(self, ids: list) -> int:
        if not ids:
            return 0
        platzhalter = ",".join("?" * len(ids))
        with self._c() as conn:
            cur = conn.execute(f"DELETE FROM pflege_eintraege WHERE id IN ({platzhalter})", ids)
        return cur.rowcount

    def duplikate_finden(self) -> list:
        alle = self.alle()
        gruppen: dict = {}
        for e in alle:
            key = (e.person, str(e.datum), e.von, e.bis)
            gruppen.setdefault(key, []).append(e)
        return [g for g in gruppen.values() if len(g) > 1]

    def suche(self, suchbegriff: str) -> list:
        like = f"%{suchbegriff}%"
        with self._c() as conn:
            rows = conn.execute("""
                SELECT * FROM pflege_eintraege
                WHERE person LIKE ?
                   OR datum LIKE ?
                   OR wochentag LIKE ?
                   OR notiz LIKE ?
                   OR art LIKE ?
                   OR grund LIKE ?
                   OR ersatz_name LIKE ?
                ORDER BY datum DESC, von
            """, (like, like, like, like, like, like, like)).fetchall()
        return [_row_to_eintrag(r) for r in rows]

    def statistik(self, owner_id: int = 0) -> dict:
        with self._c() as conn:
            if owner_id:
                g = conn.execute("SELECT COUNT(*) as n, SUM(stunden) as h FROM pflege_eintraege WHERE owner_id=?", (owner_id,)).fetchone()
                p = conn.execute("SELECT COUNT(DISTINCT person) as n FROM pflege_eintraege WHERE owner_id=?", (owner_id,)).fetchone()
                j = conn.execute("SELECT COUNT(DISTINCT jahr) as n FROM pflege_eintraege WHERE owner_id=?", (owner_id,)).fetchone()
            else:
                g = conn.execute("SELECT COUNT(*) as n, SUM(stunden) as h FROM pflege_eintraege").fetchone()
                p = conn.execute("SELECT COUNT(DISTINCT person) as n FROM pflege_eintraege").fetchone()
                j = conn.execute("SELECT COUNT(DISTINCT jahr) as n FROM pflege_eintraege").fetchone()
        return {"eintraege_gesamt": g["n"] or 0, "stunden_gesamt": round(g["h"] or 0, 2),
                "personen_anzahl": p["n"] or 0, "jahre_anzahl": j["n"] or 0}
