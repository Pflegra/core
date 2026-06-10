"""
Tests: Jahreslogik-Testmatrix — berechne_prognose

Prüft jahresspezifisches Budget in der Prognoseberechnung.
Kernaussage: berechne_prognose(eintraege, person, jahr) nutzt immer
das korrekte Budget für das angegebene Jahr aus pflege_rules.py.

Testmatrix:
    Jahr  | Budget  | Überschreitung bei X Stunden
    2024  | 3386€   | > 169.3h/Jahr
    2025  | 3539€   | > 176.95h/Jahr
    2026  | 3539€   | > 176.95h/Jahr
"""

import pytest
from datetime import date
from typing import List

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from models import PflegeEintrag
from calculations import berechne_prognose
from pflege_rules import get_regelwerk

STUNDENSATZ = 20.0


def mk(d: date, h: float, p: str = "Test") -> PflegeEintrag:
    return PflegeEintrag.from_datum(
        datum=d, von="08:00", bis="12:00", stunden=h, person=p,
    )


def eintraege_fuer_monate(jahr: int, monate: int, stunden_pro_monat: float) -> List[PflegeEintrag]:
    return [mk(date(jahr, m, 1), stunden_pro_monat) for m in range(1, monate + 1)]


# ── Budget jahresspezifisch ────────────────────────────────────────────────────

class TestPrognoseJahresspezifisch:
    @pytest.mark.parametrize("jahr,erwartetes_budget", [
        (2024, 3386.0),
        (2025, 3539.0),
        (2026, 3539.0),
    ])
    def test_budget_korrekt_fuer_jahr(self, jahr, erwartetes_budget):
        """Budget in Prognose muss dem jeweiligen Jahr entsprechen."""
        eintraege = eintraege_fuer_monate(jahr, 6, 10.0)
        p = berechne_prognose(eintraege, "Test", jahr, STUNDENSATZ)
        assert p.budget_gesamt == pytest.approx(erwartetes_budget, abs=0.01), \
            f"Jahr {jahr}: erwartet {erwartetes_budget}€, bekommen {p.budget_gesamt}€"

    def test_2024_nutzt_nicht_2025_budget(self):
        """2024-Prognose darf nicht 3539€ verwenden."""
        eintraege = eintraege_fuer_monate(2024, 6, 10.0)
        p = berechne_prognose(eintraege, "Test", 2024, STUNDENSATZ)
        assert p.budget_gesamt != pytest.approx(3539.0, abs=0.01)
        assert p.budget_gesamt == pytest.approx(3386.0, abs=0.01)

    def test_explizites_budget_wird_respektiert(self):
        """Wenn budget_gesamt explizit übergeben wird, wird es verwendet."""
        eintraege = eintraege_fuer_monate(2026, 6, 10.0)
        p = berechne_prognose(eintraege, "Test", 2026, STUNDENSATZ, budget_gesamt=5000.0)
        assert p.budget_gesamt == pytest.approx(5000.0, abs=0.01)


# ── Überschreitung jahresspezifisch ──────────────────────────────────────────

class TestPrognoseUeberschreitung:
    def test_2024_ueberschreitung_bei_170h(self):
        """170h * 20€ = 3400€ > 3386€ (Budget 2024) → Überschreitung."""
        # 6 Monate * 14.2h/Monat ≈ 85.2h → Prognose 12 * 14.2 = 170.4h
        eintraege = eintraege_fuer_monate(2024, 6, 14.2)
        p = berechne_prognose(eintraege, "Test", 2024, STUNDENSATZ)
        assert p.hochrechnung_kosten > p.budget_gesamt
        assert p.budget_wird_ueüberschritten is True
        assert p.differenz < 0

    def test_2024_kein_ueberschreitung_bei_140h(self):
        """140h * 20€ = 2800€ < 3386€ (Budget 2024) → keine Überschreitung."""
        eintraege = eintraege_fuer_monate(2024, 6, 11.67)  # 12 * 11.67 ≈ 140h
        p = berechne_prognose(eintraege, "Test", 2024, STUNDENSATZ)
        assert p.budget_wird_ueüberschritten is False
        assert p.differenz > 0

    def test_2025_ueberschreitung_bei_180h(self):
        """180h * 20€ = 3600€ > 3539€ (Budget 2025) → Überschreitung."""
        eintraege = eintraege_fuer_monate(2025, 6, 15.0)
        p = berechne_prognose(eintraege, "Test", 2025, STUNDENSATZ)
        assert p.budget_wird_ueüberschritten is True

    def test_2025_kein_ueberschreitung_bei_170h(self):
        """170h * 20€ = 3400€ < 3539€ (Budget 2025) → keine Überschreitung."""
        eintraege = eintraege_fuer_monate(2025, 6, 14.16)
        p = berechne_prognose(eintraege, "Test", 2025, STUNDENSATZ)
        assert p.budget_wird_ueüberschritten is False

    def test_grenzfall_exakt_budget_2026(self):
        """Prognose exakt = Budget → keine Überschreitung."""
        # 3539 / 20 / 12 = 14.745h/Monat
        eintraege = eintraege_fuer_monate(2026, 6, 14.745)
        p = berechne_prognose(eintraege, "Test", 2026, STUNDENSATZ)
        assert p.budget_wird_ueüberschritten is False
        assert p.differenz >= 0


# ── Konsistenz mit berechne_budget_status ────────────────────────────────────

class TestPrognoseKonsistenz:
    def test_prognose_und_budget_nutzen_gleiches_jahresbudget(self):
        """Prognose und BudgetStatus müssen dasselbe Budget für ein Jahr verwenden."""
        from calculations import berechne_budget_status
        eintraege = eintraege_fuer_monate(2024, 12, 10.0)
        prognose = berechne_prognose(eintraege, "Test", 2024, STUNDENSATZ)
        budget = berechne_budget_status(eintraege, "Test", 2024, STUNDENSATZ)
        assert prognose.budget_gesamt == pytest.approx(budget.budget_gesamt, abs=0.01)

    @pytest.mark.parametrize("jahr", [2024, 2025, 2026])
    def test_prognose_budget_entspricht_regelwerk(self, jahr):
        """Prognose-Budget muss exakt dem Regelwerk-Budget entsprechen."""
        regeln = get_regelwerk(jahr)
        eintraege = eintraege_fuer_monate(jahr, 3, 10.0)
        p = berechne_prognose(eintraege, "Test", jahr, STUNDENSATZ)
        assert p.budget_gesamt == pytest.approx(regeln.vp_budget_jahresbetrag, abs=0.01)


# ── Randfälle ─────────────────────────────────────────────────────────────────

class TestPrognoseRandfaelle:
    def test_keine_eintraege(self):
        p = berechne_prognose([], "Test", 2026, STUNDENSATZ)
        assert p.hochrechnung_stunden == 0.0
        assert p.budget_wird_ueüberschritten is False
        assert p.budget_gesamt == pytest.approx(3539.0, abs=0.01)

    def test_ein_monat_hochrechnung(self):
        """Ein Monat mit 20h → Prognose 240h/Jahr."""
        eintraege = [mk(date(2026, 1, 1), 20.0)]
        p = berechne_prognose(eintraege, "Test", 2026, STUNDENSATZ)
        assert p.hochrechnung_stunden == pytest.approx(240.0, abs=0.01)
        assert p.abgeschlossene_monate == 1

    def test_12_monate_keine_hochrechnung(self):
        """12 Monate vorhanden → Prognose = tatsächlicher Wert."""
        eintraege = eintraege_fuer_monate(2026, 12, 10.0)
        p = berechne_prognose(eintraege, "Test", 2026, STUNDENSATZ)
        assert p.hochrechnung_stunden == pytest.approx(120.0, abs=0.01)
        assert p.abgeschlossene_monate == 12
