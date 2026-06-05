"""Tests fr config.py  Konfiguration laden/speichern."""

import sys
import json
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import Konfiguration


class TestKonfiguration:

    def test_standardwerte(self):
        k = Konfiguration()
        assert k.stundensatz         == 20.0
        assert k.budget_basis        == 3_539.0
        assert k.budget_aufstockung_max == 0.0
        assert k.pflegedienst_name   == ""
        assert k.datenbank_pfad      == "pflegra.db"

    def test_budget_gesamt_property(self):
        k = Konfiguration()
        assert k.budget_gesamt == pytest.approx(3_539.0)

    def test_speichern_und_laden(self, tmp_path):
        pfad = tmp_path / "config.json"
        k = Konfiguration(
            pflegedienst_name="Testdienst GmbH",
            stundensatz=30.0,
            fenster_breite=1200,
        )
        k.speichere(pfad)
        assert pfad.exists()

        geladen = Konfiguration.lade(pfad)
        assert geladen.pflegedienst_name == "Testdienst GmbH"
        assert geladen.stundensatz       == pytest.approx(30.0)
        assert geladen.fenster_breite    == 1200

    def test_laden_nicht_vorhanden_gibt_standard(self, tmp_path):
        k = Konfiguration.lade(tmp_path / "nicht_da.json")
        assert k.stundensatz == 20.0

    def test_laden_kaputte_json_gibt_standard(self, tmp_path):
        pfad = tmp_path / "kaputt.json"
        pfad.write_text("{ das ist kein JSON }", encoding="utf-8")
        k = Konfiguration.lade(pfad)
        assert k.stundensatz == 20.0

    def test_laden_ignoriert_unbekannte_felder(self, tmp_path):
        pfad = tmp_path / "extra.json"
        daten = {"stundensatz": 28.0, "unbekanntes_feld": "wird ignoriert"}
        pfad.write_text(json.dumps(daten), encoding="utf-8")
        k = Konfiguration.lade(pfad)
        assert k.stundensatz == pytest.approx(28.0)

    def test_speichern_ist_lesbares_json(self, tmp_path):
        pfad = tmp_path / "c.json"
        Konfiguration(pflegedienst_name="Test").speichere(pfad)
        daten = json.loads(pfad.read_text(encoding="utf-8"))
        assert daten["pflegedienst_name"] == "Test"

    def test_roundtrip_alle_felder(self, tmp_path):
        pfad = tmp_path / "full.json"
        original = Konfiguration(
            pflegedienst_name="Pflege AG",
            stundensatz=32.5,
            budget_basis=1700.0,
            archiv_basis="MeinArchiv",
            fenster_x=200,
            fenster_y=150,
        )
        original.speichere(pfad)
        geladen = Konfiguration.lade(pfad)
        assert geladen.pflegedienst_name == "Pflege AG"
        assert geladen.stundensatz       == pytest.approx(32.5)
        assert geladen.budget_basis      == pytest.approx(1700.0)
        assert geladen.archiv_basis      == "MeinArchiv"
        assert geladen.fenster_x         == 200

    def test_speichern_erstellt_ordner(self, tmp_path):
        pfad = tmp_path / "tief" / "ordner" / "config.json"
        Konfiguration().speichere(pfad)
        assert pfad.exists()
