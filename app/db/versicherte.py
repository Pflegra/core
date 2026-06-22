"""
db/versicherte.py — Versicherter Dataclass + VersicherterRepo
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from db.schema import DbSchema, require_owner_id


@dataclass
class Versicherter:
    """Die pflegebedürftige Person (Versicherter)."""
    name:               str
    adresse:            str = ""
    versicherungsnr:    str = ""
    krankenkasse:       str = ""
    krankenkasse_adresse: str = ""
    pflegegrad:         int = 0
    geburtsdatum:       str = ""
    mail:               str = ""
    notiz:              str = ""
    id: Optional[int]  = field(default=None, repr=False)
    owner_id: int      = field(default=1, repr=False)

    def __str__(self) -> str:
        pg = f" (PG{self.pflegegrad})" if self.pflegegrad else ""
        return f"{self.name}{pg}"


class VersicherterRepo:
    """CRUD für versicherte-Tabelle."""

    def __init__(self, schema: DbSchema) -> None:
        self._s = schema

    def _c(self):
        return self._s.connect()

    def laden(self, person_name: str, owner_id: int) -> Optional[Versicherter]:
        owner_id = require_owner_id(owner_id)
        with self._c() as conn:
            row = conn.execute("SELECT * FROM versicherte WHERE person_name=? AND owner_id=?", (person_name, owner_id)).fetchone()
        if not row:
            return None
        return Versicherter(
            name=row["person_name"],
            adresse=row["adresse"],
            versicherungsnr=row["versicherungsnr"],
            krankenkasse=row["krankenkasse"],
            krankenkasse_adresse=row["krankenkasse_adresse"] if "krankenkasse_adresse" in row.keys() else "",
            pflegegrad=row["pflegegrad"],
            geburtsdatum=row["geburtsdatum"] if "geburtsdatum" in row.keys() else "",
            mail=row["mail"] if "mail" in row.keys() else "",
            notiz=row["notiz"],
            id=row["id"],
            owner_id=row["owner_id"] if "owner_id" in row.keys() else 1,
        )

    def speichern(self, v: Versicherter) -> bool:
        v.owner_id = require_owner_id(v.owner_id)
        with self._c() as conn:
            conn.execute("""
                INSERT INTO versicherte (person_name,adresse,versicherungsnr,krankenkasse,krankenkasse_adresse,pflegegrad,geburtsdatum,mail,notiz,owner_id)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(person_name, owner_id) DO UPDATE SET
                    adresse=excluded.adresse, versicherungsnr=excluded.versicherungsnr,
                    krankenkasse=excluded.krankenkasse, krankenkasse_adresse=excluded.krankenkasse_adresse,
                    pflegegrad=excluded.pflegegrad, geburtsdatum=excluded.geburtsdatum,
                    mail=excluded.mail, notiz=excluded.notiz
            """, (v.name, v.adresse, v.versicherungsnr, v.krankenkasse,
                  v.krankenkasse_adresse, v.pflegegrad, v.geburtsdatum, v.mail, v.notiz,
                  v.owner_id))
        return True

    def loeschen(self, person_name: str, owner_id: int) -> bool:
        owner_id = require_owner_id(owner_id)
        with self._c() as conn:
            c = conn.execute("DELETE FROM versicherte WHERE person_name=? AND owner_id=?", (person_name, owner_id))
        return c.rowcount > 0
