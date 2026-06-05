"""Tests fr calculations.py."""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from models import PflegeEintrag
from calculations import (
    berechne_kosten,
    berechne_monats_summe,
    berechne_jahres_summe,
    berechne_budget_status,
    berechne_prognose,
    alle_personen_budget,
    BUDGET_VERHINDERUNGSPFLEGE,
    BUDGET_AUFSTOCKUNG_MAX,
    BUDGET_GESAMT_MAX,
    STUNDENSATZ_DEFAULT,
)


# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

def _eintrag(datum: date, stunden: float, person: str = "Test") -> PflegeEintrag:
    return PflegeEintrag.from_datum(datum, "09:00", "13:00", stunden, person)


@pytest.fixture
def standard_eintraege():
    """4 Eintrge Januar + 3 Eintrge Februar fr 'Mller, Hans'."""
    return [
        _eintrag(date(2024, 1,  8), 4.0, "Mller, Hans"),
        _eintrag(date(2024, 1, 15), 4.5, "Mller, Hans"),
        _eintrag(date(2024, 1, 22), 4.0, "Mller, Hans"),
        _eintrag(date(2024, 1, 29), 4.0, "Mller, Hans"),
        _eintrag(date(2024, 2,  5), 5.0, "Mller, Hans"),
        _eintrag(date(2024, 2, 12), 3.0, "Mller, Hans"),
        _eintrag(date(2024, 2, 19), 4.0, "Mller, Hans"),
    ]


# ------------------------------------------------------------------ #
#  berechne_kosten                                                     #
# ------------------------------------------------------------------ #

class TestBerechneKosten:

    def test_standard_stundensatz(self):
        e = _eintrag(date(2024, 1, 8), 4.0)
        assert berechne_kosten(e) == 4.0 * STUNDENSATZ_DEFAULT

    def test_benutzerdefinierter_stundensatz(self):
        e = _eintrag(date(2024, 1, 8), 3.5)
        assert berechne_kosten(e, stundensatz=30.0) == pytest.approx(105.0)

    def test_null_stunden(self):
        e = _eintrag(date(2024, 1, 8), 0.0)
        assert berechne_kosten(e) == 0.0

    def test_rundung_auf_zwei_dezimalstellen(self):
        e = _eintrag(date(2024, 1, 8), 1.0/3)
        kosten = berechne_kosten(e, stundensatz=10.0)
        assert round(kosten, 2) == kosten   # maximal 2 Nachkommastellen


# ------------------------------------------------------------------ #
#  berechne_monats_summe                                               #
# ------------------------------------------------------------------ #

class TestBerechneMonatsSumme:

    def test_januar_4_eintraege(self, standard_eintraege):
        ms = berechne_monats_summe(standard_eintraege, "Mller, Hans", 2024, 1)
        assert ms.einsaetze == 4
        assert ms.stunden   == pytest.approx(16.5)
        assert ms.kosten    == pytest.approx(16.5 * STUNDENSATZ_DEFAULT)

    def test_leerer_monat(self, standard_eintraege):
        ms = berechne_monats_summe(standard_eintraege, "Mller, Hans", 2024, 3)
        assert ms.einsaetze == 0
        assert ms.stunden   == 0.0
        assert ms.kosten    == 0.0

    def test_falsche_person(self, standard_eintraege):
        ms = berechne_monats_summe(standard_eintraege, "Schmidt, Anna", 2024, 1)
        assert ms.einsaetze == 0

    def test_monat_name(self, standard_eintraege):
        ms = berechne_monats_summe(standard_eintraege, "Mller, Hans", 2024, 1)
        assert ms.monat_name == "Januar"

    def test_str_ausgabe_enthaelt_daten(self, standard_eintraege):
        ms = berechne_monats_summe(standard_eintraege, "Mller, Hans", 2024, 1)
        s = str(ms)
        assert "Januar" in s
        assert "Mller, Hans" in s


# ------------------------------------------------------------------ #
#  berechne_jahres_summe                                               #
# ------------------------------------------------------------------ #

class TestBerechneJahresSumme:

    def test_gesamt_stunden(self, standard_eintraege):
        js = berechne_jahres_summe(standard_eintraege, "Mller, Hans", 2024)
        erwartete_stunden = 4.0 + 4.5 + 4.0 + 4.0 + 5.0 + 3.0 + 4.0
        assert js.stunden == pytest.approx(erwartete_stunden)

    def test_gesamt_einsaetze(self, standard_eintraege):
        js = berechne_jahres_summe(standard_eintraege, "Mller, Hans", 2024)
        assert js.einsaetze == 7

    def test_monate_hat_12_eintraege(self, standard_eintraege):
        js = berechne_jahres_summe(standard_eintraege, "Mller, Hans", 2024)
        assert len(js.monate) == 12

    def test_abgerechnete_monate(self, standard_eintraege):
        js = berechne_jahres_summe(standard_eintraege, "Mller, Hans", 2024)
        assert js.abgerechnete_monate == [1, 2]

    def test_kosten_stimmen(self, standard_eintraege):
        js = berechne_jahres_summe(standard_eintraege, "Mller, Hans", 2024)
        assert js.kosten == pytest.approx(js.stunden * STUNDENSATZ_DEFAULT)


# ------------------------------------------------------------------ #
#  berechne_budget_status                                              #
# ------------------------------------------------------------------ #

class TestBerechneBudgetStatus:

    def test_grundwerte(self, standard_eintraege):
        bs = berechne_budget_status(standard_eintraege, "Mller, Hans", 2026)
        assert bs.budget_basis      == BUDGET_VERHINDERUNGSPFLEGE
        assert bs.budget_aufstockung == BUDGET_AUFSTOCKUNG_MAX
        assert bs.budget_gesamt      == BUDGET_GESAMT_MAX

    def test_verbraucht_korrekt(self, standard_eintraege):
        js = berechne_jahres_summe(standard_eintraege, "Mller, Hans", 2024)
        bs = berechne_budget_status(standard_eintraege, "Mller, Hans", 2024)
        assert bs.verbraucht == pytest.approx(js.kosten)

    def test_restbudget_nicht_negativ(self, standard_eintraege):
        # Viele Stunden hinzufgen  Budget knapp
        viele = standard_eintraege + [
            _eintrag(date(2024, m, 1), 10.0, "Mller, Hans")
            for m in range(3, 13)
        ]
        bs = berechne_budget_status(viele, "Mller, Hans", 2024)
        assert bs.restbudget_basis   >= 0.0
        assert bs.restbudget_gesamt  >= 0.0

    def test_ausgeschoepft_prozent_max_100(self, standard_eintraege):
        # Sehr viele Stunden  weit ber Budget
        viele = [_eintrag(date(2024, m, 1), 20.0, "Mller, Hans") for m in range(1, 13)]
        bs = berechne_budget_status(viele, "Mller, Hans", 2024)
        assert bs.ausgeschoepft_prozent == pytest.approx(100.0)

    def test_restbudget_in_stunden(self, standard_eintraege):
        bs = berechne_budget_status(standard_eintraege, "Mller, Hans", 2024)
        erwartete_stunden = bs.restbudget_gesamt / STUNDENSATZ_DEFAULT
        assert bs.restbudget_in_stunden == pytest.approx(erwartete_stunden)

    def test_ist_im_basis_budget_true(self, standard_eintraege):
        bs = berechne_budget_status(standard_eintraege, "Mller, Hans", 2024)
        # 28.5 h * 25 /h = 712.50  < 1612 
        assert bs.ist_im_basis_budget is True

    def test_aufstockung_genutzt_null_wenn_unter_basis(self, standard_eintraege):
        bs = berechne_budget_status(standard_eintraege, "Mller, Hans", 2024)
        assert bs.aufstockung_genutzt == 0.0


# ------------------------------------------------------------------ #
#  berechne_prognose                                                   #
# ------------------------------------------------------------------ #

class TestBerechnePrognose:

    def test_keine_eintraege_gibt_null_prognose(self):
        p = berechne_prognose([], "Unbekannt", 2024)
        assert p.hochrechnung_stunden == 0.0
        assert p.hochrechnung_kosten  == 0.0
        assert p.budget_wird_ueüberschritten is False

    def test_linear_hochrechnung_2_monate(self, standard_eintraege):
        p = berechne_prognose(standard_eintraege, "Mller, Hans", 2024)
        assert p.abgeschlossene_monate == 2
        # Jan: 16.5h, Feb: 12h   14.25h/Monat  12 * 14.25 = 171h
        assert p.hochrechnung_stunden == pytest.approx(171.0)
        # 171h * 20€/h = 3420 > 3386 (Budget 2024) → Überschreitung
        assert p.hochrechnung_kosten == pytest.approx(3420.0, abs=0.01)
        assert p.budget_gesamt == pytest.approx(3386.0, abs=0.01)
        assert p.budget_wird_ueüberschritten is True
        assert p.differenz < 0

    def test_ueberschreitung_wird_erkannt(self):
        viele = [_eintrag(date(2024, m, 1), 15.0, "X") for m in range(1, 13)]
        p = berechne_prognose(viele, "X", 2024)
        # 10h * 20€ * 12 = 2400 < 3386 → kein Überschreitung bei 2024-Budget
        assert p.budget_wird_ueüberschritten is True
        assert p.differenz < 0

    def test_im_budget_wenn_stunden_gering(self):
        # Budget-Grenze 2024: 3386€ / 20€/h = 169.3h/Jahr
        wenige = [_eintrag(date(2024, m, 1), 6.0, "X") for m in range(1, 4)]
        p = berechne_prognose(wenige, "X", 2024)
        # 6h * 20€ * 12 = 1440 < 3386
        assert p.budget_wird_ueüberschritten is False
        assert p.differenz > 0

    def test_str_enthaelt_person(self, standard_eintraege):
        p = berechne_prognose(standard_eintraege, "Mller, Hans", 2024)
        assert "Mller, Hans" in str(p)


# ------------------------------------------------------------------ #
#  alle_personen_budget                                                 #
# ------------------------------------------------------------------ #

class TestAllePersonenBudget:

    def test_mehrere_personen(self, standard_eintraege):
        anna = [_eintrag(date(2024, 1, 10), 3.0, "Schmidt, Anna")]
        bs_liste = alle_personen_budget(standard_eintraege + anna, 2024)
        personen = {bs.person for bs in bs_liste}
        assert "Mller, Hans"  in personen
        assert "Schmidt, Anna" in personen

    def test_falsches_jahr_leer(self, standard_eintraege):
        bs_liste = alle_personen_budget(standard_eintraege, 2023)
        assert bs_liste == []
