import asyncio
from datetime import date

from models import Ersatzpflegekraft, PflegeEintrag, PflegraDB
from web import validation
from web.routers import eintraege


def test_eintraege_router_verwendet_zentrale_validierung():
    assert eintraege.validiere_eintrag is validation.validiere_eintrag
    assert eintraege.Validierungsfehler is validation.Validierungsfehler


def test_neuer_eintrag_laed_ersatzpflege_fuer_person_und_owner(monkeypatch):
    aufrufe = []
    maria = Ersatzpflegekraft(person="Max Muster", name="Maria Muster", owner_id=7)

    class FakeDb:
        def personen(self, owner_id):
            assert owner_id == 7
            return ["Erika Beispiel", "Max Muster"]

        def ersatz_alle(self, person, owner_id):
            aufrufe.append(("alle", person, owner_id))
            return [maria]

        def ersatz_letzten(self, person, owner_id):
            aufrufe.append(("letzten", person, owner_id))
            return maria

    class FakeTemplates:
        @staticmethod
        def TemplateResponse(request, template, context, **kwargs):
            return context

    db = FakeDb()
    monkeypatch.setattr(eintraege, "get_db", lambda request: db)
    monkeypatch.setattr(eintraege, "get_owner_id", lambda request: 7)
    monkeypatch.setattr(eintraege, "base_ctx", lambda request: {})
    monkeypatch.setattr(eintraege, "TEMPLATES", FakeTemplates())

    context = asyncio.run(eintraege.eintrag_neu_form(object(), person="Max Muster"))

    assert context["person"] == "Max Muster"
    assert context["ersatzliste"] == [maria]
    assert context["letzten_ersatz"] is maria
    assert aufrufe == [
        ("alle", "Max Muster", 7),
        ("letzten", "Max Muster", 7),
    ]


def test_letzte_ersatzpflegekraft_ist_nach_owner_getrennt(tmp_path):
    db = PflegraDB(tmp_path / "ersatzpflege.db")
    db.ersatz_speichern(Ersatzpflegekraft(
        person="Max Muster", name="Maria Owner 1", owner_id=1,
    ))
    db.ersatz_speichern(Ersatzpflegekraft(
        person="Max Muster", name="Maria Owner 2", owner_id=2,
    ))

    eintrag_owner_1 = PflegeEintrag.from_datum(
        date(2026, 1, 1), "08:00", "09:00", 1.0, "Max Muster",
        ersatz_name="Maria Owner 1",
    )
    eintrag_owner_1.owner_id = 1
    db.insert(eintrag_owner_1)

    eintrag_owner_2 = PflegeEintrag.from_datum(
        date(2026, 1, 2), "08:00", "09:00", 1.0, "Max Muster",
        ersatz_name="Maria Owner 2",
    )
    eintrag_owner_2.owner_id = 2
    db.insert(eintrag_owner_2)

    assert db.ersatz_letzten("Max Muster", 1).name == "Maria Owner 1"
    assert db.ersatz_letzten("Max Muster", 2).name == "Maria Owner 2"
