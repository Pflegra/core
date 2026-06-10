"""
db/users.py — User Dataclass + UserRepo
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from db.schema import DbSchema


@dataclass
class User:
    id:          int  = 0
    username:    str  = ""
    passwort:    str  = ""   # bcrypt-Hash
    rolle:       str  = "user"
    aktiv:       bool = True
    erstellt_am: str  = ""
    notiz:       str  = ""

    @classmethod
    def from_row(cls, r) -> "User":
        return cls(
            id=r["id"], username=r["username"], passwort=r["passwort"],
            rolle=r["rolle"], aktiv=bool(r["aktiv"]),
            erstellt_am=r["erstellt_am"], notiz=r["notiz"],
        )

    @property
    def ist_admin(self) -> bool:
        return self.rolle == "admin"


class UserRepo:
    """CRUD für users-Tabelle."""

    def __init__(self, schema: DbSchema) -> None:
        self._s = schema

    def _c(self):
        return self._s.connect()

    def alle(self) -> List[User]:
        with self._c() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY username").fetchall()
        return [User.from_row(r) for r in rows]

    def laden_by_id(self, user_id: int) -> Optional[User]:
        with self._c() as conn:
            row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        return User.from_row(row) if row else None

    def laden_by_username(self, username: str) -> Optional[User]:
        with self._c() as conn:
            row = conn.execute("SELECT * FROM users WHERE username=? AND aktiv=1", (username,)).fetchone()
        return User.from_row(row) if row else None

    def speichern(self, u: User) -> int:
        with self._c() as conn:
            if u.id:
                conn.execute("""
                    UPDATE users SET username=?, passwort=?, rolle=?, aktiv=?, notiz=?
                    WHERE id=?
                """, (u.username, u.passwort, u.rolle, int(u.aktiv), u.notiz, u.id))
                return u.id
            else:
                cur = conn.execute("""
                    INSERT INTO users (username, passwort, rolle, aktiv, notiz)
                    VALUES (?, ?, ?, ?, ?)
                """, (u.username, u.passwort, u.rolle, int(u.aktiv), u.notiz))
                return cur.lastrowid

    def loeschen(self, user_id: int) -> bool:
        with self._c() as conn:
            cur = conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        return cur.rowcount > 0

    def anzahl(self) -> int:
        with self._c() as conn:
            return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def admin_existiert(self) -> bool:
        with self._c() as conn:
            row = conn.execute("SELECT COUNT(*) FROM users WHERE rolle='admin'").fetchone()
        return row[0] > 0
