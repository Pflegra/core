"""
db/settings.py — UserSettings Dataclass + UserSettingsRepo + PlanungsRepo
"""
from __future__ import annotations

from dataclasses import dataclass

from db.schema import DbSchema


@dataclass
class UserSettings:
    """Benutzerspezifische Einstellungen."""
    user_id:              int   = 0
    absender_name:        str   = ""
    absender_adresse:     str   = ""
    absender_mail:        str   = ""
    absender_geburtsdatum: str  = ""
    stundensatz:          float = 20.0
    standard_person:      str   = ""
    standard_jahr:        int   = 0
    benachrichtigung_email: int = 0
    benachrichtigung_push:  int = 0

    @classmethod
    def from_row(cls, r) -> "UserSettings":
        return cls(
            user_id=r["user_id"],
            absender_name=r["absender_name"],
            absender_adresse=r["absender_adresse"],
            absender_mail=r["absender_mail"],
            absender_geburtsdatum=r["absender_geburtsdatum"],
            stundensatz=r["stundensatz"],
            standard_person=r["standard_person"],
            standard_jahr=r["standard_jahr"],
            benachrichtigung_email=r["benachrichtigung_email"] if "benachrichtigung_email" in r.keys() else 0,
            benachrichtigung_push=r["benachrichtigung_push"] if "benachrichtigung_push" in r.keys() else 0,
        )


class UserSettingsRepo:
    """CRUD für user_settings-Tabelle."""

    def __init__(self, schema: DbSchema) -> None:
        self._s = schema

    def _c(self):
        return self._s.connect()

    def laden(self, user_id: int) -> UserSettings:
        with self._c() as conn:
            row = conn.execute("SELECT * FROM user_settings WHERE user_id=?", (user_id,)).fetchone()
        return UserSettings.from_row(row) if row else UserSettings(user_id=user_id)

    def speichern(self, s: UserSettings) -> None:
        with self._c() as conn:
            conn.execute("""
                INSERT INTO user_settings
                    (user_id, absender_name, absender_adresse, absender_mail,
                     absender_geburtsdatum, stundensatz, standard_person, standard_jahr,
                     benachrichtigung_email, benachrichtigung_push)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    absender_name=excluded.absender_name,
                    absender_adresse=excluded.absender_adresse,
                    absender_mail=excluded.absender_mail,
                    absender_geburtsdatum=excluded.absender_geburtsdatum,
                    stundensatz=excluded.stundensatz,
                    standard_person=excluded.standard_person,
                    standard_jahr=excluded.standard_jahr,
                    benachrichtigung_email=excluded.benachrichtigung_email,
                    benachrichtigung_push=excluded.benachrichtigung_push
            """, (s.user_id, s.absender_name, s.absender_adresse, s.absender_mail,
                  s.absender_geburtsdatum, s.stundensatz, s.standard_person, s.standard_jahr,
                  s.benachrichtigung_email, s.benachrichtigung_push))


class PlanungsRepo:
    """CRUD für budget_planung-Tabelle."""

    def __init__(self, schema: DbSchema) -> None:
        self._s = schema

    def _c(self):
        return self._s.connect()

    def laden(self, person: str, jahr: int) -> dict:
        with self._c() as conn:
            rows = conn.execute(
                "SELECT monat, stunden, notiz FROM budget_planung WHERE person=? AND jahr=?",
                (person, jahr)
            ).fetchall()
        return {r["monat"]: {"stunden": r["stunden"], "notiz": r["notiz"]} for r in rows}

    def speichern(self, person: str, jahr: int, monat: int, stunden: float, notiz: str = "") -> None:
        with self._c() as conn:
            conn.execute("""
                INSERT INTO budget_planung (person, jahr, monat, stunden, notiz)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(person, jahr, monat) DO UPDATE SET
                    stunden=excluded.stunden, notiz=excluded.notiz
            """, (person, jahr, monat, stunden, notiz))

    def bulk_speichern(self, person: str, jahr: int, planung: dict) -> None:
        with self._c() as conn:
            for monat, stunden in planung.items():
                conn.execute("""
                    INSERT INTO budget_planung (person, jahr, monat, stunden, notiz)
                    VALUES (?, ?, ?, ?, '')
                    ON CONFLICT(person, jahr, monat) DO UPDATE SET stunden=excluded.stunden
                """, (person, jahr, monat, float(stunden)))

    def loeschen(self, person: str, jahr: int) -> None:
        with self._c() as conn:
            conn.execute("DELETE FROM budget_planung WHERE person=? AND jahr=?", (person, jahr))
