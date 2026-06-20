"""
services/kalender_service.py — Pflege-Kalender für Pflegra

Aggregiert Kalenderereignisse aus bestehenden Quellen, ohne eigene Tabelle:
  - eigene_fristen (Termine, Dokumente, Anträge, Arzt, Behörde, Sonstiges)
  - pflegeberatung (berechneter nächster Termin, alle Personen, ohne 60-Tage-Limit)
  - aufgaben (Entlastungsbetrag-Übertrag etc. aus fristen_service)

Alles ganztägig (keine Uhrzeit/Dauer in den Quelldaten).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class KalenderEreignis:
    datum:      date
    titel:      str
    person:     str
    quelle:     str   # "frist", "pflegeberatung", "aufgabe"
    kategorie:  str = ""
    link:       str = ""
    erledigt:   bool = False
    zeit_text:  str = ""

    @property
    def datum_str(self) -> str:
        return self.datum.strftime("%d.%m.%Y")

    @property
    def quelle_icon(self) -> str:
        return {
            "frist": "📅",
            "pflegeberatung": "🤝",
            "aufgabe": "🟡",
            "dokument": "📄",
            "tagebuch": "📝",
            "termin": "📅",
        }.get(self.quelle, "📌")


def baue_kalender(
    eigene_fristen: list,
    pflegeberatungen: list,
    fristen_aus_service: list,
    monat: int,
    jahr: int,
    dokumente: list = None,
    tagebuch_eintraege: list = None,
    termin_vorkommen: list = None,
) -> dict[int, list[KalenderEreignis]]:
    """
    Baut eine Kalenderansicht für einen Monat.
    Gibt ein Dict {tag: [KalenderEreignis, ...]} zurück.

    eigene_fristen: Liste von EigeneFrist-Objekten (aus web.routers.fristen)
    pflegeberatungen: Liste von Pflegeberatung-Objekten, neueste pro Person
    fristen_aus_service: Liste von Frist-Objekten (aus services.fristen_service)
    dokumente: optional, Liste von Dokument-Objekten (für Anzeige "Dokument hochgeladen")
    tagebuch_eintraege: optional, Liste von Tagebucheintrag-Objekten
    termin_vorkommen: optional, im Zielmonat expandierte eigene Termine
    """
    tage: dict[int, list[KalenderEreignis]] = {}

    def _add(ereignis: KalenderEreignis):
        if ereignis.datum.month == monat and ereignis.datum.year == jahr:
            tage.setdefault(ereignis.datum.day, []).append(ereignis)

    # Eigene Fristen (alle, auch erledigte werden im Kalender angezeigt, aber markiert)
    for f in eigene_fristen:
        d = f.datum_date
        if d is None:
            continue
        _add(KalenderEreignis(
            datum=d,
            titel=f.titel,
            person=f.person,
            quelle="frist",
            kategorie=f.kategorie_label,
            link="/fristen/",
            erledigt=f.ist_erledigt,
        ))

    # Pflegeberatung: nächster Termin pro Person, OHNE 60-Tage-Limit (anders als Aufgaben-Service)
    for b in pflegeberatungen:
        termin = b.naechster_termin
        if termin is None:
            continue
        _add(KalenderEreignis(
            datum=termin,
            titel="Pflegeberatung § 37.3 SGB XI",
            person=b.person,
            quelle="pflegeberatung",
            kategorie="Pflegeberatung",
            link="/pflegeberatung/",
        ))

    # Automatische Fristen aus fristen_service (Entlastungsbetrag-Übertrag etc.)
    for f in fristen_aus_service:
        _add(KalenderEreignis(
            datum=f.faellig,
            titel=f.titel,
            person=f.person,
            quelle="aufgabe",
            kategorie=f.paragraf or "Frist",
            link=f.link,
        ))

    # Dokumente (informativ: "Dokument hochgeladen")
    if dokumente:
        for d in dokumente:
            try:
                dd = date.fromisoformat(d.datum[:10])
            except Exception:
                continue
            _add(KalenderEreignis(
                datum=dd,
                titel=f"📄 {d.titel}",
                person=d.person,
                quelle="dokument",
                kategorie=d.kategorie,
                link="/dokumente/",
            ))

    # Tagebucheinträge (informativ)
    if tagebuch_eintraege:
        for t in tagebuch_eintraege:
            try:
                td = date.fromisoformat(t.datum[:10])
            except Exception:
                continue
            _add(KalenderEreignis(
                datum=td,
                titel=f"📝 {t.titel or 'Tagebucheintrag'}",
                person=t.person,
                quelle="tagebuch",
                kategorie="Tagebuch",
                link="/tagebuch/chronik",
            ))

    # Eigene einmalige und wiederkehrende Termine
    if termin_vorkommen:
        for vorkommen in termin_vorkommen:
            termin = vorkommen.termin
            _add(KalenderEreignis(
                datum=vorkommen.datum,
                titel=termin.titel,
                person=termin.person,
                quelle="termin",
                kategorie=termin.wiederholung_label,
                link=f"/termine/{termin.id}/bearbeiten",
                zeit_text=termin.zeit_text,
            ))

    # Innerhalb jedes Tages nach Person sortieren
    for tag in tage:
        tage[tag].sort(key=lambda e: (e.erledigt, bool(e.zeit_text and e.zeit_text != "Ganztägig"), e.zeit_text, e.person))

    return tage


MONATSNAMEN = {
    1: "Januar", 2: "Februar", 3: "März", 4: "April",
    5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
    9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
}


def monat_navigation(monat: int, jahr: int) -> tuple[tuple[int, int], tuple[int, int]]:
    """Gibt (vorheriger_monat_jahr, naechster_monat_jahr) als Tupel zurück."""
    if monat == 1:
        prev = (12, jahr - 1)
    else:
        prev = (monat - 1, jahr)
    if monat == 12:
        nxt = (1, jahr + 1)
    else:
        nxt = (monat + 1, jahr)
    return prev, nxt
