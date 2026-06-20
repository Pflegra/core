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
