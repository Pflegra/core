"""
Tests für pflege_rules.py — jahresspezifische Regelwerke

Prüft:
- Korrekte Beträge pro Jahr
- Fallback auf nächstälteres Jahr
- Pflegegeld-Sätze
- Halbierungsberechnung
- Jahreswechsel-Verhalten in Berechnungen
"""

import pytest
from datetime import date

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from pflege_rules import get_regelwerk, get_regelwerk_fuer_datum, REGELWERKE, REGELN_AKTUELL
from models import PflegeEintrag
from calculations import berechne_budget_status, berechne_jahres_summe


def mk(datum: date, stunden: float, person: str = "Test",
       art: str = "stundenweise") -> PflegeEintrag:
    return PflegeEintrag.from_datum(
        datum=datum, von="08:00", bis="12:00",
        stunden=stunden, person=person, art=art,
    )


# ── Regelwerk-Abruf ────────────────────────────────────────────────────────────

class TestRegelwerkAbruf:
    def test_2024_vorhanden(self):
        r = get_regelwerk(2024)
        assert r.jahr == 2024

    def test_2025_vorhanden(self):
        r = get_regelwerk(2025)
        assert r.jahr == 2025

    def test_2026_vorhanden(self):
        r = get_regelwerk(2026)
        assert r.jahr == 2026

    def test_unbekanntes_jahr_fallback(self):
        """Unbekanntes Jahr → nächstälteres bekanntes Jahr."""
        r = get_regelwerk(2099)
        assert r.jahr <= 2099

    def test_sehr_altes_jahr_fallback(self):
        """Sehr altes Jahr → ältestes bekanntes Regelwerk."""
        r = get_regelwerk(2000)
        assert r is not None

    def test_fuer_datum(self):
        r = get_regelwerk_fuer_datum(date(2026, 6, 15))
        assert r.jahr == 2026

    def test_regelwerke_nicht_leer(self):
        assert len(REGELWERKE) >= 3


# ── Budget-Beträge ─────────────────────────────────────────────────────────────

class TestBudgetBetraege:
    def test_2024_budget(self):
        r = get_regelwerk(2024)
        assert r.vp_budget_jahresbetrag == pytest.approx(3386.0, abs=0.01)

    def test_2025_budget(self):
        r = get_regelwerk(2025)
        assert r.vp_budget_jahresbetrag == pytest.approx(3539.0, abs=0.01)

    def test_2026_budget(self):
        r = get_regelwerk(2026)
        assert r.vp_budget_jahresbetrag == pytest.approx(3539.0, abs=0.01)

    def test_56_tage_alle_jahre(self):
        """56-Tage-Grenze ist in allen bekannten Jahren gleich."""
        for jahr, r in REGELWERKE.items():
            assert r.vp_max_tage_tageweise == 56, f"Jahr {jahr}: erwartet 56 Tage"

    def test_8h_grenze_tageweise(self):
        for r in REGELWERKE.values():
            assert r.vp_stunden_grenze_tageweise == 8.0


# ── Pflegegeld-Sätze ──────────────────────────────────────────────────────────

class TestPflegegeldSaetze:
    def test_2025_pg2(self):
        r = get_regelwerk(2025)
        assert r.pflegegeld_monatlich(2) == pytest.approx(347.0, abs=0.01)

    def test_2025_pg3(self):
        r = get_regelwerk(2025)
        assert r.pflegegeld_monatlich(3) == pytest.approx(599.0, abs=0.01)

    def test_2025_pg4(self):
        r = get_regelwerk(2025)
        assert r.pflegegeld_monatlich(4) == pytest.approx(800.0, abs=0.01)

    def test_2025_pg5(self):
        r = get_regelwerk(2025)
        assert r.pflegegeld_monatlich(5) == pytest.approx(990.0, abs=0.01)

    def test_pg1_immer_null(self):
        for r in REGELWERKE.values():
            assert r.pflegegeld_monatlich(1) == 0.0

    def test_pflegegrad_0_liefert_null(self):
        r = get_regelwerk(2026)
        assert r.pflegegeld_monatlich(0) == 0.0

    def test_pflegegrad_6_liefert_null(self):
        r = get_regelwerk(2026)
        assert r.pflegegeld_monatlich(6) == 0.0

    def test_2024_vs_2025_pg3_gestiegen(self):
        r24 = get_regelwerk(2024)
        r25 = get_regelwerk(2025)
        assert r25.pflegegeld_monatlich(3) > r24.pflegegeld_monatlich(3)


# ── Halbierungsberechnung ─────────────────────────────────────────────────────

class TestHalbierung:
    def test_pg3_halbierung_2026(self):
        """PG3 2026: 599€ / 30 / 2 = 9,98€ pro Tag."""
        r = get_regelwerk(2026)
        h = r.pflegegeld_halbierung_pro_tag(3)
        assert h == pytest.approx(9.98, abs=0.01)

    def test_pg2_halbierung_2026(self):
        """PG2 2026: 347€ / 30 / 2 = 5,78€."""
        r = get_regelwerk(2026)
        h = r.pflegegeld_halbierung_pro_tag(2)
        assert h == pytest.approx(5.78, abs=0.01)

    def test_pg1_halbierung_null(self):
        r = get_regelwerk(2026)
        assert r.pflegegeld_halbierung_pro_tag(1) == 0.0


# ── Tageweise-Grenze ─────────────────────────────────────────────────────────

class TestTageweiseGrenze:
    def test_55_tage_nicht_erreicht(self):
        r = get_regelwerk(2026)
        assert r.tageweise_grenze_erreicht(55) is False

    def test_56_tage_erreicht(self):
        r = get_regelwerk(2026)
        assert r.tageweise_grenze_erreicht(56) is True

    def test_57_tage_erreicht(self):
        r = get_regelwerk(2026)
        assert r.tageweise_grenze_erreicht(57) is True

    def test_44_tage_nahe_80pct(self):
        """80% von 56 = int(44.8) = 44 → ab 44 Tagen Warnung."""
        r = get_regelwerk(2026)
        assert r.tageweise_grenze_nahe(43) is False
        assert r.tageweise_grenze_nahe(44) is True

    def test_0_tage_nicht_nahe(self):
        r = get_regelwerk(2026)
        assert r.tageweise_grenze_nahe(0) is False


# ── Jahreswechsel in Berechnungen ─────────────────────────────────────────────

class TestJahreswechsel:
    def test_dez_jan_getrennt(self):
        """Einträge Dez 2025 und Jan 2026 werden separat summiert."""
        eintraege = [
            mk(date(2025, 12, 31), 10.0),
            mk(date(2026, 1, 1),   10.0),
        ]
        js_2025 = berechne_jahres_summe(eintraege, "Test", 2025, 20.0)
        js_2026 = berechne_jahres_summe(eintraege, "Test", 2026, 20.0)
        assert js_2025.stunden == pytest.approx(10.0, abs=0.01)
        assert js_2026.stunden == pytest.approx(10.0, abs=0.01)

    def test_budget_jahresspezifisch(self):
        """Budget 2024 != Budget 2025."""
        eintraege_2024 = [mk(date(2024, 6, 1), 169.3)]  # = 3386€ exakt
        eintraege_2025 = [mk(date(2025, 6, 1), 176.95)]  # = 3539€ exakt

        bs_2024 = berechne_budget_status(eintraege_2024, "Test", 2024, 20.0)
        bs_2025 = berechne_budget_status(eintraege_2025, "Test", 2025, 20.0)

        assert bs_2024.budget_gesamt == pytest.approx(3386.0, abs=0.01)
        assert bs_2025.budget_gesamt == pytest.approx(3539.0, abs=0.01)

    def test_jahreswechsel_kein_ueberlauf(self):
        """Einträge aus Vorjahr beeinflussen nicht das aktuelle Jahr."""
        vj_eintraege = [mk(date(2025, m, 1), 30.0) for m in range(1, 13)]
        bs = berechne_budget_status(vj_eintraege, "Test", 2026, 20.0)
        assert bs.verbraucht == pytest.approx(0.0, abs=0.01)

    def test_29_februar_schaltjahr(self):
        """29. Februar in Schaltjahr wird korrekt verarbeitet."""
        e = mk(date(2028, 2, 29), 5.0)  # 2028 ist Schaltjahr
        js = berechne_jahres_summe([e], "Test", 2028, 20.0)
        assert js.stunden == pytest.approx(5.0, abs=0.01)
        assert js.monate[1].stunden == pytest.approx(5.0, abs=0.01)  # Februar = Index 1
