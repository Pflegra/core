"""Tests fr csv_import.py."""

import csv
import sys
from pathlib import Path
from datetime import date

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from csv_import import lese_csv, schreibe_csv, _parse_datum
from models import PflegeEintrag


# ------------------------------------------------------------------ #
#  Hilfsfunktion: CSV schreiben                                        #
# ------------------------------------------------------------------ #

def _schreibe(tmp_path, zeilen: list[list], delimiter=";", encoding="utf-8-sig") -> Path:
    p = tmp_path / "test.csv"
    with p.open("w", newline="", encoding=encoding) as f:
        csv.writer(f, delimiter=delimiter).writerows(zeilen)
    return p


# ------------------------------------------------------------------ #
#  _parse_datum                                                        #
# ------------------------------------------------------------------ #

class TestParseDatum:
    @pytest.mark.parametrize("raw,erwartet", [
        ("2024-01-08",  date(2024, 1, 8)),
        ("08.01.2024",  date(2024, 1, 8)),
        ("08/01/2024",  date(2024, 1, 8)),
        ("2024/01/08",  date(2024, 1, 8)),
        ("2024-12-31",  date(2024, 12, 31)),
    ])
    def test_formate(self, raw, erwartet):
        assert _parse_datum(raw) == erwartet

    def test_unbekanntes_format_wirft_fehler(self):
        with pytest.raises(ValueError, match="Unbekanntes Datumsformat"):
            _parse_datum("January 8, 2024")

    def test_leerzeichen_werden_ignoriert(self):
        assert _parse_datum("  2024-01-08  ") == date(2024, 1, 8)


# ------------------------------------------------------------------ #
#  lese_csv                                                            #
# ------------------------------------------------------------------ #

class TestLeseCsv:

    STANDARD_HEADER = ["datum", "von", "bis", "stunden", "person"]

    def test_basis_import(self, tmp_path):
        p = _schreibe(tmp_path, [
            self.STANDARD_HEADER,
            ["2024-01-08", "09:00", "13:00", "4.0", "Mller, Hans"],
        ])
        eintraege = lese_csv(p)
        assert len(eintraege) == 1
        e = eintraege[0]
        assert e.datum   == date(2024, 1, 8)
        assert e.von     == "09:00"
        assert e.bis     == "13:00"
        assert e.stunden == 4.0
        assert e.person  == "Mller, Hans"
        assert e.wochentag == "Montag"

    def test_monat_jahr_werden_abgeleitet(self, tmp_path):
        p = _schreibe(tmp_path, [
            self.STANDARD_HEADER,
            ["2024-03-15", "09:00", "12:00", "3.0", "Test"],
        ])
        e = lese_csv(p)[0]
        assert e.monat == 3
        assert e.jahr  == 2024

    def test_komma_als_dezimaltrenner(self, tmp_path):
        p = _schreibe(tmp_path, [
            self.STANDARD_HEADER,
            ["2024-01-08", "09:00", "13:30", "4,5", "X"],
        ])
        assert lese_csv(p)[0].stunden == 4.5

    def test_deutsches_datum(self, tmp_path):
        p = _schreibe(tmp_path, [
            self.STANDARD_HEADER,
            ["08.01.2024", "09:00", "13:00", "4.0", "X"],
        ])
        assert lese_csv(p)[0].datum == date(2024, 1, 8)

    def test_komma_delimiter(self, tmp_path):
        p = _schreibe(tmp_path, [
            self.STANDARD_HEADER,
            ["2024-01-08", "09:00", "13:00", "4.0", "X"],
        ], delimiter=",")
        # kein Anfhrungszeichen-Problem, da "Mller, Hans" entfllt
        assert len(lese_csv(p)) == 1

    def test_synonyme_spaltennahmen(self, tmp_path):
        p = _schreibe(tmp_path, [
            ["date", "start", "end", "hours", "patient"],
            ["2024-01-08", "09:00", "13:00", "4.0", "Test"],
        ])
        e = lese_csv(p)[0]
        assert e.datum == date(2024, 1, 8)
        assert e.person == "Test"

    def test_fehlende_pflichtfelder_werfen_fehler(self, tmp_path):
        p = _schreibe(tmp_path, [
            ["datum", "von"],   # fehlt: bis, stunden, person
            ["2024-01-08", "09:00"],
        ])
        with pytest.raises(ValueError, match="Pflichtfelder fehlen"):
            lese_csv(p)

    def test_fehlerhafte_zeile_wird_uebersprungen(self, tmp_path):
        fehler: list = []
        p = _schreibe(tmp_path, [
            self.STANDARD_HEADER,
            ["2024-01-08", "09:00", "13:00", "4.0", "OK"],
            ["KEIN-DATUM",  "09:00", "13:00", "4.0", "Fehler"],
        ])
        ergebnis = lese_csv(p, fehler_callback=lambda n, z, e: fehler.append(n))
        assert len(ergebnis)  == 1
        assert len(fehler)    == 1
        assert fehler[0]      == 3   # Zeile 3

    def test_datei_nicht_gefunden(self):
        with pytest.raises(FileNotFoundError):
            lese_csv(Path("/nichtvorhanden/datei.csv"))

    def test_mehrere_eintraege_sortiert(self, tmp_path):
        p = _schreibe(tmp_path, [
            self.STANDARD_HEADER,
            ["2024-01-22", "09:00", "13:00", "4.0", "X"],
            ["2024-01-08", "09:00", "13:00", "4.0", "X"],
            ["2024-01-15", "09:00", "13:00", "4.0", "X"],
        ])
        eintraege = lese_csv(p)
        assert len(eintraege) == 3
        # Reihenfolge ist CSV-Reihenfolge (kein automatisches Sortieren im Import)
        assert eintraege[0].datum == date(2024, 1, 22)

    def test_leerzeilen_werden_ignoriert(self, tmp_path):
        p = tmp_path / "leer.csv"
        p.write_text(
            "datum;von;bis;stunden;person\n"
            "2024-01-08;09:00;13:00;4.0;X\n"
            "\n"
            "2024-01-15;09:00;13:00;4.0;X\n",
            encoding="utf-8-sig",
        )
        eintraege = lese_csv(p)
        # Leerzeile hat fehlende Felder  Fehler, wird bersprungen
        assert len(eintraege) >= 2


# ------------------------------------------------------------------ #
#  schreibe_csv                                                        #
# ------------------------------------------------------------------ #

class TestSchreibeCsv:

    def test_schreibt_datei(self, tmp_path):
        e = PflegeEintrag.from_datum(date(2024, 1, 8), "09:00", "13:00", 4.0, "Mller")
        pfad = tmp_path / "export.csv"
        schreibe_csv([e], pfad)
        assert pfad.exists()

    def test_roundtrip(self, tmp_path):
        eintraege = [
            PflegeEintrag.from_datum(date(2024, 1, 8),  "09:00", "13:00", 4.0, "Mller"),
            PflegeEintrag.from_datum(date(2024, 1, 15), "10:00", "14:30", 4.5, "Mller"),
        ]
        pfad = tmp_path / "roundtrip.csv"
        schreibe_csv(eintraege, pfad)
        eingelesen = lese_csv(pfad)
        assert len(eingelesen) == 2
        assert eingelesen[0].datum   == date(2024, 1, 8)
        assert eingelesen[1].stunden == 4.5

    def test_erstellt_elternordner(self, tmp_path):
        e = PflegeEintrag.from_datum(date(2024, 1, 8), "09:00", "13:00", 4.0, "X")
        pfad = tmp_path / "tief" / "ordner" / "export.csv"
        schreibe_csv([e], pfad)
        assert pfad.exists()
