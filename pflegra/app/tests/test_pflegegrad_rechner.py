"""
tests/test_pflegegrad_rechner.py — Tests für NBA-Pflegegradrechner

Prüft:
  1. Grenzwerte der Pflegegrad-Einstufung
  2. Modul 2+3 Kombinationslogik (max, nicht Summe/Durchschnitt)
  3. Alle Kriterien haben Hilfetext
  4. Gesamtpunkte-Berechnung
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pflegegrad_rechner import (
    berechne_pflegegrad, ALLE_MODULE, _lookup_gewichtet,
    _PFLEGEGRAD_GRENZEN,
)


# ── Hilfsfunktion ─────────────────────────────────────────────────────────────

def make_antworten(m1_roh=0, m2_roh=0, m3_roh=0, m4_roh=0, m5_roh=0, m6_roh=0):
    """Erzeugt minimale Antworten mit gewünschten Rohpunkten pro Modul."""
    result = {}
    def fill(modul, target_roh):
        roh = 0
        for k in modul.kriterien:
            if roh >= target_roh:
                result[k.id] = 0
            else:
                add = min(3, target_roh - roh)
                result[k.id] = add
                roh += add
    fill(ALLE_MODULE[0], m1_roh)
    fill(ALLE_MODULE[1], m2_roh)
    fill(ALLE_MODULE[2], m3_roh)
    fill(ALLE_MODULE[3], m4_roh)
    fill(ALLE_MODULE[4], m5_roh)
    fill(ALLE_MODULE[5], m6_roh)
    return result


# ── 1. Struktur-Tests ─────────────────────────────────────────────────────────

def test_alle_module_vorhanden():
    assert len(ALLE_MODULE) == 6

def test_kriterien_gesamt():
    assert sum(len(m.kriterien) for m in ALLE_MODULE) == 57

def test_alle_kriterien_haben_hilfetext():
    ohne = [(m.id, k.id) for m in ALLE_MODULE for k in m.kriterien if not k.hilfe]
    assert ohne == [], f"Kriterien ohne Hilfetext: {ohne}"

def test_alle_kriterien_haben_optionen():
    for m in ALLE_MODULE:
        for k in m.kriterien:
            assert len(k.optionen) >= 4, f"{k.id} hat zu wenige Optionen"

def test_pflegegrad_grenzen_vollstaendig():
    # Muss alle 6 Stufen (0-5) abdecken
    pgs = [pg for _, _, pg, _ in _PFLEGEGRAD_GRENZEN]
    assert pgs == [0, 1, 2, 3, 4, 5]


# ── 2. Grenzwert-Tests ────────────────────────────────────────────────────────

def test_kein_pflegegrad_alle_null():
    r = berechne_pflegegrad({})
    assert r.pflegegrad == 0
    assert r.gesamtpunkte == 0.0

def test_pg1_grenze_exakt_12_5():
    # M1 roh=1→2.5 + M4 roh=3→10.0 = 12.5 → PG1
    r = berechne_pflegegrad(make_antworten(m1_roh=1, m4_roh=3))
    assert r.gesamtpunkte == 12.5
    assert r.pflegegrad == 1

def test_pg0_knapp_unter_grenze():
    # M1 roh=5→10.0 → PG0 (unter 12.5)
    r = berechne_pflegegrad(make_antworten(m1_roh=5))
    assert r.gesamtpunkte == 10.0
    assert r.pflegegrad == 0

def test_pg2_grenze_27_5():
    # M4=3→10 + M5=4→10 + M6=4→7.5 = 27.5 → PG2
    r = berechne_pflegegrad(make_antworten(m4_roh=3, m5_roh=4, m6_roh=4))
    assert r.gesamtpunkte == 27.5
    assert r.pflegegrad == 2

def test_pg1_knapp_unter_pg2():
    # M1=2.5 + M4=10 + M5=5 + M6=3.75 = 21.25 → PG1
    r = berechne_pflegegrad(make_antworten(m1_roh=1, m4_roh=3, m5_roh=3, m6_roh=3))
    assert r.pflegegrad == 1

def test_pg3_grenze_exakt_47_5():
    # M1=10 + M4=20 + M5=10 + M6=7.5 = 47.5 → PG3
    r = berechne_pflegegrad(make_antworten(m1_roh=5, m4_roh=8, m5_roh=4, m6_roh=4))
    assert r.gesamtpunkte == 47.5
    assert r.pflegegrad == 3

def test_pg2_knapp_unter_pg3():
    # M1=5 + M4=20 + M5=10 + M6=7.5 = 42.5 → PG2
    r = berechne_pflegegrad(make_antworten(m1_roh=3, m4_roh=8, m5_roh=4, m6_roh=4))
    assert r.gesamtpunkte == 42.5
    assert r.pflegegrad == 2

def test_pg4_erreichbar():
    # M1=10 + M4=40 + M5=10 + M6=15 = 75.0 → PG4
    r = berechne_pflegegrad(make_antworten(m1_roh=5, m4_roh=18, m5_roh=4, m6_roh=10))
    assert r.gesamtpunkte == 75.0
    assert r.pflegegrad == 4

def test_pg5_maximum():
    # Alle Module maximal → 100 Punkte → PG5
    r = berechne_pflegegrad(make_antworten(m1_roh=5, m2_roh=11, m4_roh=18, m5_roh=9, m6_roh=10))
    assert r.gesamtpunkte == 100.0
    assert r.pflegegrad == 5

def test_70_nicht_exakt_erreichbar():
    """70.0 Punkte sind mit NBA-Stufentabelle nicht exakt erreichbar.
    Nächste Werte: 67.5 (PG3) und 71.25 (PG4)."""
    r_unter = berechne_pflegegrad(make_antworten(m1_roh=5, m4_roh=18, m5_roh=4, m6_roh=4))
    assert r_unter.gesamtpunkte == 67.5
    assert r_unter.pflegegrad == 3

    r_ueber = berechne_pflegegrad(make_antworten(m1_roh=5, m2_roh=1, m4_roh=18, m5_roh=4, m6_roh=4))
    assert r_ueber.pflegegrad == 4


# ── 3. Modul 2+3 Kombinationslogik ───────────────────────────────────────────

def test_m2_m3_max_nicht_summe():
    """max(M2, M3) muss zählen, nicht M2+M3."""
    # M2 voll (roh=11→15.0 gew), M3 leer (roh=0→0 gew)
    a = make_antworten(m2_roh=11)
    r = berechne_pflegegrad(a)
    # Gesamtpunkte dürfen nicht M2+M3 enthalten
    assert r.gesamtpunkte == 15.0  # nur M2, kein Doppelzählen

def test_m3_dominiert_wenn_hoeher():
    # M3 voll (roh=39→15.0 gew), M2 leer
    a = make_antworten(m3_roh=39)
    r = berechne_pflegegrad(a)
    assert r.gesamtpunkte == 15.0

def test_m2_m3_kombiniert_nimmt_hoeheren():
    # M2 roh=5→7.5 gew, M3 roh=21→15.0 gew → max=15.0
    a = make_antworten(m2_roh=5, m3_roh=21)
    r = berechne_pflegegrad(a)
    m2_e = next(m for m in r.modul_ergebnisse if m.modul_id == 2)
    m3_e = next(m for m in r.modul_ergebnisse if m.modul_id == 3)
    assert m2_e.gewichtete_punkte == 15.0  # beide zeigen den max-Wert
    assert m3_e.gewichtete_punkte == 15.0
    assert r.gesamtpunkte == 15.0

def test_m2_m3_nicht_durchschnitt():
    # M2=15.0 gew, M3=3.75 gew → max=15.0, Durchschnitt wäre 9.375
    a = make_antworten(m2_roh=11, m3_roh=3)
    r = berechne_pflegegrad(a)
    assert r.gesamtpunkte == 15.0  # nicht 9.375


# ── 4. Gewichtungstabellen ────────────────────────────────────────────────────

@pytest.mark.parametrize("modul_id,roh,erwartet", [
    (1, 0, 0.0), (1, 1, 2.5), (1, 2, 2.5), (1, 3, 5.0), (1, 4, 5.0), (1, 5, 10.0),
    (4, 0, 0.0), (4, 2, 0.0), (4, 3, 10.0), (4, 7, 10.0), (4, 8, 20.0), (4, 17, 20.0), (4, 18, 40.0),
    (5, 0, 0.0), (5, 1, 5.0), (5, 3, 5.0), (5, 4, 10.0), (5, 8, 10.0), (5, 9, 20.0),
    (6, 0, 0.0), (6, 1, 3.75), (6, 3, 3.75), (6, 4, 7.5), (6, 9, 7.5), (6, 10, 15.0),
])
def test_gewichtungstabelle(modul_id, roh, erwartet):
    assert _lookup_gewichtet(modul_id, roh) == erwartet


# ── 5. Ergebnis-Vollständigkeit ───────────────────────────────────────────────

def test_ergebnis_hat_alle_felder():
    r = berechne_pflegegrad(make_antworten(m4_roh=8))
    assert r.gesamtpunkte >= 0
    assert r.pflegegrad in range(6)
    assert r.pflegegrad_bezeichnung
    assert len(r.modul_ergebnisse) == 6
    assert r.begruendung
    assert len(r.hinweise) >= 1

def test_hinweis_orientierung_immer_vorhanden():
    r = berechne_pflegegrad({})
    assert any("Orientierungshilfe" in h for h in r.hinweise)


# ── 6. Leistungen je Pflegegrad ───────────────────────────────────────────────

def test_leistungen_import():
    from pflege_rules import leistungen_fuer_pflegegrad
    assert callable(leistungen_fuer_pflegegrad)

def test_pg0_keine_leistungen():
    from pflege_rules import leistungen_fuer_pflegegrad
    leistungen = leistungen_fuer_pflegegrad(0, 2026)
    verfuegbar = [l for l in leistungen if l["verfuegbar"]]
    assert verfuegbar == []

def test_pg1_nur_basisleistungen():
    from pflege_rules import leistungen_fuer_pflegegrad
    leistungen = leistungen_fuer_pflegegrad(1, 2026)
    verfuegbar = {l["titel"] for l in leistungen if l["verfuegbar"]}
    # PG1 hat Entlastungsbetrag, Hilfsmittel, Wohnumfeld, DiPA
    assert "Entlastungsbetrag" in verfuegbar
    assert "Pflegehilfsmittel" in verfuegbar
    # Aber kein Pflegegeld
    assert "Pflegegeld" not in verfuegbar

def test_pg2_hat_pflegegeld():
    from pflege_rules import leistungen_fuer_pflegegrad
    leistungen = leistungen_fuer_pflegegrad(2, 2026)
    pg_leistung = next(l for l in leistungen if l["titel"] == "Pflegegeld")
    assert pg_leistung["verfuegbar"]
    assert pg_leistung["betrag"] == 347.0  # 2026

def test_pg3_pflegegeld_hoeher():
    from pflege_rules import leistungen_fuer_pflegegrad
    l2 = next(l for l in leistungen_fuer_pflegegrad(2, 2026) if l["titel"] == "Pflegegeld")
    l3 = next(l for l in leistungen_fuer_pflegegrad(3, 2026) if l["titel"] == "Pflegegeld")
    assert l3["betrag"] > l2["betrag"]

def test_leistungen_haben_pflichtfelder():
    from pflege_rules import leistungen_fuer_pflegegrad
    for pg in range(6):
        for l in leistungen_fuer_pflegegrad(pg, 2026):
            assert "titel" in l
            assert "betrag" in l
            assert "einheit" in l
            assert "paragraf" in l
            assert "info" in l
            assert "verfuegbar" in l
            assert "kategorie" in l
