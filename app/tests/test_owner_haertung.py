"""Regression tests for the v1.6.0 owner boundary."""
from datetime import date
import asyncio
import sqlite3

import pytest

from models import Ersatzpflegekraft, PflegeEintrag, PflegraDB, Versicherter
from db.schema import DbSchema


@pytest.fixture
def db(tmp_path):
    return PflegraDB(tmp_path / "owner_haertung.db")


def _eintrag(owner_id: int, notiz: str) -> PflegeEintrag:
    eintrag = PflegeEintrag.from_datum(
        date(2026, 6, 21), "10:00", "12:00", 2.0, "Gleicher Name", notiz=notiz
    )
    eintrag.owner_id = owner_id
    return eintrag


def test_suche_und_duplikate_bleiben_beim_owner(db):
    db.insert(_eintrag(1, "nur owner eins"))
    db.insert(_eintrag(2, "nur owner zwei"))
    db.insert(_eintrag(2, "duplikat owner zwei"))

    assert [e.notiz for e in db.suche("owner", 1)] == ["nur owner eins"]
    assert db.suche("zwei", 1) == []
    assert db.duplikate_finden(1) == []
    assert len(db.duplikate_finden(2)) == 1


def test_fremde_eintrags_id_kann_nicht_mutiert_oder_geloescht_werden(db):
    fremd = db.insert(_eintrag(2, "unveraendert"))
    angriffsobjekt = _eintrag(1, "manipuliert")
    angriffsobjekt.id = fremd.id

    assert db.update(angriffsobjekt) is False
    assert db.loeschen(fremd.id, 1) is False
    assert db.bulk_loeschen([fremd.id], 1) == 0
    assert db.alle(2)[0].notiz == "unveraendert"


def test_gleicher_personenname_und_versicherte_sind_isoliert(db):
    db.person_anlegen("Gleicher Name", owner_id=1)
    db.person_anlegen("Gleicher Name", owner_id=2)
    db.versicherter_speichern(Versicherter("Gleicher Name", krankenkasse="A", owner_id=1))
    db.versicherter_speichern(Versicherter("Gleicher Name", krankenkasse="B", owner_id=2))

    assert db.versicherter_laden("Gleicher Name", 1).krankenkasse == "A"
    assert db.versicherter_laden("Gleicher Name", 2).krankenkasse == "B"

    assert db.person_umbenennen("Gleicher Name", "Nur Owner Eins", 1) is True
    assert "Nur Owner Eins" in db.personen(1)
    assert "Gleicher Name" in db.personen(2)


def test_ersatzpflege_load_update_delete_sind_ownergebunden(db):
    db.ersatz_speichern(Ersatzpflegekraft(person="Gleicher Name", name="Maria", owner_id=2))
    fremd = db.ersatz_alle("Gleicher Name", 2)[0]

    assert db.ersatz_laden(fremd.id, 1) is None
    fremd.owner_id = 1
    fremd.name = "Manipuliert"
    db.ersatz_speichern(fremd)
    assert db.ersatz_loeschen(fremd.id, "Gleicher Name", 1) is False
    assert db.ersatz_laden(fremd.id, 2).name == "Maria"


def test_budgetplanung_unique_und_crud_sind_ownergebunden(db):
    db.planung_bulk_speichern("Gleicher Name", 2026, {1: 10}, 1)
    db.planung_bulk_speichern("Gleicher Name", 2026, {1: 20}, 2)

    assert db.planung_laden("Gleicher Name", 2026, 1)[1]["stunden"] == 10
    assert db.planung_laden("Gleicher Name", 2026, 2)[1]["stunden"] == 20
    db.planung_loeschen("Gleicher Name", 2026, 1)
    assert db.planung_laden("Gleicher Name", 2026, 1) == {}
    assert db.planung_laden("Gleicher Name", 2026, 2)[1]["stunden"] == 20


def test_migration_v23_auf_v24_erhaelt_budgetplanung(tmp_path):
    db_path = tmp_path / "schema_v23.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE schema_version (version INTEGER NOT NULL);
        INSERT INTO schema_version VALUES (23);
        CREATE TABLE budget_planung (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person TEXT NOT NULL,
            jahr INTEGER NOT NULL,
            monat INTEGER NOT NULL,
            stunden REAL NOT NULL DEFAULT 0,
            notiz TEXT NOT NULL DEFAULT '',
            owner_id INTEGER NOT NULL DEFAULT 1,
            UNIQUE(person, jahr, monat)
        );
        INSERT INTO budget_planung (person, jahr, monat, stunden, notiz, owner_id)
        VALUES ('Bestand', 2026, 1, 12.5, 'bleibt', 2);
    """)
    conn.close()

    schema = DbSchema(db_path)
    schema.migrate()
    with schema.connect() as migrated:
        row = migrated.execute("SELECT * FROM budget_planung").fetchone()
        index_sql = migrated.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='budget_planung'"
        ).fetchone()["sql"]
    assert schema.schema_version() == 24
    assert (row["owner_id"], row["stunden"], row["notiz"]) == (2, 12.5, "bleibt")
    assert "UNIQUE(owner_id, person, jahr, monat)" in index_sql


@pytest.mark.parametrize("aufruf", [
    lambda db: db.alle(0),
    lambda db: db.suche("x", 0),
    lambda db: db.personen(0),
    lambda db: db.planung_laden("x", 2026, 0),
    lambda db: db.ersatz_laden(1, 0),
])
def test_owner_null_wird_abgewiesen(db, aufruf):
    with pytest.raises(ValueError):
        aufruf(db)


def test_push_abmeldung_loescht_keinen_fremden_endpoint(db, monkeypatch):
    from web.routers import erinnerungen

    with db._schema.connect() as conn:
        conn.execute(
            "INSERT INTO push_subscriptions (owner_id, endpoint, p256dh, auth) VALUES (2, 'fremd', 'p', 'a')"
        )

    class Request:
        async def json(self):
            return {"endpoint": "fremd"}

    monkeypatch.setattr(erinnerungen, "get_db", lambda request: db)
    monkeypatch.setattr(erinnerungen, "get_owner_id", lambda request: 1)
    response = asyncio.run(erinnerungen.push_unsubscribe(Request()))

    assert response.status_code == 200
    with db._schema.connect() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM push_subscriptions WHERE endpoint='fremd' AND owner_id=2"
        ).fetchone()[0] == 1
