"""Validierung der Terminformularfelder."""
from web.routers.termine import _validiere


def test_ganztag_leert_uhrzeiten():
    fehler, werte = _validiere("", "Geburtstag", "2026-06-20", 1,
                                "10:00", "11:00", "jaehrlich", [])
    assert fehler == ""
    assert werte["ganztag"] == 1
    assert werte["uhrzeit_von"] == ""
    assert werte["uhrzeit_bis"] == ""


def test_zeitfenster_wird_akzeptiert():
    fehler, werte = _validiere("Max", "Therapie", "2026-06-22", 0,
                                "15:00", "16:00", "woechentlich", ["Max"])
    assert fehler == ""
    assert werte["uhrzeit_von"] == "15:00"
    assert werte["uhrzeit_bis"] == "16:00"


def test_endzeit_vor_startzeit_wird_abgewiesen():
    fehler, _ = _validiere("", "Arzt", "2026-06-22", 0,
                            "16:00", "15:00", "einmalig", [])
    assert "Endzeit" in fehler


def test_unbekannte_wiederholung_wird_abgewiesen():
    fehler, _ = _validiere("", "Arzt", "2026-06-22", 1,
                            "", "", "komplex", [])
    assert "Wiederholung" in fehler
