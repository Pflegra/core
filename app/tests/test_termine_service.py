"""Tests fuer Terminserien und Schema v23 (auch direkt mit unittest lauffaehig)."""
import sqlite3
import sys
import tempfile
import unittest
import gc
from dataclasses import dataclass
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from db.schema import DbSchema
from services.termine_service import vorkommen_im_monat
from services.kalender_service import baue_kalender


@dataclass
class TerminStub:
    datum: str
    wiederholung: str
    titel: str = "Testtermin"
    uhrzeit_von: str = ""

    @property
    def datum_date(self):
        return date.fromisoformat(self.datum)


class TerminserienTests(unittest.TestCase):
    def daten(self, start, wiederholung, jahr, monat):
        termin = TerminStub(start, wiederholung)
        return [v.datum for v in vorkommen_im_monat(termin, jahr, monat)]

    def test_einmalig(self):
        self.assertEqual(self.daten("2026-06-15", "einmalig", 2026, 6), [date(2026, 6, 15)])
        self.assertEqual(self.daten("2026-06-15", "einmalig", 2026, 7), [])

    def test_taeglich_beginnt_nicht_vor_start(self):
        daten = self.daten("2026-06-29", "taeglich", 2026, 6)
        self.assertEqual(daten, [date(2026, 6, 29), date(2026, 6, 30)])
        self.assertEqual(len(self.daten("2026-06-29", "taeglich", 2026, 7)), 31)

    def test_woechentlich(self):
        self.assertEqual(
            self.daten("2026-06-03", "woechentlich", 2026, 6),
            [date(2026, 6, 3), date(2026, 6, 10), date(2026, 6, 17), date(2026, 6, 24)],
        )

    def test_monatlich_ueberspringt_unmoeglichen_tag(self):
        self.assertEqual(self.daten("2026-01-31", "monatlich", 2026, 2), [])
        self.assertEqual(self.daten("2026-01-31", "monatlich", 2026, 3), [date(2026, 3, 31)])

    def test_jaehrlich_und_schaltjahr(self):
        self.assertEqual(self.daten("2024-02-29", "jaehrlich", 2025, 2), [])
        self.assertEqual(self.daten("2024-02-29", "jaehrlich", 2028, 2), [date(2028, 2, 29)])

    def test_unbekannte_wiederholung(self):
        self.assertEqual(self.daten("2026-06-01", "frei", 2026, 6), [])

    def test_vorkommen_wird_in_kalender_integriert(self):
        termin = TerminStub("2026-06-03", "woechentlich", titel="Therapie", uhrzeit_von="15:00")
        termin.id = 7
        termin.person = "Max"
        termin.wiederholung_label = "Wöchentlich"
        termin.zeit_text = "15:00–16:00 Uhr"
        vorkommen = vorkommen_im_monat(termin, 2026, 6)
        tage = baue_kalender([], [], [], 6, 2026, termin_vorkommen=vorkommen)
        self.assertEqual(tage[3][0].quelle, "termin")
        self.assertEqual(tage[3][0].link, "/termine/7/bearbeiten")
        self.assertEqual(tage[3][0].zeit_text, "15:00–16:00 Uhr")


class SchemaV23Tests(unittest.TestCase):
    def test_migration_erstellt_termintabelle_und_owner_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "pflegra.db"
            schema = DbSchema(db_path)
            schema.migrate()

            self.assertEqual(schema.schema_version(), 23)
            conn = sqlite3.connect(db_path)
            try:
                spalten = {row[1] for row in conn.execute("PRAGMA table_info(eigene_termine)")}
                self.assertEqual(
                    spalten,
                    {"id", "owner_id", "person", "titel", "datum", "ganztag", "uhrzeit_von",
                     "uhrzeit_bis", "wiederholung", "notiz", "created_at"},
                )
                indizes = {row[1] for row in conn.execute("PRAGMA index_list(eigene_termine)")}
                self.assertIn("idx_eigene_termine_owner_datum", indizes)
                self.assertIn("idx_eigene_termine_owner_person", indizes)
            finally:
                conn.close()
            del schema
            gc.collect()

    def test_owner_daten_bleiben_getrennt(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "pflegra.db"
            schema = DbSchema(db_path)
            schema.migrate()
            conn = schema.connect()
            try:
                conn.execute("""INSERT INTO eigene_termine
                    (owner_id, titel, datum, wiederholung) VALUES (1, 'A', '2026-06-01', 'einmalig')""")
                conn.execute("""INSERT INTO eigene_termine
                    (owner_id, titel, datum, wiederholung) VALUES (2, 'B', '2026-06-01', 'einmalig')""")
                rows = conn.execute("SELECT titel FROM eigene_termine WHERE owner_id=?", (1,)).fetchall()
                self.assertEqual([row["titel"] for row in rows], ["A"])
                conn.commit()
            finally:
                conn.close()
            del schema
            gc.collect()

    def test_migration_v22_auf_v23_erhaelt_bestandsdaten(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "pflegra.db"
            schema = DbSchema(db_path)
            schema.migrate()
            conn = schema.connect()
            try:
                conn.execute("INSERT INTO eigene_fristen (owner_id, person, titel, datum) VALUES (4, 'Max', 'Bestand', '2026-07-01')")
                conn.execute("DROP TABLE eigene_termine")
                conn.execute("UPDATE schema_version SET version=22")
                conn.commit()
            finally:
                conn.close()
            schema.migrate()
            conn = schema.connect()
            try:
                bestand = conn.execute("SELECT titel FROM eigene_fristen WHERE owner_id=4").fetchone()
                neue_tabelle = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='eigene_termine'").fetchone()
                version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
                self.assertEqual(bestand["titel"], "Bestand")
                self.assertIsNotNone(neue_tabelle)
                self.assertEqual(version, 23)
            finally:
                conn.close()
            del schema
            gc.collect()


if __name__ == "__main__":
    unittest.main()
