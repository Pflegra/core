"""
services/aufgaben_service.py — Offene Aufgaben für Pflegra

Sammelt alle offenen Aufgaben aus verschiedenen Quellen:
  - Fristen (Entlastungsbetrag, VP-Budget etc.)
  - Pflegeberatung § 37.3 SGB XI
  - (zukünftig: Dokumente, Widersprüche etc.)

Ampelfarben:
  🔴 überfällig (< 0 Tage)
  🟠 kritisch   (1–7 Tage)
  🟡 bald       (8–30 Tage)
  🟢 ok         (> 30 Tage)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Aufgabe:
    titel:    str
    person:   str
    faellig:  date
    link:     str = ""
    hinweis:  str = ""

    @property
    def tage(self) -> int:
        return (self.faellig - date.today()).days

    @property
    def ampel(self) -> str:
        t = self.tage
        if t < 0:    return "rot"
        if t <= 7:   return "orange"
        if t <= 30:  return "gelb"
        return "gruen"

    @property
    def ampel_emoji(self) -> str:
        return {"rot": "🔴", "orange": "🟠", "gelb": "🟡", "gruen": "🟢"}[self.ampel]

    @property
    def faellig_str(self) -> str:
        return self.faellig.strftime("%d.%m.%Y")

    @property
    def tage_text(self) -> str:
        t = self.tage
        if t < 0:   return f"{abs(t)} Tage überfällig"
        if t == 0:  return "heute fällig"
        if t == 1:  return "morgen fällig"
        return f"in {t} Tagen"


def berechne_aufgaben(fristen: list, beratungen: list) -> list[Aufgabe]:
    """
    Sammelt alle offenen Aufgaben aus Fristen und Pflegeberatungen.
    Gibt eine nach Dringlichkeit sortierte Liste zurück.
    """
    aufgaben = []

    # Aus Fristen-Service
    for f in fristen:
        aufgaben.append(Aufgabe(
            titel=f.titel,
            person=f.person,
            faellig=f.faellig,
            link=f.link,
            hinweis=f.beschreibung,
        ))

    # Aus Pflegeberatungen (nur wenn in 60 Tagen fällig oder überfällig)
    for b in beratungen:
        if b.naechster_termin and b.tage_bis_termin is not None and b.tage_bis_termin <= 60:
            aufgaben.append(Aufgabe(
                titel="Pflegeberatung § 37.3 SGB XI",
                person=b.person,
                faellig=b.naechster_termin,
                link="/pflegeberatung/",
                hinweis="Halbjährlicher Pflichtnachweis für Pflegegeld-Bezieher",
            ))

    # Sortieren: überfällig zuerst, dann nach Fälligkeit
    aufgaben.sort(key=lambda a: a.faellig)
    return aufgaben
