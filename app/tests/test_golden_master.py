"""
Golden Master Tests  Pflegra v2.3 ODS als Referenzsystem

Alle Erwartungswerte stammen direkt aus Pflegra_v2_3.ods:
  - Jamie Neu:  Statistik-Sheet (volles Jahr 2026, 12 Monate)
  - Julian Neu: Nachweis-Sheet  (volles Jahr 2026, 12 Monate)

Stundensatz: 20 /h (aus Blanko-Sheet: "Stundensatz : 20")
Budget:      3.539  (gemeinsamer Jahresbetrag ab 01.07.2025)

Feldnamen der Dataclasses (calculations.py):
  MonatsSumme:  .stunden, .kosten, .einsaetze, .tage_tageweise
  JahresSumme:  .stunden, .kosten, .einsaetze, .monate
  BudgetStatus: .verbraucht, .budget_gesamt, .restbudget_gesamt,
                .tage_tageweise, .tage_grenze_erreicht

Zweck:
  Jede nderung an calculations.py die einen dieser Tests bricht,
  ist eine fachliche Regression. Kein stilles Kaputgehen mglich.
"""

import pytest
from datetime import date
from typing import List

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from models import PflegeEintrag
from calculations import (
    berechne_monats_summe,
    berechne_jahres_summe,
    berechne_budget_status,
    berechne_kosten,
    BUDGET_JAHRESBETRAG,
    MAX_TAGE_TAGEWEISE,
)

# ------------------------------------------------------------------ #
#  Konstanten                                                          #
# ------------------------------------------------------------------ #

STUNDENSATZ = 20.0
JAHR = 2026


# ------------------------------------------------------------------ #
#  Hilfsfunktion                                                       #
# ------------------------------------------------------------------ #

def mk(datum: date, stunden: float, person: str,
       art: str = "stundenweise") -> PflegeEintrag:
    return PflegeEintrag.from_datum(
        datum=datum, von="13:00", bis="18:00",
        stunden=stunden, person=person, art=art,
    )


# ------------------------------------------------------------------ #
#  Referenzdaten: Jamie Neu (ODS Statistik-Sheet)                     #
#                                                                      #
#  Monat  | Stunden | Betrag                                          #
#  -------+---------+---------                                         #
#  Jan    |      15 |     300                                          #
#  Feb    |      13 |     260                                          #
#  Mr    |      13 |     260                                          #
#  Apr    |      12 |     240                                          #
#  Mai    |      14 |     280                                          #
#  Jun    |      18 |     360                                          #
#  Jul    |      18 |     360                                          #
#  Aug    |      10 |     200                                          #
#  Sep    |      16 |     320                                          #
#  Okt    |      18 |     360                                          #
#  Nov    |      18 |     360                                          #
#  Dez    |      12 |     240                                          #
#  GESAMT |     177 |   3.540   Budget 3.539  überschritten         #
# ------------------------------------------------------------------ #

JAMIE_H = {1:15, 2:13, 3:13, 4:12, 5:14, 6:18,
           7:18, 8:10, 9:16, 10:18, 11:18, 12:12}

# Kumulative Betrge laut ODS Statistik-Spalte "Kum. ()"
JAMIE_KUM_EUR = [300, 560, 820, 1060, 1340, 1700,
                 2060, 2260, 2580, 2940, 3300, 3540]


def _jamie() -> List[PflegeEintrag]:
    return [mk(date(JAHR, m, 1), float(h), "Jamie Neu")
            for m, h in JAMIE_H.items()]


# ------------------------------------------------------------------ #
#  Referenzdaten: Julian Neu (ODS Nachweis-Sheet)                     #
#                                                                      #
#  Alle Einstze: 5h, stundenweise, freitags 13:0018:00              #
#  GESAMT: 36 Einstze, 180h, 3.600   Budget überschritten         #
# ------------------------------------------------------------------ #

JULIAN_DATEN = [
    date(2026,1,9),  date(2026,1,16), date(2026,1,23), date(2026,1,30),
    date(2026,2,6),  date(2026,2,13), date(2026,2,20), date(2026,2,27),
    date(2026,3,6),  date(2026,3,13), date(2026,3,20), date(2026,3,27),
    date(2026,4,3),  date(2026,4,10), date(2026,4,17), date(2026,4,24),
    date(2026,5,8),  date(2026,5,15), date(2026,5,22), date(2026,5,29),
    date(2026,6,5),  date(2026,6,19),
    date(2026,7,3),  date(2026,7,17), date(2026,7,31),
    date(2026,8,7),  date(2026,8,28),
    date(2026,9,4),  date(2026,9,18),
    date(2026,10,9), date(2026,10,23),
    date(2026,11,6), date(2026,11,20),
    date(2026,12,4), date(2026,12,11), date(2026,12,18),
]

JULIAN_H = {1:20, 2:20, 3:20, 4:20, 5:20, 6:10,
            7:15, 8:10, 9:10, 10:10, 11:10, 12:15}

JULIAN_E = {1:4, 2:4, 3:4, 4:4, 5:4, 6:2,
            7:3, 8:2, 9:2, 10:2, 11:2, 12:3}


def _julian() -> List[PflegeEintrag]:
    return [mk(d, 5.0, "Julian Neu") for d in JULIAN_DATEN]


# ================================================================== #
#  Tests: Konstanten                                                   #
# ================================================================== #

class TestKonstanten:
    def test_budget_jahresbetrag(self):
        assert BUDGET_JAHRESBETRAG == 3539.0

    def test_max_tage_tageweise(self):
        assert MAX_TAGE_TAGEWEISE == 56


# ================================================================== #
#  Tests: Kostenberechnung                                             #
# ================================================================== #

class TestKosten:
    def test_5h_mal_20(self):
        assert berechne_kosten(mk(date(JAHR, 1, 1), 5.0, "T"), 20.0) == 100.0

    def test_jamie_jahresbetrag(self):
        assert berechne_kosten(mk(date(JAHR, 1, 1), 177.0, "T"), 20.0) == 3540.0

    def test_null_stunden(self):
        assert berechne_kosten(mk(date(JAHR, 1, 1), 0.0, "T"), 20.0) == 0.0


# ================================================================== #
#  Tests: Monatssummen  Jamie Neu                                     #
# ================================================================== #

class TestMonatsSummeJamie:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.eintraege = _jamie()

    @pytest.mark.parametrize("monat,h", list(JAMIE_H.items()))
    def test_stunden(self, monat, h):
        ms = berechne_monats_summe(self.eintraege, "Jamie Neu", JAHR, monat, STUNDENSATZ)
        assert ms.stunden == pytest.approx(h, abs=0.01)

    @pytest.mark.parametrize("monat,h", list(JAMIE_H.items()))
    def test_kosten(self, monat, h):
        ms = berechne_monats_summe(self.eintraege, "Jamie Neu", JAHR, monat, STUNDENSATZ)
        assert ms.kosten == pytest.approx(h * 20, abs=0.01)


# ================================================================== #
#  Tests: Jahressumme + kumulative Werte  Jamie Neu                  #
# ================================================================== #

class TestJahresSummeJamie:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.js = berechne_jahres_summe(_jamie(), "Jamie Neu", JAHR, STUNDENSATZ)

    def test_gesamtstunden(self):
        assert self.js.stunden == pytest.approx(177.0, abs=0.01)

    def test_gesamtkosten(self):
        assert self.js.kosten == pytest.approx(3540.0, abs=0.01)

    def test_alle_12_monate(self):
        aktiv = [m for m in self.js.monate if m.einsaetze > 0]
        assert len(aktiv) == 12

    @pytest.mark.parametrize("idx,kum", list(enumerate(JAMIE_KUM_EUR)))
    def test_kumuliert(self, idx, kum):
        """Kumulative Betrge aus ODS Statistik-Sheet Spalte 'Kum. ()'."""
        total = sum(m.kosten for m in self.js.monate[:idx + 1])
        assert total == pytest.approx(kum, abs=0.01)


# ================================================================== #
#  Tests: Budgetstatus  Jamie Neu                                     #
# ================================================================== #

class TestBudgetStatusJamie:
    """ODS: 3.540  verbraucht > 3.539  Budget  überschritten um 1 ."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.bs = berechne_budget_status(_jamie(), "Jamie Neu", JAHR, STUNDENSATZ)

    def test_verbraucht(self):
        assert self.bs.verbraucht == pytest.approx(3540.0, abs=0.01)

    def test_verbleibend(self):
        verbleibend = self.bs.budget_gesamt - self.bs.verbraucht
        assert verbleibend == pytest.approx(-1.0, abs=0.01)

    def test_ueüberschritten(self):
        assert self.bs.verbraucht > self.bs.budget_gesamt

    def test_restbudget_nie_negativ(self):
        """restbudget_gesamt ist max(0, ...)  nie negativ."""
        assert self.bs.restbudget_gesamt >= 0.0


# ================================================================== #
#  Tests: Monatssummen  Julian Neu                                    #
# ================================================================== #

class TestMonatsSummeJulian:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.eintraege = _julian()

    @pytest.mark.parametrize("monat,h", list(JULIAN_H.items()))
    def test_stunden(self, monat, h):
        ms = berechne_monats_summe(self.eintraege, "Julian Neu", JAHR, monat, STUNDENSATZ)
        assert ms.stunden == pytest.approx(h, abs=0.01)

    @pytest.mark.parametrize("monat,h", list(JULIAN_H.items()))
    def test_kosten(self, monat, h):
        ms = berechne_monats_summe(self.eintraege, "Julian Neu", JAHR, monat, STUNDENSATZ)
        assert ms.kosten == pytest.approx(h * 20, abs=0.01)

    @pytest.mark.parametrize("monat,n", list(JULIAN_E.items()))
    def test_einsaetze(self, monat, n):
        ms = berechne_monats_summe(self.eintraege, "Julian Neu", JAHR, monat, STUNDENSATZ)
        assert ms.einsaetze == n


# ================================================================== #
#  Tests: Jahressumme  Julian Neu                                     #
# ================================================================== #

class TestJahresSummeJulian:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.eintraege = _julian()
        self.js = berechne_jahres_summe(self.eintraege, "Julian Neu", JAHR, STUNDENSATZ)

    def test_anzahl_eintraege(self):
        assert len(self.eintraege) == 36

    def test_gesamtstunden(self):
        assert self.js.stunden == pytest.approx(180.0, abs=0.01)

    def test_gesamtkosten(self):
        assert self.js.kosten == pytest.approx(3600.0, abs=0.01)

    def test_alle_12_monate(self):
        aktiv = [m for m in self.js.monate if m.einsaetze > 0]
        assert len(aktiv) == 12


# ================================================================== #
#  Tests: Budgetstatus  Julian Neu                                    #
# ================================================================== #

class TestBudgetStatusJulian:
    """180h  20  = 3.600  > 3.539   überschritten um 61 ."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.bs = berechne_budget_status(_julian(), "Julian Neu", JAHR, STUNDENSATZ)

    def test_verbraucht(self):
        assert self.bs.verbraucht == pytest.approx(3600.0, abs=0.01)

    def test_verbleibend(self):
        verbleibend = self.bs.budget_gesamt - self.bs.verbraucht
        assert verbleibend == pytest.approx(-61.0, abs=0.01)

    def test_ueüberschritten(self):
        assert self.bs.verbraucht > self.bs.budget_gesamt

    def test_keine_tageweise_eintraege(self):
        assert self.bs.tage_tageweise == 0

    def test_keine_56_tage_grenze(self):
        assert self.bs.tage_grenze_erreicht is False


# ================================================================== #
#  Tests: Grenzflle                                                   #
# ================================================================== #

class TestGrenzfaelle:
    def test_leere_eintraege(self):
        js = berechne_jahres_summe([], "X", JAHR, STUNDENSATZ)
        assert js.stunden == 0.0
        assert js.kosten == 0.0

    def test_budget_exakt_ausgeschoepft(self):
        """3.539  exakt  nicht überschritten, Restbudget = 0."""
        bs = berechne_budget_status(
            [mk(date(JAHR, 1, 1), 3539 / 20, "T")], "T", JAHR, STUNDENSATZ
        )
        verbl = bs.budget_gesamt - bs.verbraucht
        assert verbl == pytest.approx(0.0, abs=0.01)
        assert not (bs.verbraucht > bs.budget_gesamt)

    def test_um_1_euro_ueüberschritten(self):
        """177h  20  = 3.540  = Budget + 1 . Wie Jamie."""
        bs = berechne_budget_status(
            [mk(date(JAHR, 1, 1), 177.0, "T")], "T", JAHR, STUNDENSATZ
        )
        verbl = bs.budget_gesamt - bs.verbraucht
        assert verbl == pytest.approx(-1.0, abs=0.01)
        assert bs.verbraucht > bs.budget_gesamt

    def test_falsche_person_liefert_null(self):
        js = berechne_jahres_summe(_jamie(), "Jemand Anders", JAHR, STUNDENSATZ)
        assert js.stunden == 0.0

    def test_falsches_jahr_liefert_null(self):
        js = berechne_jahres_summe(_julian(), "Julian Neu", 2025, STUNDENSATZ)
        assert js.stunden == 0.0

    def test_56_tage_grenze_exakt(self):
        """56 tageweise Eintrge  Grenze exakt erreicht."""
        eintraege = []
        for i in range(56):
            m = (i // 28) + 1
            t = (i % 28) + 1
            eintraege.append(mk(date(JAHR, m, t), 8.0, "T", art="tageweise"))
        bs = berechne_budget_status(eintraege, "T", JAHR, STUNDENSATZ)
        assert bs.tage_tageweise == 56
        assert bs.tage_grenze_erreicht is True

    def test_57_tage_ueber_grenze(self):
        """57 tageweise Eintrge  Grenze überschritten."""
        eintraege = []
        for i in range(56):
            m = (i // 28) + 1
            t = (i % 28) + 1
            eintraege.append(mk(date(JAHR, m, t), 8.0, "T", art="tageweise"))
        eintraege.append(mk(date(JAHR, 3, 15), 8.0, "T", art="tageweise"))
        bs = berechne_budget_status(eintraege, "T", JAHR, STUNDENSATZ)
        assert bs.tage_tageweise == 57
        assert bs.tage_grenze_erreicht is True
