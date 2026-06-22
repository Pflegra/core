"""Tests fr models.py  PflegeEintrag und PflegraDB."""

import sys
import tempfile
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from models import PflegeEintrag, PflegraDB, WOCHENTAGE


# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

@pytest.fixture
def eintrag_jan():
    return PflegeEintrag.from_datum(
        datum=date(2024, 1, 8),   # Montag
        von="09:00", bis="13:00",
        stunden=4.0,
        person="Mller, Hans",
    )


@pytest.fixture
def eintrag_feb():
    return PflegeEintrag.from_datum(
        datum=date(2024, 2, 5),   # Montag
        von="10:00", bis="14:00",
        stunden=4.0,
        person="Mller, Hans",
    )


@pytest.fixture
def tmp_db(tmp_path):
    return PflegraDB(tmp_path / "test.db")


# ------------------------------------------------------------------ #
#  PflegeEintrag                                                       #
# ------------------------------------------------------------------ #

class TestPflegeEintrag:

    def test_from_datum_leitet_felder_ab(self, eintrag_jan):
        assert eintrag_jan.monat    == 1
        assert eintrag_jan.jahr     == 2024
        assert eintrag_jan.wochentag == "Montag"

    def test_wochentag_mittwoch(self):
        e = PflegeEintrag.from_datum(date(2024, 1, 10), "14:00", "17:00", 3.0, "X")
        assert e.wochentag == "Mittwoch"

    def test_wochentag_sonntag(self):
        e = PflegeEintrag.from_datum(date(2024, 1, 7), "10:00", "12:00", 2.0, "X")
        assert e.wochentag == "Sonntag"

    def test_from_dict_iso_datum(self):
        e = PflegeEintrag.from_dict({
            "datum": "2024-03-15",
            "von": "09:00", "bis": "12:00",
            "stunden": "3.0", "person": "Test",
        })
        assert e.datum == date(2024, 3, 15)
        assert e.monat == 3
        assert e.jahr  == 2024

    def test_from_dict_deutsches_datum(self):
        from csv_import import _parse_datum
        d = _parse_datum("15.03.2024")
        assert d == date(2024, 3, 15)

    def test_from_dict_stunden_komma(self):
        e = PflegeEintrag.from_dict({
            "datum": "2024-01-10",
            "von": "09:00", "bis": "13:30",
            "stunden": "4,5", "person": "Test",
        })
        assert e.stunden == 4.5

    def test_from_dict_ohne_wochentag_leitet_ab(self):
        e = PflegeEintrag.from_dict({
            "datum": "2024-01-08",  # Montag
            "von": "09:00", "bis": "13:00",
            "stunden": "4.0", "person": "T",
        })
        assert e.wochentag == "Montag"

    def test_to_dict_datum_als_string(self, eintrag_jan):
        d = eintrag_jan.to_dict()
        assert d["datum"] == "2024-01-08"
        assert isinstance(d["datum"], str)

    def test_roundtrip_from_to_dict(self, eintrag_jan):
        d  = eintrag_jan.to_dict()
        e2 = PflegeEintrag.from_dict(d)
        assert e2.datum    == eintrag_jan.datum
        assert e2.stunden  == eintrag_jan.stunden
        assert e2.person   == eintrag_jan.person
        assert e2.wochentag == eintrag_jan.wochentag

    def test_archiv_pfad(self, eintrag_jan):
        p = eintrag_jan.archiv_pfad(Path("Archiv"))
        assert p == Path("Archiv/2024/Mller, Hans")

    def test_str_repraesentation(self, eintrag_jan):
        s = str(eintrag_jan)
        assert "Montag" in s
        assert "2024-01-08" in s
        assert "Mller, Hans" in s


# ------------------------------------------------------------------ #
#  PflegraDB                                                    #
# ------------------------------------------------------------------ #

class TestPflegraDB:

    def test_insert_setzt_id(self, tmp_db, eintrag_jan):
        result = tmp_db.insert(eintrag_jan)
        assert result.id is not None
        assert result.id >= 1

    def test_insert_many(self, tmp_db, eintrag_jan, eintrag_feb):
        ergebnisse = tmp_db.insert_many([eintrag_jan, eintrag_feb])
        assert all(e.id is not None for e in ergebnisse)
        assert ergebnisse[0].id != ergebnisse[1].id

    def test_alle_gibt_chronologisch(self, tmp_db, eintrag_feb, eintrag_jan):
        tmp_db.insert(eintrag_feb)
        tmp_db.insert(eintrag_jan)
        alle = tmp_db.alle(1)
        assert len(alle) == 2
        assert alle[0].datum <= alle[1].datum

    def test_nach_person_und_jahr(self, tmp_db, eintrag_jan, eintrag_feb):
        tmp_db.insert_many([eintrag_jan, eintrag_feb])
        schmidt = PflegeEintrag.from_datum(date(2024, 1, 10), "14:00", "17:00", 3.0, "Schmidt")
        tmp_db.insert(schmidt)

        ergebnis = tmp_db.nach_person_und_jahr("Mller, Hans", 2024, 1)
        assert len(ergebnis) == 2
        assert all(e.person == "Mller, Hans" for e in ergebnis)

    def test_nach_monat(self, tmp_db, eintrag_jan, eintrag_feb):
        tmp_db.insert_many([eintrag_jan, eintrag_feb])
        januar = tmp_db.nach_monat("Mller, Hans", 2024, 1, 1)
        assert len(januar) == 1
        assert januar[0].monat == 1

    def test_personen(self, tmp_db, eintrag_jan):
        tmp_db.insert(eintrag_jan)
        anna = PflegeEintrag.from_datum(date(2024, 1, 10), "14:00", "17:00", 3.0, "Schmidt, Anna")
        tmp_db.insert(anna)
        personen = tmp_db.personen(1)
        assert "Mller, Hans" in personen
        assert "Schmidt, Anna" in personen

    def test_jahre(self, tmp_db, eintrag_jan):
        tmp_db.insert(eintrag_jan)
        e2025 = PflegeEintrag.from_datum(date(2025, 3, 1), "09:00", "12:00", 3.0, "Mller, Hans")
        tmp_db.insert(e2025)
        assert tmp_db.jahre(1) == [2024, 2025]

    def test_loeschen(self, tmp_db, eintrag_jan):
        eingefuegt = tmp_db.insert(eintrag_jan)
        assert tmp_db.loeschen(eingefuegt.id, 1) is True
        assert tmp_db.alle(1) == []

    def test_loeschen_nicht_vorhanden(self, tmp_db):
        assert tmp_db.loeschen(9999, 1) is False

    def test_roundtrip_datum_bleibt_date(self, tmp_db, eintrag_jan):
        tmp_db.insert(eintrag_jan)
        gelesen = tmp_db.alle(1)[0]
        assert isinstance(gelesen.datum, date)
        assert gelesen.datum == date(2024, 1, 8)

    def test_update_aendert_felder(self, tmp_db, eintrag_jan):
        tmp_db.insert(eintrag_jan)
        eintrag_jan.stunden = 6.0
        eintrag_jan.von     = "08:00"
        assert tmp_db.update(eintrag_jan) is True
        aktualisiert = tmp_db.alle(1)[0]
        assert aktualisiert.stunden == 6.0
        assert aktualisiert.von     == "08:00"

    def test_update_ohne_id_gibt_false(self, tmp_db):
        """Update ohne ID gibt False zurück (keine Zeile betroffen)."""
        e = PflegeEintrag.from_datum(date(2024,1,8),"09:00","13:00",4.0,"X")
        result = tmp_db.update(e)
        assert result is False

    def test_update_nicht_vorhanden_gibt_false(self, tmp_db):
        e = PflegeEintrag.from_datum(date(2024,1,8),"09:00","13:00",4.0,"X")
        e.id = 9999
        assert tmp_db.update(e) is False

    def test_suche_nach_person(self, tmp_db, eintrag_jan):
        tmp_db.insert(eintrag_jan)
        anna = PflegeEintrag.from_datum(date(2024,1,10),"14:00","17:00",3.0,"Schmidt, Anna")
        tmp_db.insert(anna)
        ergebnis = tmp_db.suche("Mller", 1)
        assert len(ergebnis) == 1
        assert ergebnis[0].person == "Mller, Hans"

    def test_suche_nach_datum(self, tmp_db, eintrag_jan):
        tmp_db.insert(eintrag_jan)
        ergebnis = tmp_db.suche("2024-01", 1)
        assert len(ergebnis) == 1

    def test_suche_kein_treffer(self, tmp_db, eintrag_jan):
        tmp_db.insert(eintrag_jan)
        assert tmp_db.suche("XYZ_nicht_vorhanden", 1) == []

    def test_statistik(self, tmp_db, eintrag_jan, eintrag_feb):
        tmp_db.insert_many([eintrag_jan, eintrag_feb])
        s = tmp_db.statistik(1)
        assert s["eintraege_gesamt"] == 2
        assert s["stunden_gesamt"]   == pytest.approx(8.0)
        assert s["personen_anzahl"]  == 1
        assert s["jahre_anzahl"]     == 1

    def test_schema_version(self, tmp_db):
        assert tmp_db.schema_version() == 24
