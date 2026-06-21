"""Berechnung einfacher Terminserien fuer einen Kalendermonat."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta


WIEDERHOLUNGEN = ("einmalig", "taeglich", "woechentlich", "monatlich", "jaehrlich")


@dataclass(frozen=True)
class TerminVorkommen:
    termin: object
    datum: date

    @property
    def datum_str(self) -> str:
        return self.datum.strftime("%d.%m.%Y")

    @property
    def titel(self) -> str:
        return self.termin.titel

    @property
    def person(self) -> str:
        return self.termin.person

    @property
    def zeit_text(self) -> str:
        if self.termin.ganztag:
            return "ganztägig"
        if self.termin.uhrzeit_von and self.termin.uhrzeit_bis:
            return f"{self.termin.uhrzeit_von}–{self.termin.uhrzeit_bis}"
        if self.termin.uhrzeit_von:
            return f"ab {self.termin.uhrzeit_von}"
        return "ohne Uhrzeit"

    @property
    def link(self) -> str:
        return f"/termine/{self.termin.id}/bearbeiten"


def _datum_im_monat(jahr: int, monat: int, tag: int) -> date | None:
    if tag > calendar.monthrange(jahr, monat)[1]:
        return None
    return date(jahr, monat, tag)


def vorkommen_im_monat(termin: object, jahr: int, monat: int) -> list[TerminVorkommen]:
    """Erzeugt nur die Vorkommen eines Stammtermins im angefragten Monat."""
    start = termin.datum_date
    if start is None or termin.wiederholung not in WIEDERHOLUNGEN:
        return []

    monatsanfang = date(jahr, monat, 1)
    monatsende = date(jahr, monat, calendar.monthrange(jahr, monat)[1])
    if start > monatsende:
        return []

    daten: list[date] = []
    if termin.wiederholung == "einmalig":
        if monatsanfang <= start <= monatsende:
            daten.append(start)
    elif termin.wiederholung == "taeglich":
        aktuell = max(start, monatsanfang)
        while aktuell <= monatsende:
            daten.append(aktuell)
            aktuell += timedelta(days=1)
    elif termin.wiederholung == "woechentlich":
        aktuell = monatsanfang + timedelta(days=(start.weekday() - monatsanfang.weekday()) % 7)
        if aktuell < start:
            aktuell += timedelta(days=7)
        while aktuell <= monatsende:
            daten.append(aktuell)
            aktuell += timedelta(days=7)
    elif termin.wiederholung == "monatlich":
        kandidat = _datum_im_monat(jahr, monat, start.day)
        if kandidat is not None and kandidat >= start:
            daten.append(kandidat)
    elif termin.wiederholung == "jaehrlich" and monat == start.month and jahr >= start.year:
        kandidat = _datum_im_monat(jahr, monat, start.day)
        if kandidat is not None and kandidat >= start:
            daten.append(kandidat)

    return [TerminVorkommen(termin=termin, datum=d) for d in daten]


def alle_vorkommen_im_monat(termine: list, jahr: int, monat: int) -> list[TerminVorkommen]:
    vorkommen = []
    for termin in termine:
        vorkommen.extend(vorkommen_im_monat(termin, jahr, monat))
    vorkommen.sort(key=lambda v: (v.datum, v.termin.uhrzeit_von, v.termin.titel.lower()))
    return vorkommen


def naechstes_vorkommen(termin: object, ab: date | None = None) -> TerminVorkommen | None:
    """Ermittelt das nächste Vorkommen eines Stammtermins ab dem angegebenen Tag."""
    ab = ab or date.today()
    start = termin.datum_date
    if start is None or termin.wiederholung not in WIEDERHOLUNGEN:
        return None

    kandidat = None
    if termin.wiederholung == "einmalig":
        kandidat = start if start >= ab else None
    elif termin.wiederholung == "taeglich":
        kandidat = max(start, ab)
    elif termin.wiederholung == "woechentlich":
        basis = max(start, ab)
        kandidat = basis + timedelta(days=(start.weekday() - basis.weekday()) % 7)
    elif termin.wiederholung == "monatlich":
        jahr, monat = max((start.year, start.month), (ab.year, ab.month))
        for _ in range(24):
            monat_kandidat = _datum_im_monat(jahr, monat, start.day)
            if monat_kandidat is not None and monat_kandidat >= start and monat_kandidat >= ab:
                kandidat = monat_kandidat
                break
            monat += 1
            if monat > 12:
                monat, jahr = 1, jahr + 1
    elif termin.wiederholung == "jaehrlich":
        for jahr in range(max(start.year, ab.year), max(start.year, ab.year) + 9):
            jahres_kandidat = _datum_im_monat(jahr, start.month, start.day)
            if jahres_kandidat is not None and jahres_kandidat >= start and jahres_kandidat >= ab:
                kandidat = jahres_kandidat
                break

    return TerminVorkommen(termin=termin, datum=kandidat) if kandidat else None


def naechster_termin(termine: list, ab: date | None = None, person: str | None = None,
                     allgemeine: bool = True) -> TerminVorkommen | None:
    """Ermittelt den nächsten Termin insgesamt oder für eine bestimmte Person."""
    kandidaten = []
    for termin in termine:
        if person is not None:
            passt = termin.person == person or (allgemeine and not termin.person)
            if not passt:
                continue
        vorkommen = naechstes_vorkommen(termin, ab)
        if vorkommen:
            kandidaten.append(vorkommen)
    if not kandidaten:
        return None
    return min(kandidaten, key=lambda v: (
        v.datum,
        0 if v.termin.ganztag else 1,
        v.termin.uhrzeit_von,
        v.termin.titel.lower(),
    ))


def dashboard_termine(termine: list, personen: list[str], ab: date | None = None):
    """Liefert die nächsten personengebundenen Termine und den nächsten Gesamttermin."""
    pro_person = {
        person: naechster_termin(termine, ab=ab, person=person, allgemeine=False)
        for person in personen
    }
    return pro_person, naechster_termin(termine, ab=ab)
