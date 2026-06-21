"""Validierung der Terminformularfelder."""
import gc
import tempfile
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from db.schema import DbSchema
from services.termine_service import naechster_termin
from starlette.applications import Starlette
from starlette.requests import Request
from web.routers.deps import TEMPLATES
from web.routers.termine import _lade_termine, _validiere


def _dashboard_rendern(termin=None):
    app = Starlette()
    app.state.ingress_entry = ""
    request = Request({
        "type": "http", "method": "GET", "scheme": "http", "path": "/",
        "root_path": "", "query_string": b"", "headers": [],
        "server": ("testserver", 80), "client": ("testclient", 50000), "app": app,
    })
    karte = {
        "name": "Max", "initialen": "M", "vers": None, "budget": None,
        "ampel": "gruen", "eintraege_anzahl": 0, "letzter_eintrag": None,
        "naechster_termin": termin,
    }
    return TEMPLATES.env.get_template("index.html").render(
        request=request, _=lambda key, **kwargs: key, current_user=None,
        is_admin=False, impersonation_aktiv=False, karten=[karte],
        offene_aufgaben=[], naechster_termin_dashboard=termin,
        aktuelles_jahr=2026, letzte_dokumente=[], letzte_beratungen=[],
        letzte_gutachten=[], fristen=[], csrf_token="test",
    )


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


def test_lade_termine_beachtet_owner_id():
    with tempfile.TemporaryDirectory() as tmp:
        schema = DbSchema(Path(tmp) / "pflegra.db")
        schema.migrate()
        conn = schema.connect()
        try:
            conn.execute("""INSERT INTO eigene_termine
                (owner_id, person, titel, datum) VALUES (1, 'Max', 'Owner 1', '2026-06-22')""")
            conn.execute("""INSERT INTO eigene_termine
                (owner_id, person, titel, datum) VALUES (2, 'Max', 'Owner 2', '2026-06-21')""")
            conn.commit()
        finally:
            conn.close()
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            db=SimpleNamespace(_schema=schema)
        )))
        termine = _lade_termine(request, owner_id=1)
        assert [termin.titel for termin in termine] == ["Owner 1"]
        del request, termine, schema
        gc.collect()


def test_dashboard_laedt_ohne_termine():
    html = _dashboard_rendern()
    assert "/kalender/?person=Max" in html
    assert "/termine/?person=Max" in html


def test_dashboard_laedt_mit_naechstem_termin():
    termin = SimpleNamespace(
        datum_date=date(2026, 6, 22), wiederholung="einmalig", titel="Autismus-Therapie",
        person="Max", ganztag=0, uhrzeit_von="15:00", uhrzeit_bis="16:00", id=7,
    )
    vorkommen = naechster_termin([termin], ab=date(2026, 6, 20))
    html = _dashboard_rendern(vorkommen)
    assert "Autismus-Therapie" in html
    assert "22.06.2026" in html
    assert "15:00–16:00" in html
