"""
db/personen.py — PersonenRepo
"""
from __future__ import annotations

from db.schema import DbSchema


class PersonenRepo:
    """CRUD für personen-Tabelle."""

    def __init__(self, schema: DbSchema) -> None:
        self._s = schema

    def _c(self):
        return self._s.connect()

    def anlegen(self, name: str, notiz: str = "", owner_id: int = 0) -> bool:
        name = name.strip()
        if not name:
            raise ValueError("Name darf nicht leer sein.")
        try:
            with self._c() as conn:
                conn.execute("INSERT INTO personen (name, notiz, owner_id) VALUES (?, ?, ?)", (name, notiz, owner_id))
            return True
        except Exception:
            return False

    def umbenennen(self, alter_name: str, neuer_name: str) -> bool:
        neuer_name = neuer_name.strip()
        if not neuer_name:
            raise ValueError("Name darf nicht leer sein.")
        with self._c() as conn:
            c = conn.execute("UPDATE personen SET name=? WHERE name=?", (neuer_name, alter_name))
            if c.rowcount > 0:
                conn.execute("UPDATE pflege_eintraege SET person=? WHERE person=?", (neuer_name, alter_name))
        return c.rowcount > 0

    def loeschen(self, name: str, owner_id: int = 0) -> tuple:
        with self._c() as conn:
            if owner_id:
                n = conn.execute("SELECT COUNT(*) as n FROM pflege_eintraege WHERE person=? AND owner_id=?", (name, owner_id)).fetchone()["n"]
                if n > 0:
                    return False, n
                c = conn.execute("DELETE FROM personen WHERE name=? AND owner_id=?", (name, owner_id))
            else:
                n = conn.execute("SELECT COUNT(*) as n FROM pflege_eintraege WHERE person=?", (name,)).fetchone()["n"]
                if n > 0:
                    return False, n
                c = conn.execute("DELETE FROM personen WHERE name=?", (name,))
        return c.rowcount > 0, 0

    def loeschen_mit_eintraegen(self, name: str, owner_id: int = 0) -> int:
        with self._c() as conn:
            if owner_id:
                c = conn.execute("DELETE FROM pflege_eintraege WHERE person=? AND owner_id=?", (name, owner_id))
                n = c.rowcount
                conn.execute("DELETE FROM personen WHERE name=? AND owner_id=?", (name, owner_id))
            else:
                c = conn.execute("DELETE FROM pflege_eintraege WHERE person=?", (name,))
                n = c.rowcount
                conn.execute("DELETE FROM personen WHERE name=?", (name,))
        return n

    def liste(self, owner_id: int = 0) -> list:
        with self._c() as conn:
            if owner_id:
                rows = conn.execute("""
                    SELECT p.name, p.notiz, COUNT(e.id) as eintraege, COALESCE(SUM(e.stunden), 0) as stunden
                    FROM personen p LEFT JOIN pflege_eintraege e ON e.person = p.name AND e.owner_id = ?
                    WHERE p.owner_id = ?
                    GROUP BY p.name ORDER BY p.name
                """, (owner_id, owner_id)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT p.name, p.notiz, COUNT(e.id) as eintraege, COALESCE(SUM(e.stunden), 0) as stunden
                    FROM personen p LEFT JOIN pflege_eintraege e ON e.person = p.name
                    GROUP BY p.name ORDER BY p.name
                """).fetchall()
        return [dict(r) for r in rows]

    def namen(self, owner_id: int = 0) -> list:
        with self._c() as conn:
            if owner_id:
                rows = conn.execute("""
                    SELECT name FROM personen WHERE owner_id=?
                    UNION SELECT DISTINCT person FROM pflege_eintraege WHERE owner_id=?
                    ORDER BY name
                """, (owner_id, owner_id)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT name FROM personen
                    UNION SELECT DISTINCT person FROM pflege_eintraege
                    ORDER BY name
                """).fetchall()
        return [r["name"] for r in rows]
