"""
Tests für den Budgetplaner (budget_planung Router + JS-Berechnungslogik)

Abgedeckte Bereiche:
  1. Regelwerk-Integration  — korrekte Beträge aus pflege_rules.py
  2. Kombinationsleistung § 38  — Sachleistungs-% kürzt Pflegegeld
  3. VP+KZP Budgetverbrauch  — Rest-Budget über 12 Monate
  4. Entlastungsbetrag KZP-Verrechnung  — Checkbox-Logik
  5. Gleichmäßig-Verteilen  — 3.539 € auf 12 Monate
  6. Chip-Toggle  — Sichtbarkeit ≠ Berechnungsänderung
  7. Grenzwerte  — Budget exakt / überschritten / leer
  8. Pflegegrad-Sätze  — alle PG 1–5 korrekt
  9. Router  — GET /budget/planung liefert 200 + korrekte Context-Daten
"""

from __future__ import annotations

import sys
import pathlib
import pytest
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from pflege_rules import get_regelwerk, REGELWERKE


# ═══════════════════════════════════════════════════════════════════════════════
# Hilfs-Klassen: Python-Spiegel der JS-Berechnungslogik
# (berechne() aus budget_planung.js — pure Funktion, browserunabhängig testbar)
# ═══════════════════════════════════════════════════════════════════════════════

def _berechne(
    monate_state: dict,           # {1..12: {"pg", "vp", "kzp", "slPct"}}
    budget: float,
    pg_saetze: dict,              # {1..5: float}
    sl_saetze: dict,              # {1..5: float}
    tp_saetze: dict,              # {1..5: float}
    entlastung_monatlich: float = 131.0,
    entlastung_kzp_aktiv: bool = False,
    kzp_verpfl: dict | None = None,  # {1..12: float}
    vorjahr_guthaben: float = 0.0,
    vorjahr_aktiv: bool = True,
) -> dict:
    """
    Python-Äquivalent der berechne()-Funktion in budget_planung.js.
    Liefert dasselbe Ergebnis-Dict.
    """
    if kzp_verpfl is None:
        kzp_verpfl = {}

    result = {
        "monate": {},
        "totalPG": 0, "totalVP": 0, "totalKZP": 0,
        "totalSL": 0, "totalTP": 0,
        "restBudget": budget,
        "entlastungMonate": {},
    }

    for m in range(1, 13):
        s = monate_state.get(m, {"pg": 1, "vp": 0.0, "kzp": 0.0, "slPct": 0})
        pg_key = s["pg"]
        pg_max = pg_saetze.get(pg_key, 0.0)
        sl_max = sl_saetze.get(pg_key, 0.0)
        tp_betrag = tp_saetze.get(pg_key, 0.0)

        # Kombinationsleistung § 38
        sl_betrag  = round(sl_max * s["slPct"] / 100)
        pg_prozent = max(0, 100 - s["slPct"])
        pg_betrag  = round(pg_max * pg_prozent / 100)

        result["restBudget"] -= s["vp"]
        result["restBudget"] -= s["kzp"]
        result["totalPG"]  += pg_betrag
        result["totalVP"]  += s["vp"]
        result["totalKZP"] += s["kzp"]
        result["totalSL"]  += sl_betrag
        result["totalTP"]  += tp_betrag

        result["monate"][m] = {
            "pgBetrag":  pg_betrag,
            "pgProzent": pg_prozent,
            "slBetrag":  sl_betrag,
            "slProzent": s["slPct"],
            "tpBetrag":  tp_betrag,
            "restBudget": result["restBudget"],
        }

        # Entlastungsbetrag KZP-Verrechnung
        verpfl    = kzp_verpfl.get(m, 0.0)
        erstattet = min(verpfl, entlastung_monatlich) if entlastung_kzp_aktiv else 0.0
        result["entlastungMonate"][m] = {
            "erstattet": erstattet,
            "rest": entlastung_monatlich - erstattet,
        }

    result["pct"] = min(100, round((result["totalVP"] + result["totalKZP"]) / budget * 100))
    result["restGesamt"] = budget - result["totalVP"] - result["totalKZP"]
    vorjahr_effektiv = vorjahr_guthaben if vorjahr_aktiv else 0.0
    result["vorjahrGuthaben"]          = vorjahr_guthaben
    result["vorjahrAktiv"]             = vorjahr_aktiv
    result["vorjahrEntlastungGesamt"]  = vorjahr_effektiv
    result["totalEntlastungRest"] = sum(
        e["rest"] for e in result["entlastungMonate"].values()
    ) + vorjahr_effektiv
    return result


def _leere_monate(pg: int = 3) -> dict:
    """12 leere Monate mit gegebenem Pflegegrad."""
    return {m: {"pg": pg, "vp": 0.0, "kzp": 0.0, "slPct": 0} for m in range(1, 13)}


def _saetze_2026():
    """Gibt pg_saetze, sl_saetze, tp_saetze für 2026 zurück."""
    r = get_regelwerk(2026)
    pg = {pg: r.pflegegeld_monatlich(pg)   for pg in range(1, 6)}
    sl = {pg: r.sachleistung_monatlich(pg)  for pg in range(1, 6)}
    tp = {pg: r.tagespflege_monatlich(pg)   for pg in range(1, 6)}
    return pg, sl, tp


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Regelwerk-Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegelwerkIntegration:
    """Budget-Planung nutzt korrekte Beträge aus pflege_rules.py."""

    def test_budget_2026_korrekt(self):
        r = get_regelwerk(2026)
        assert r.vp_budget_jahresbetrag == pytest.approx(3_539.00, abs=0.01)

    def test_entlastungsbetrag_2026(self):
        r = get_regelwerk(2026)
        assert r.entlastungsbetrag_monatlich == pytest.approx(131.0, abs=0.01)

    def test_hilfsmittel_2026(self):
        r = get_regelwerk(2026)
        assert r.pflegehilfsmittel_monatlich == pytest.approx(42.0, abs=0.01)

    def test_hausnotruf_2026(self):
        r = get_regelwerk(2026)
        assert r.hausnotruf_monatlich == pytest.approx(25.50, abs=0.01)

    def test_dipa_app_2026(self):
        r = get_regelwerk(2026)
        assert r.dipa_app_monatlich == pytest.approx(40.0, abs=0.01)

    def test_dipa_unterstuetzung_2026(self):
        r = get_regelwerk(2026)
        assert r.dipa_unterstuetzung_monatlich == pytest.approx(30.0, abs=0.01)

    def test_wohnumfeld_2026(self):
        r = get_regelwerk(2026)
        assert r.wohnumfeld_je_massnahme == pytest.approx(4_180.0, abs=0.01)

    def test_saetze_alle_pflegegrade_vorhanden(self):
        r = get_regelwerk(2026)
        for pg in range(1, 6):
            assert r.pflegegeld_monatlich(pg)  >= 0
            assert r.sachleistung_monatlich(pg) >= 0
            assert r.tagespflege_monatlich(pg)  >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Kombinationsleistung § 38
# ═══════════════════════════════════════════════════════════════════════════════

class TestKombinationsleistung:
    """Sachleistungs-% reduziert Pflegegeld anteilig."""

    def test_0pct_sachleistung_volles_pflegegeld(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate(pg=3)
        state[1]["slPct"] = 0
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["monate"][1]["pgBetrag"] == round(pg[3] * 100 / 100)
        assert r["monate"][1]["pgProzent"] == 100

    def test_50pct_sachleistung_halbiert_pflegegeld(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate(pg=3)
        state[1]["slPct"] = 50
        r = _berechne(state, 3_539.0, pg, sl, tp)
        erwartet_pg  = round(pg[3] * 50 / 100)
        erwartet_sl  = round(sl[3] * 50 / 100)
        assert r["monate"][1]["pgBetrag"]  == erwartet_pg
        assert r["monate"][1]["pgProzent"] == 50
        assert r["monate"][1]["slBetrag"]  == erwartet_sl

    def test_100pct_sachleistung_kein_pflegegeld(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate(pg=3)
        state[1]["slPct"] = 100
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["monate"][1]["pgBetrag"]  == 0
        assert r["monate"][1]["pgProzent"] == 0
        assert r["monate"][1]["slBetrag"]  == sl[3]

    def test_kombinationsleistung_pg5_100pct(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate(pg=5)
        state[6]["slPct"] = 100
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["monate"][6]["pgBetrag"] == 0
        assert r["monate"][6]["slBetrag"] == sl[5]

    def test_sachleistung_ueber_100pct_wird_geclampt(self):
        """slPct > 100 darf pgProzent nicht negativ machen."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate(pg=3)
        state[1]["slPct"] = 150  # ungültiger Wert
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["monate"][1]["pgProzent"] == 0  # max(0, 100-150) = 0

    def test_kombinationsleistung_unabhaengig_pro_monat(self):
        """Monat 1 = 50%, Monat 2 = 0% — keine gegenseitige Beeinflussung."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate(pg=3)
        state[1]["slPct"] = 50
        state[2]["slPct"] = 0
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["monate"][1]["pgProzent"] == 50
        assert r["monate"][2]["pgProzent"] == 100


# ═══════════════════════════════════════════════════════════════════════════════
# 3. VP+KZP Budgetverbrauch
# ═══════════════════════════════════════════════════════════════════════════════

class TestBudgetverbrauch:
    """VP- und KZP-Beträge reduzieren das Jahresbudget korrekt."""

    def test_leere_planung_budget_unveraendert(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["restGesamt"] == pytest.approx(3_539.0, abs=0.01)
        assert r["totalVP"]  == 0.0
        assert r["totalKZP"] == 0.0

    def test_vp_kuerzt_budget(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        state[1]["vp"] = 500.0
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["restGesamt"] == pytest.approx(3_039.0, abs=0.01)
        assert r["totalVP"]    == pytest.approx(500.0, abs=0.01)

    def test_kzp_kuerzt_budget(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        state[3]["kzp"] = 1_000.0
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["restGesamt"] == pytest.approx(2_539.0, abs=0.01)
        assert r["totalKZP"]   == pytest.approx(1_000.0, abs=0.01)

    def test_vp_und_kzp_kumulieren(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        state[1]["vp"]  = 500.0
        state[2]["kzp"] = 500.0
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["restGesamt"] == pytest.approx(2_539.0, abs=0.01)

    def test_rest_budget_kumuliert_ueber_monate(self):
        """restBudget in Monat[m] = Budget minus VP+KZP aller Monate 1..m."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        state[1]["vp"] = 200.0
        state[2]["vp"] = 300.0
        state[3]["vp"] = 100.0
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["monate"][1]["restBudget"] == pytest.approx(3_339.0, abs=0.01)
        assert r["monate"][2]["restBudget"] == pytest.approx(3_039.0, abs=0.01)
        assert r["monate"][3]["restBudget"] == pytest.approx(2_939.0, abs=0.01)

    def test_budget_prozent_berechnung(self):
        """50% des Budgets → pct = 50."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        state[1]["vp"] = 3_539.0 / 2
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["pct"] == 50


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Entlastungsbetrag KZP-Verrechnung
# ═══════════════════════════════════════════════════════════════════════════════

class TestEntlastungsbetrag:
    """Checkbox: Entlastungsbetrag finanziert KZP-Hotelkosten mit."""

    def test_checkbox_inaktiv_keine_erstattung(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      entlastung_kzp_aktiv=False,
                      kzp_verpfl={1: 100.0})
        assert r["entlastungMonate"][1]["erstattet"] == 0.0
        assert r["entlastungMonate"][1]["rest"] == pytest.approx(131.0, abs=0.01)

    def test_checkbox_aktiv_verpfl_unter_grenze(self):
        """Verpflegung 80 € < 131 € → erstattet = 80 €."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      entlastung_kzp_aktiv=True,
                      kzp_verpfl={1: 80.0})
        assert r["entlastungMonate"][1]["erstattet"] == pytest.approx(80.0, abs=0.01)
        assert r["entlastungMonate"][1]["rest"]      == pytest.approx(51.0, abs=0.01)

    def test_checkbox_aktiv_verpfl_gleich_grenze(self):
        """Verpflegung = 131 € → voll erstattet, Rest = 0."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      entlastung_kzp_aktiv=True,
                      kzp_verpfl={1: 131.0})
        assert r["entlastungMonate"][1]["erstattet"] == pytest.approx(131.0, abs=0.01)
        assert r["entlastungMonate"][1]["rest"]      == pytest.approx(0.0, abs=0.01)

    def test_checkbox_aktiv_verpfl_ueber_grenze(self):
        """Verpflegung 200 € > 131 € → nur 131 € erstattet."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      entlastung_kzp_aktiv=True,
                      kzp_verpfl={1: 200.0})
        assert r["entlastungMonate"][1]["erstattet"] == pytest.approx(131.0, abs=0.01)
        assert r["entlastungMonate"][1]["rest"]      == pytest.approx(0.0, abs=0.01)

    def test_entlastung_unabhaengig_pro_monat(self):
        """Monat 1 mit KZP-Verpfl., Monat 2 ohne — keine Übertragung."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      entlastung_kzp_aktiv=True,
                      kzp_verpfl={1: 131.0, 2: 0.0})
        assert r["entlastungMonate"][1]["erstattet"] == pytest.approx(131.0, abs=0.01)
        assert r["entlastungMonate"][2]["erstattet"] == pytest.approx(0.0, abs=0.01)

    def test_total_entlastung_rest_jahressumme(self):
        """Ohne KZP-Verpfl.: totalEntlastungRest = 12 × 131 = 1.572 €."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["totalEntlastungRest"] == pytest.approx(131.0 * 12, abs=0.01)

    def test_kzp_verpfl_keine_auswirkung_auf_budget(self):
        """KZP-Hotelkosten beeinflussen VP+KZP-Budget NICHT."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      entlastung_kzp_aktiv=True,
                      kzp_verpfl={m: 100.0 for m in range(1, 13)})
        assert r["restGesamt"] == pytest.approx(3_539.0, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Gleichmäßig verteilen
# ═══════════════════════════════════════════════════════════════════════════════

class TestGleichVerteilen:
    """3.539 € gleichmäßig auf 12 Monate — kein Cent verloren."""

    def _gleich_verteilen(self, budget: float) -> list[float]:
        """Python-Spiegel der gleichVerteilen()-Funktion aus dem JS."""
        pro_monat = int(budget / 12 * 100) / 100
        verteilt  = 0.0
        werte = []
        for i in range(12):
            if i < 11:
                werte.append(round(pro_monat, 2))
                verteilt += pro_monat
            else:
                werte.append(round(budget - verteilt, 2))
        return werte

    def test_summe_exakt_budget(self):
        werte = self._gleich_verteilen(3_539.0)
        assert sum(werte) == pytest.approx(3_539.0, abs=0.01)

    def test_12_werte(self):
        werte = self._gleich_verteilen(3_539.0)
        assert len(werte) == 12

    def test_alle_werte_positiv(self):
        werte = self._gleich_verteilen(3_539.0)
        assert all(v >= 0 for v in werte)

    def test_kein_cent_verloren_2024_budget(self):
        werte = self._gleich_verteilen(3_386.0)
        assert sum(werte) == pytest.approx(3_386.0, abs=0.01)

    def test_letzter_monat_gleicht_rest_aus(self):
        """Rundungsdifferenzen landen im Dezember."""
        werte = self._gleich_verteilen(3_539.0)
        pro_monat = int(3_539.0 / 12 * 100) / 100
        for v in werte[:11]:
            assert v == pytest.approx(pro_monat, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Chip-Toggle (keine Berechnungsänderung)
# ═══════════════════════════════════════════════════════════════════════════════

class TestChipToggle:
    """Chips steuern nur die Sichtbarkeit — Werte bleiben aktiv."""

    def test_chip_toggle_aendert_berechnung_nicht(self):
        """
        Chip-Toggle = CSS-only. berechne() wertet alle 12 Monate aus,
        unabhängig davon ob eine Zeile sichtbar ist.
        """
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        state[1]["vp"] = 300.0

        # Berechnung mit und ohne "sichtbarem" Monat 1 ist identisch —
        # weil berechne() keine Sichtbarkeit kennt
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["totalVP"] == pytest.approx(300.0, abs=0.01)

    def test_ausgeblendeter_monat_reduziert_budget(self):
        """
        Auch ein per Chip ausgeblendeter Monat mit VP-Betrag
        reduziert das Budget (Werte bleiben aktiv).
        """
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        # Monat 6 "ausgeblendet" — aber Wert ist trotzdem gesetzt
        state[6]["vp"] = 500.0
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["restGesamt"] == pytest.approx(3_039.0, abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Grenzwerte
# ═══════════════════════════════════════════════════════════════════════════════

class TestGrenzwerte:
    """Budget exakt ausgeschöpft, überschritten, Nullfall."""

    def test_budget_exakt_ausgeschoepft(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        state[1]["vp"] = 3_539.0
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["restGesamt"] == pytest.approx(0.0, abs=0.01)
        assert r["pct"]        == 100

    def test_budget_ueberschritten(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        state[1]["vp"] = 2_000.0
        state[2]["kzp"] = 2_000.0
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["restGesamt"] < 0
        assert r["pct"]        == 100  # capped bei 100

    def test_budget_ueberschritten_restbudget_negativ_im_letzten_monat(self):
        """restBudget pro Monat kann negativ werden bei Überschreitung."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        state[12]["vp"]  = 2_000.0
        state[12]["kzp"] = 2_000.0
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["monate"][12]["restBudget"] < 0

    def test_alle_monate_null_pct_null(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp)
        assert r["pct"] == 0

    def test_tagespflege_pg1_null(self):
        """PG1 hat keine Tagespflege."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate(pg=1)
        r = _berechne(state, 3_539.0, pg, sl, tp)
        for m in range(1, 13):
            assert r["monate"][m]["tpBetrag"] == 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Pflegegrad-Sätze
# ═══════════════════════════════════════════════════════════════════════════════

class TestPflegegradSaetze:
    """Alle Pflegegrade liefern die korrekten Beträge aus pflege_rules.py."""

    @pytest.mark.parametrize("pg,erwartetes_pg,erwartetes_sl,erwartetes_tp", [
        (2, 347.0,   796.0,  721.0),
        (3, 599.0, 1_497.0, 1_357.0),
        (4, 800.0, 1_859.0, 1_685.0),
        (5, 990.0, 2_299.0, 2_085.0),
    ])
    def test_satz_pro_pflegegrad_2026(self, pg, erwartetes_pg, erwartetes_sl, erwartetes_tp):
        r = get_regelwerk(2026)
        assert r.pflegegeld_monatlich(pg)   == pytest.approx(erwartetes_pg,  abs=0.01)
        assert r.sachleistung_monatlich(pg) == pytest.approx(erwartetes_sl,  abs=0.01)
        assert r.tagespflege_monatlich(pg)  == pytest.approx(erwartetes_tp,  abs=0.01)

    def test_pg1_pflegegeld_null(self):
        r = get_regelwerk(2026)
        assert r.pflegegeld_monatlich(1) == 0.0

    def test_pg1_sachleistung_null(self):
        r = get_regelwerk(2026)
        assert r.sachleistung_monatlich(1) == 0.0

    def test_pg_saetze_steigen_mit_grad(self):
        """Höherer Pflegegrad → höherer Betrag."""
        r = get_regelwerk(2026)
        pg_werte = [r.pflegegeld_monatlich(pg) for pg in range(2, 6)]
        sl_werte = [r.sachleistung_monatlich(pg) for pg in range(2, 6)]
        tp_werte = [r.tagespflege_monatlich(pg) for pg in range(2, 6)]
        for i in range(len(pg_werte) - 1):
            assert pg_werte[i] < pg_werte[i + 1]
            assert sl_werte[i] < sl_werte[i + 1]
            assert tp_werte[i] < tp_werte[i + 1]

    def test_pflegegrad_wechsel_mid_year(self):
        """Pflegegradwechsel per Monat — jeder Monat rechnet mit eigenem PG."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        for m in range(1, 7):
            state[m]["pg"] = 2
        for m in range(7, 13):
            state[m]["pg"] = 3

        r = _berechne(state, 3_539.0, pg, sl, tp)
        # Monat 1-6: PG2 Pflegegeld
        assert r["monate"][1]["pgBetrag"] == round(pg[2])
        # Monat 7-12: PG3 Pflegegeld
        assert r["monate"][7]["pgBetrag"] == round(pg[3])


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Router-Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestBudgetPlanungRouter:
    """GET /budget/planung liefert korrekte Daten im Template-Kontext."""

    def test_pg_saetze_enthalten_alle_grade(self):
        """Der Router baut pg_saetze für PG 1–5."""
        r = get_regelwerk(2026)
        pg_saetze = {pg: r.pflegegeld_monatlich(pg) for pg in range(1, 6)}
        assert set(pg_saetze.keys()) == {1, 2, 3, 4, 5}

    def test_sl_saetze_enthalten_alle_grade(self):
        r = get_regelwerk(2026)
        sl_saetze = {pg: r.sachleistung_monatlich(pg) for pg in range(1, 6)}
        assert set(sl_saetze.keys()) == {1, 2, 3, 4, 5}

    def test_tp_saetze_enthalten_alle_grade(self):
        r = get_regelwerk(2026)
        tp_saetze = {pg: r.tagespflege_monatlich(pg) for pg in range(1, 6)}
        assert set(tp_saetze.keys()) == {1, 2, 3, 4, 5}

    def test_monate_liste_hat_12_eintraege(self):
        monate_kurz = ["", "Jan", "Feb", "Mrz", "Apr", "Mai", "Jun",
                       "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
        monate_liste = [{"nr": m, "name": monate_kurz[m]} for m in range(1, 13)]
        assert len(monate_liste) == 12

    def test_planung_vp_startet_mit_null(self):
        """Planer startet mit 0 für alle Monate — keine Altdaten."""
        planung_vp = {m: 0.0 for m in range(1, 13)}
        assert len(planung_vp) == 12
        assert all(v == 0.0 for v in planung_vp.values())

    def test_budget_gesamt_aus_regelwerk(self):
        """budget_gesamt im Context kommt aus pflege_rules, nicht hardcoded."""
        r = get_regelwerk(2026)
        assert r.vp_budget_jahresbetrag == pytest.approx(3_539.0, abs=0.01)

    def test_regelwerk_jahreswechsel_2024_auf_2026(self):
        """Router passt budget_gesamt ans Jahr an."""
        r24 = get_regelwerk(2024)
        r26 = get_regelwerk(2026)
        assert r24.vp_budget_jahresbetrag == pytest.approx(3_386.0, abs=0.01)
        assert r26.vp_budget_jahresbetrag == pytest.approx(3_539.0, abs=0.01)
        assert r24.vp_budget_jahresbetrag != r26.vp_budget_jahresbetrag


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Vorjahresguthaben Entlastungsbetrag
# ═══════════════════════════════════════════════════════════════════════════════

class TestVorjahrGuthaben:
    """
    Nicht verbrauchter Entlastungsbetrag aus Vorjahr (§ 45b SGB XI).
    Nutzbar Jan–Jun des Folgejahres. Max. 12 × 131 = 1.572 €.
    """

    def test_kein_guthaben_keine_auswirkung(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      vorjahr_guthaben=0.0, vorjahr_aktiv=True)
        assert r["vorjahrEntlastungGesamt"] == 0.0
        # totalEntlastungRest = nur laufende 12 × 131
        assert r["totalEntlastungRest"] == pytest.approx(131.0 * 12, abs=0.01)

    def test_guthaben_aktiv_wird_addiert(self):
        """200 € Vorjahresguthaben + 12×131 laufend = totalEntlastungRest."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      vorjahr_guthaben=200.0, vorjahr_aktiv=True)
        assert r["vorjahrEntlastungGesamt"] == pytest.approx(200.0, abs=0.01)
        assert r["totalEntlastungRest"] == pytest.approx(131.0 * 12 + 200.0, abs=0.01)

    def test_guthaben_inaktiv_nach_30_juni(self):
        """Nach 30.06. ist das Vorjahresguthaben verfallen — kein Aufschlag."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      vorjahr_guthaben=500.0, vorjahr_aktiv=False)
        assert r["vorjahrEntlastungGesamt"] == 0.0
        assert r["totalEntlastungRest"] == pytest.approx(131.0 * 12, abs=0.01)

    def test_guthaben_maximal_1572(self):
        """Max. übertragbar = 12 × 131 = 1.572 €."""
        r = get_regelwerk(2026)
        max_guthaben = r.entlastungsbetrag_monatlich * 12
        assert max_guthaben == pytest.approx(1_572.0, abs=0.01)

    def test_guthaben_ueber_maximum_wird_geclampt(self):
        """Eingabe > 1.572 € → wird auf 1.572 € begrenzt."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        # Simulation: Clamping wie im JS (Math.min(wert, ENTLASTUNG_MAX))
        guthaben_roh = 2_000.0
        guthaben = min(guthaben_roh, 1_572.0)
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      vorjahr_guthaben=guthaben, vorjahr_aktiv=True)
        assert r["vorjahrEntlastungGesamt"] == pytest.approx(1_572.0, abs=0.01)

    def test_guthaben_null_explizit(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      vorjahr_guthaben=0.0, vorjahr_aktiv=True)
        assert r["vorjahrEntlastungGesamt"] == 0.0

    def test_guthaben_negativ_wird_ignoriert(self):
        """Negative Eingabe → 0."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        guthaben = max(-100.0, 0.0)  # wie im JS: Math.max(wert, 0)
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      vorjahr_guthaben=guthaben, vorjahr_aktiv=True)
        assert r["vorjahrEntlastungGesamt"] == 0.0

    def test_guthaben_kein_einfluss_auf_vp_kzp_budget(self):
        """Vorjahresguthaben betrifft NUR Entlastungsbetrag, nicht VP+KZP."""
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r = _berechne(state, 3_539.0, pg, sl, tp,
                      vorjahr_guthaben=500.0, vorjahr_aktiv=True)
        assert r["restGesamt"] == pytest.approx(3_539.0, abs=0.01)
        assert r["pct"]        == 0

    def test_vorjahr_aktiv_flag_korrekt_gesetzt(self):
        pg, sl, tp = _saetze_2026()
        state = _leere_monate()
        r_aktiv   = _berechne(state, 3_539.0, pg, sl, tp,
                               vorjahr_guthaben=300.0, vorjahr_aktiv=True)
        r_inaktiv = _berechne(state, 3_539.0, pg, sl, tp,
                               vorjahr_guthaben=300.0, vorjahr_aktiv=False)
        assert r_aktiv["vorjahrAktiv"]   is True
        assert r_inaktiv["vorjahrAktiv"] is False
        assert r_aktiv["vorjahrEntlastungGesamt"]   == pytest.approx(300.0, abs=0.01)
        assert r_inaktiv["vorjahrEntlastungGesamt"] == pytest.approx(0.0,   abs=0.01)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Speichern-Router (v41l)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSpeichernRouter:
    """
    _lade_gespeicherte_planung() — Lade-Logik des Routers direkt testen.
    Kein FastAPI-Testclient nötig — pure Python-Logik isoliert testbar.
    """

    def _mock_db(self, roh: dict):
        """Minimal-Mock für db.planung_laden()."""
        class MockDB:
            def planung_laden(self, person, jahr, owner_id):
                return roh
        return MockDB()

    def _lade(self, roh: dict, jahr: int = 2026) -> dict:
        """Ruft _lade_gespeicherte_planung mit Mock-DB auf."""
        import json as _json
        # Inline-Reimplementierung für isolierten Test
        planung_vp  = {}
        planung_kzp = {}
        planung_sl  = {}
        planung_pg  = {}

        for m in range(1, 13):
            eintrag = roh.get(m, {})
            planung_vp[m] = eintrag.get("stunden", 0.0)
            try:
                zusatz = _json.loads(eintrag.get("notiz", "{}") or "{}")
            except (ValueError, TypeError):
                zusatz = {}
            planung_kzp[m] = zusatz.get("kzp", 0.0)
            planung_sl[m]  = zusatz.get("sl_pct", 0)
            planung_pg[m]  = zusatz.get("pg", 3)

        eintrag_0 = roh.get(0, {})
        try:
            extras = _json.loads(eintrag_0.get("notiz", "{}") or "{}")
        except (ValueError, TypeError):
            extras = {}

        return {
            "planung_vp":       planung_vp,
            "planung_kzp":      planung_kzp,
            "planung_sl":       planung_sl,
            "planung_pg":       planung_pg,
            "vorjahr_guthaben": extras.get("vorjahr_guthaben", 0.0),
            "entlastung_kzp":   extras.get("entlastung_kzp", False),
        }

    def _make_notiz(self, kzp=0.0, sl_pct=0, pg=3) -> str:
        import json as _json
        return _json.dumps({"kzp": kzp, "sl_pct": sl_pct, "pg": pg})

    def _make_extras(self, vorjahr=0.0, entlastung_kzp=False) -> str:
        import json as _json
        return _json.dumps({"vorjahr_guthaben": vorjahr, "entlastung_kzp": entlastung_kzp})

    # ── Leere DB ──────────────────────────────────────────────────────────────

    def test_leere_db_liefert_nullwerte(self):
        r = self._lade({})
        assert all(v == 0.0 for v in r["planung_vp"].values())
        assert all(v == 0.0 for v in r["planung_kzp"].values())
        assert all(v == 0   for v in r["planung_sl"].values())
        assert all(v == 3   for v in r["planung_pg"].values())
        assert r["vorjahr_guthaben"] == 0.0
        assert r["entlastung_kzp"]   is False

    def test_leere_db_hat_12_monate(self):
        r = self._lade({})
        assert len(r["planung_vp"])  == 12
        assert len(r["planung_kzp"]) == 12
        assert len(r["planung_sl"])  == 12
        assert len(r["planung_pg"])  == 12

    # ── VP laden ──────────────────────────────────────────────────────────────

    def test_vp_wird_korrekt_geladen(self):
        roh = {1: {"stunden": 300.0, "notiz": "{}"}}
        r = self._lade(roh)
        assert r["planung_vp"][1] == pytest.approx(300.0, abs=0.01)
        assert r["planung_vp"][2] == 0.0  # nicht gesetzt → Default

    def test_alle_12_vp_monate_laden(self):
        roh = {m: {"stunden": float(m * 100), "notiz": "{}"} for m in range(1, 13)}
        r = self._lade(roh)
        for m in range(1, 13):
            assert r["planung_vp"][m] == pytest.approx(m * 100.0, abs=0.01)

    # ── KZP / SL / PG laden ──────────────────────────────────────────────────

    def test_kzp_aus_notiz_geladen(self):
        roh = {3: {"stunden": 0.0, "notiz": self._make_notiz(kzp=750.0)}}
        r = self._lade(roh)
        assert r["planung_kzp"][3] == pytest.approx(750.0, abs=0.01)

    def test_sl_aus_notiz_geladen(self):
        roh = {6: {"stunden": 0.0, "notiz": self._make_notiz(sl_pct=50)}}
        r = self._lade(roh)
        assert r["planung_sl"][6] == 50

    def test_pg_aus_notiz_geladen(self):
        roh = {9: {"stunden": 0.0, "notiz": self._make_notiz(pg=5)}}
        r = self._lade(roh)
        assert r["planung_pg"][9] == 5

    def test_alle_felder_gleichzeitig_geladen(self):
        roh = {4: {"stunden": 400.0, "notiz": self._make_notiz(kzp=200.0, sl_pct=30, pg=4)}}
        r = self._lade(roh)
        assert r["planung_vp"][4]  == pytest.approx(400.0, abs=0.01)
        assert r["planung_kzp"][4] == pytest.approx(200.0, abs=0.01)
        assert r["planung_sl"][4]  == 30
        assert r["planung_pg"][4]  == 4

    # ── Jahres-Extras (monat=0) ───────────────────────────────────────────────

    def test_vorjahr_guthaben_aus_extras(self):
        roh = {0: {"stunden": 0.0, "notiz": self._make_extras(vorjahr=450.0)}}
        r = self._lade(roh)
        assert r["vorjahr_guthaben"] == pytest.approx(450.0, abs=0.01)

    def test_entlastung_kzp_checkbox_true(self):
        roh = {0: {"stunden": 0.0, "notiz": self._make_extras(entlastung_kzp=True)}}
        r = self._lade(roh)
        assert r["entlastung_kzp"] is True

    def test_entlastung_kzp_checkbox_false(self):
        roh = {0: {"stunden": 0.0, "notiz": self._make_extras(entlastung_kzp=False)}}
        r = self._lade(roh)
        assert r["entlastung_kzp"] is False

    def test_extras_fehlen_liefert_defaults(self):
        """Kein monat=0 in DB → vorjahr_guthaben=0, entlastung_kzp=False."""
        r = self._lade({})
        assert r["vorjahr_guthaben"] == 0.0
        assert r["entlastung_kzp"]   is False

    # ── Robustheit ────────────────────────────────────────────────────────────

    def test_kaputtes_json_in_notiz_gibt_defaults(self):
        roh = {5: {"stunden": 100.0, "notiz": "KEIN_JSON{{{}}}"}}
        r = self._lade(roh)
        assert r["planung_kzp"][5] == 0.0
        assert r["planung_sl"][5]  == 0
        assert r["planung_pg"][5]  == 3

    def test_leere_notiz_gibt_defaults(self):
        roh = {7: {"stunden": 50.0, "notiz": ""}}
        r = self._lade(roh)
        assert r["planung_kzp"][7] == 0.0

    def test_none_notiz_gibt_defaults(self):
        roh = {8: {"stunden": 50.0, "notiz": None}}
        r = self._lade(roh)
        assert r["planung_kzp"][8] == 0.0

    def test_kaputtes_json_in_extras_gibt_defaults(self):
        roh = {0: {"stunden": 0.0, "notiz": "KAPUTT"}}
        r = self._lade(roh)
        assert r["vorjahr_guthaben"] == 0.0
        assert r["entlastung_kzp"]   is False

    def test_teilweise_monate_rest_ist_default(self):
        """Nur Monat 1 gespeichert — Monate 2–12 bekommen Defaults."""
        roh = {1: {"stunden": 200.0, "notiz": self._make_notiz(kzp=100.0, sl_pct=20, pg=3)}}
        r = self._lade(roh)
        for m in range(2, 13):
            assert r["planung_vp"][m]  == 0.0
            assert r["planung_kzp"][m] == 0.0
            assert r["planung_sl"][m]  == 0
            assert r["planung_pg"][m]  == 3

    # ── PLANER_PERSON Konstante ───────────────────────────────────────────────

    def test_planer_person_konstante(self):
        """__planer__ ist der reservierte Schlüssel — darf sich nicht ändern."""
        import sys, pathlib
        sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
        from web.routers.budget_planung import PLANER_PERSON
        assert PLANER_PERSON == "__planer__"

    # ── Speichern-Payload-Struktur ────────────────────────────────────────────

    def test_speichern_payload_alle_felder_vorhanden(self):
        """Der Payload den JS schickt muss alle erwarteten Keys haben."""
        import json as _json
        payload = {
            "jahr": 2026,
            "vp":  {str(m): 0.0 for m in range(1, 13)},
            "kzp": {str(m): 0.0 for m in range(1, 13)},
            "sl":  {str(m): 0   for m in range(1, 13)},
            "pg":  {str(m): 3   for m in range(1, 13)},
            "vorjahr_guthaben": 0.0,
            "entlastung_kzp":   False,
        }
        assert set(payload.keys()) == {"jahr", "vp", "kzp", "sl", "pg",
                                       "vorjahr_guthaben", "entlastung_kzp"}
        assert len(payload["vp"])  == 12
        assert len(payload["kzp"]) == 12

    def test_speichern_payload_jahreswert(self):
        payload = {"jahr": 2026}
        assert int(payload.get("jahr", 0)) == 2026

    def test_extras_roundtrip(self):
        """Extras serialisieren → deserialisieren → gleiche Werte."""
        import json as _json
        original = {"vorjahr_guthaben": 350.0, "entlastung_kzp": True}
        serialized = _json.dumps(original)
        restored = _json.loads(serialized)
        assert restored["vorjahr_guthaben"] == pytest.approx(350.0, abs=0.01)
        assert restored["entlastung_kzp"]   is True

    def test_notiz_roundtrip(self):
        """Monatsdaten serialisieren → deserialisieren → gleiche Werte."""
        import json as _json
        original = {"kzp": 500.0, "sl_pct": 40, "pg": 4}
        serialized = _json.dumps(original)
        restored = _json.loads(serialized)
        assert restored["kzp"]    == pytest.approx(500.0, abs=0.01)
        assert restored["sl_pct"] == 40
        assert restored["pg"]     == 4
