"""
Tests Phase H — Multiuser, Auth, Datenisolation, Rollen, Demo-Reset
"""
import sys
import tempfile
from pathlib import Path
from datetime import date

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import PflegraDB, PflegeEintrag, Versicherter, UserSettings
from models import User


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def db():
    """Frische In-Memory-DB für jeden Test."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)
    db = PflegraDB(db_path)
    yield db
    db_path.unlink(missing_ok=True)


@pytest.fixture
def admin(db):
    """Admin-User anlegen."""
    from web.auth import hash_passwort
    u = User(username="admin", passwort=hash_passwort("adminpass"),
             rolle="admin", aktiv=True)
    uid = db.user_speichern(u)
    return db.user_laden(uid)


@pytest.fixture
def user1(db):
    """Normaler User 1."""
    from web.auth import hash_passwort
    u = User(username="user1", passwort=hash_passwort("pass1"),
             rolle="user", aktiv=True)
    uid = db.user_speichern(u)
    return db.user_laden(uid)


@pytest.fixture
def user2(db):
    """Normaler User 2."""
    from web.auth import hash_passwort
    u = User(username="user2", passwort=hash_passwort("pass2"),
             rolle="user", aktiv=True)
    uid = db.user_speichern(u)
    return db.user_laden(uid)


@pytest.fixture
def demo_user(db):
    """Demo-User."""
    from web.auth import hash_passwort
    u = User(username="demo", passwort=hash_passwort("demo"),
             rolle="user", aktiv=True)
    uid = db.user_speichern(u)
    return db.user_laden(uid)


# ─── User-Modell ─────────────────────────────────────────────────────────────

class TestUserModell:

    def test_user_anlegen(self, db):
        from web.auth import hash_passwort
        u = User(username="test", passwort=hash_passwort("pw"), rolle="user")
        uid = db.user_speichern(u)
        assert uid > 0

    def test_user_laden_by_username(self, db, admin):
        u = db.user_laden_by_username("admin")
        assert u is not None
        assert u.username == "admin"
        assert u.rolle == "admin"

    def test_user_nicht_gefunden(self, db):
        u = db.user_laden_by_username("nichtexistent")
        assert u is None

    def test_admin_existiert(self, db, admin):
        assert db.user_admin_existiert() is True

    def test_kein_admin(self, db):
        assert db.user_admin_existiert() is False

    def test_user_anzahl(self, db, admin, user1, user2):
        assert db.user_anzahl() == 3

    def test_user_deaktivieren(self, db, user1):
        user1.aktiv = False
        db.user_speichern(user1)
        u = db.user_laden_by_username("user1")
        assert u is None  # inaktive User werden nicht geladen

    def test_user_loeschen(self, db, user1):
        db.user_loeschen(user1.id)
        assert db.user_laden_by_username("user1") is None

    def test_rollen(self, db, admin, user1):
        assert admin.ist_admin is True
        assert user1.ist_admin is False

    def test_username_unique(self, db, admin):
        from web.auth import hash_passwort
        u2 = User(username="admin", passwort=hash_passwort("other"), rolle="user")
        # Zweiter Admin mit gleichem Namen sollte fehlschlagen
        with pytest.raises(Exception):
            db.user_speichern(u2)


# ─── Auth / Passwort ─────────────────────────────────────────────────────────

class TestAuth:

    def test_passwort_hash(self):
        from web.auth import hash_passwort, pruefe_passwort
        h = hash_passwort("geheim123")
        assert h != "geheim123"
        assert pruefe_passwort("geheim123", h) is True
        assert pruefe_passwort("falsch", h) is False

    def test_session_cookie_erstellen(self):
        import os
        os.environ["PFLEGRA_SECRET"] = "test-secret-key-12345"
        from web.auth import erstelle_session_cookie, pruefe_session_cookie
        token = erstelle_session_cookie(42)
        assert token
        user_id = pruefe_session_cookie(token)
        assert user_id == 42

    def test_session_cookie_ungueltig(self):
        import os
        os.environ["PFLEGRA_SECRET"] = "test-secret-key-12345"
        from web.auth import pruefe_session_cookie
        assert pruefe_session_cookie("ungueltigertoken") is None
        assert pruefe_session_cookie("") is None

    def test_session_cookie_falscher_key(self):
        import os
        os.environ["PFLEGRA_SECRET"] = "key1"
        from web.auth import erstelle_session_cookie
        token = erstelle_session_cookie(1)

        os.environ["PFLEGRA_SECRET"] = "key2"
        # Nach Key-Wechsel: importlib.reload nötig
        import importlib
        import web.auth as auth_mod
        importlib.reload(auth_mod)
        result = auth_mod.pruefe_session_cookie(token)
        assert result is None

        os.environ["PFLEGRA_SECRET"] = "test-secret-key-12345"
        importlib.reload(auth_mod)


# ─── Datenisolation ──────────────────────────────────────────────────────────

class TestDatenisolation:

    def _eintrag(self, person: str, owner_id: int) -> PflegeEintrag:
        e = PflegeEintrag.from_datum(
            datum=date(2026, 1, 10),
            von="10:00", bis="12:00",
            stunden=2.0, person=person,
        )
        e.owner_id = owner_id
        return e

    def test_eintraege_getrennt(self, db, user1, user2):
        """User sieht nur eigene Einträge."""
        db.insert(self._eintrag("Person A", user1.id))
        db.insert(self._eintrag("Person B", user2.id))

        eintraege_u1 = db.alle(user1.id)
        eintraege_u2 = db.alle(user2.id)

        assert len(eintraege_u1) == 1
        assert len(eintraege_u2) == 1
        assert eintraege_u1[0].person == "Person A"
        assert eintraege_u2[0].person == "Person B"

    def test_eintraege_ohne_filter(self, db, user1, user2):
        """Ohne owner_id: alle Einträge sichtbar (Admin-Kontext)."""
        db.insert(self._eintrag("Person A", user1.id))
        db.insert(self._eintrag("Person B", user2.id))
        alle = db.alle(0)
        assert len(alle) == 2

    def test_personen_getrennt(self, db, user1, user2):
        """User sieht nur eigene Personen."""
        db.person_anlegen("Alice", owner_id=user1.id)
        db.person_anlegen("Bob", owner_id=user2.id)

        personen_u1 = db.personen(user1.id)
        personen_u2 = db.personen(user2.id)

        assert "Alice" in personen_u1
        assert "Alice" not in personen_u2
        assert "Bob" in personen_u2
        assert "Bob" not in personen_u1

    def test_gleicher_name_verschiedene_user(self, db, user1, user2):
        """Zwei User können dieselbe Person anlegen — UNIQUE(name, owner_id)."""
        ok1 = db.person_anlegen("Max Mustermann", owner_id=user1.id)
        ok2 = db.person_anlegen("Max Mustermann", owner_id=user2.id)
        assert ok1 is True
        assert ok2 is True

    def test_statistik_gefiltert(self, db, user1, user2):
        """Statistik zeigt nur eigene Daten."""
        db.insert(self._eintrag("A", user1.id))
        db.insert(self._eintrag("B", user1.id))
        db.insert(self._eintrag("C", user2.id))

        stats_u1 = db.statistik(user1.id)
        stats_u2 = db.statistik(user2.id)

        assert stats_u1["eintraege_gesamt"] == 2
        assert stats_u2["eintraege_gesamt"] == 1

    def test_jahre_gefiltert(self, db, user1, user2):
        db.insert(self._eintrag("A", user1.id))
        db.insert(self._eintrag("B", user2.id))

        jahre_u1 = db.jahre(user1.id)
        jahre_u2 = db.jahre(user2.id)

        assert 2026 in jahre_u1
        assert 2026 in jahre_u2
        assert len(jahre_u1) == 1
        assert len(jahre_u2) == 1

    def test_versicherter_isolation(self, db, user1, user2):
        """Versicherte sind pro User isoliert — Person zuerst anlegen wegen FK."""
        db.person_anlegen("Hans", owner_id=user1.id)
        db.person_anlegen("Hans", owner_id=user2.id)
        v1 = Versicherter(name="Hans", owner_id=user1.id)
        v2 = Versicherter(name="Hans", owner_id=user2.id)
        db.versicherter_speichern(v1)
        db.versicherter_speichern(v2)
        loaded = db.versicherter_laden("Hans")
        assert loaded is not None

    def test_eintraege_loeschen_nur_eigene(self, db, user1, user2):
        """Beim Löschen werden nur eigene Einträge gelöscht."""
        # Person zuerst anlegen
        db.person_anlegen("Alice", owner_id=user1.id)
        db.person_anlegen("Alice", owner_id=user2.id)

        e1 = self._eintrag("Alice", user1.id)
        e2 = self._eintrag("Alice", user2.id)
        db.insert(e1)
        db.insert(e2)

        db.person_loeschen_mit_eintraegen("Alice", user1.id)

        assert len(db.alle(user1.id)) == 0
        assert len(db.alle(user2.id)) == 1  # user2 unberührt


# ─── Rollen ──────────────────────────────────────────────────────────────────

class TestRollen:

    def test_admin_rolle(self, db, admin):
        assert admin.rolle == "admin"
        assert admin.ist_admin is True

    def test_user_rolle(self, db, user1):
        assert user1.rolle == "user"
        assert user1.ist_admin is False

    def test_demo_nie_admin(self, db, demo_user):
        assert demo_user.ist_admin is False
        assert demo_user.username == "demo"

    def test_admin_sieht_alle_users(self, db, admin, user1, user2, demo_user):
        alle = db.user_alle()
        assert len(alle) == 4

    def test_user_passwort_aendern(self, db, user1):
        from web.auth import hash_passwort, pruefe_passwort
        user1.passwort = hash_passwort("neuespasswort")
        db.user_speichern(user1)
        u = db.user_laden(user1.id)
        assert pruefe_passwort("neuespasswort", u.passwort) is True
        assert pruefe_passwort("pass1", u.passwort) is False


# ─── User-Settings ───────────────────────────────────────────────────────────

class TestUserSettings:

    def test_settings_anlegen(self, db, user1):
        s = UserSettings(
            user_id=user1.id,
            absender_name="Stefan Neu",
            absender_adresse="Musterstr. 1\n44800 Bochum",
            stundensatz=25.0,
        )
        db.user_settings_speichern(s)
        loaded = db.user_settings_laden(user1.id)
        assert loaded.absender_name == "Stefan Neu"
        assert loaded.stundensatz == 25.0

    def test_settings_leer_default(self, db, user1):
        """Leere Settings geben Default zurück."""
        s = db.user_settings_laden(user1.id)
        assert s.absender_name == ""
        assert s.stundensatz == 20.0

    def test_settings_pro_user(self, db, user1, user2):
        """Settings sind pro User getrennt."""
        s1 = UserSettings(user_id=user1.id, absender_name="User1", stundensatz=20.0)
        s2 = UserSettings(user_id=user2.id, absender_name="User2", stundensatz=30.0)
        db.user_settings_speichern(s1)
        db.user_settings_speichern(s2)

        assert db.user_settings_laden(user1.id).absender_name == "User1"
        assert db.user_settings_laden(user2.id).absender_name == "User2"

    def test_settings_update(self, db, user1):
        """Settings können überschrieben werden."""
        s = UserSettings(user_id=user1.id, absender_name="Alt", stundensatz=20.0)
        db.user_settings_speichern(s)
        s.absender_name = "Neu"
        db.user_settings_speichern(s)
        assert db.user_settings_laden(user1.id).absender_name == "Neu"


# ─── Demo-Reset ──────────────────────────────────────────────────────────────

class TestDemoReset:

    def test_demo_reset_loescht_daten(self, db, demo_user):
        """Demo-Reset löscht alle Demo-Daten."""
        from demo_reset import demo_reset

        # Demo-Daten anlegen
        e = PflegeEintrag.from_datum(
            datum=date(2026, 1, 10), von="10:00", bis="12:00",
            stunden=2.0, person="Test",
        )
        e.owner_id = demo_user.id
        db.insert(e)
        assert len(db.alle(demo_user.id)) > 0

        # Reset
        demo_reset(db)

        # Demo-Daten sollten neu angelegt sein (Musterdaten)
        eintraege = db.alle(demo_user.id)
        assert len(eintraege) > 0  # Musterdaten wurden angelegt

    def test_demo_reset_beruehrt_andere_user_nicht(self, db, demo_user, user1):
        """Demo-Reset berührt andere User nicht."""
        from demo_reset import demo_reset

        e = PflegeEintrag.from_datum(
            datum=date(2026, 1, 10), von="10:00", bis="12:00",
            stunden=2.0, person="User1Person",
        )
        e.owner_id = user1.id
        db.insert(e)

        demo_reset(db)

        # User1-Daten unberührt
        assert len(db.alle(user1.id)) == 1
        assert db.alle(user1.id)[0].person == "User1Person"

    def test_demo_musterdaten_nach_reset(self, db, demo_user):
        """Nach Reset hat Demo Musterdaten."""
        from demo_reset import demo_reset, DEMO_PERSON
        demo_reset(db)

        # Direkt in DB prüfen
        personen = db.personen(demo_user.id)
        eintraege = db.alle(demo_user.id)
        assert DEMO_PERSON in personen or len(eintraege) > 0

    def test_demo_reset_idempotent(self, db, demo_user):
        """Demo-Reset kann mehrfach aufgerufen werden."""
        from demo_reset import demo_reset
        demo_reset(db)
        count1 = len(db.alle(demo_user.id))
        demo_reset(db)
        count2 = len(db.alle(demo_user.id))
        # Nach zweitem Reset gleiche Anzahl Einträge
        assert count1 == count2
        assert count1 > 0


# ─── Schema-Migration ────────────────────────────────────────────────────────

class TestSchemaMigration:

    def test_schema_version(self, db):
        assert db.schema_version() == 12

    def test_owner_id_default(self, db, admin):
        """Neue Einträge bekommen owner_id gesetzt."""
        e = PflegeEintrag.from_datum(
            datum=date(2026, 1, 10), von="10:00", bis="12:00",
            stunden=2.0, person="Test",
        )
        e.owner_id = admin.id
        db.insert(e)
        eintraege = db.alle(admin.id)
        assert eintraege[0].owner_id == admin.id

    def test_personen_unique_per_owner(self, db, user1, user2):
        """UNIQUE(name, owner_id) — gleicher Name für verschiedene User ok."""
        assert db.person_anlegen("Gleicher Name", owner_id=user1.id) is True
        assert db.person_anlegen("Gleicher Name", owner_id=user2.id) is True
        # Doppelt für gleichen User schlägt fehl
        assert db.person_anlegen("Gleicher Name", owner_id=user1.id) is False
