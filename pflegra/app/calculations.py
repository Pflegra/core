"""
Pflegra  Businesslogik / Berechnungen

Alle fachlichen Berechnungen rund um Verhinderungspflege:
  - Kosten pro Eintrag / Zeitraum
  - Restbudget ( 39 SGB XI)
  - Monatssummierung
  - Jahresprognose
  - 56-Tage-Anspruchsgrenze (tageweise)
  - Pflegegeld-Halbierung bei tageweiser Vertretung

Gesetzlicher Rahmen (ab 01.07.2025  Reform Pflegekompetenzgesetz):
   39 SGB XI: Gemeinsamer Jahresbetrag 3.539  fr Verhinderungs-
  UND Kurzzeitpflege (flexibel einsetzbar, kein starrer Aufstockungsmechanismus).
  Anspruchsdauer tageweise: max. 56 Tage / Kalenderjahr.
  Pflegegeld: Bei tageweiser VP ( 8h) wird das Pflegegeld fr diese
  Tage um die Hlfte gekrzt. Bei stundenweiser VP (<8h) bleibt es voll erhalten.
  Verwandte 1./2. Grades oder Haushaltsangehrige: max. das Zweifache
  des Pflegegeldes je Tag erstattungsfhig.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import calendar

from models import PflegeEintrag, MONATE_DE, ART_TAGEWEISE, ART_STUNDENWEISE
from pflege_rules import get_regelwerk, REGELN_AKTUELL

# ── Kompatibilitäts-Konstanten (importiert aus pflege_rules) ──────────────────
# Direktzugriff für bestehenden Code — Quelle der Wahrheit: pflege_rules.py
BUDGET_JAHRESBETRAG        = REGELN_AKTUELL.vp_budget_jahresbetrag
BUDGET_VERHINDERUNGSPFLEGE = BUDGET_JAHRESBETRAG
BUDGET_AUFSTOCKUNG_MAX     = 0.00
BUDGET_GESAMT_MAX          = BUDGET_JAHRESBETRAG
MAX_TAGE_TAGEWEISE         = REGELN_AKTUELL.vp_max_tage_tageweise
STUNDENSATZ_DEFAULT        = REGELN_AKTUELL.stundensatz_referenz
PFLEGEGELD_MONATLICH: dict[int, float] = {
    pg: REGELN_AKTUELL.pflegegeld_monatlich(pg) for pg in range(1, 6)
}


# ------------------------------------------------------------------ #
#  Ergebnis-Datenklassen                                               #
# ------------------------------------------------------------------ #

@dataclass
class MonatsSumme:
    """Aggregierte Werte fr einen Kalendermonat."""
    person:    str
    jahr:      int
    monat:     int
    einsaetze: int
    stunden:   float
    kosten:    float
    tage_tageweise: int = 0      # Anzahl tageweiser Einstze im Monat

    @property
    def monat_name(self) -> str:
        return MONATE_DE[self.monat]

    def __str__(self) -> str:
        return (
            f"{self.monat_name} {self.jahr} | {self.person} | "
            f"{self.einsaetze} Einstze | {self.stunden:.2f} h | "
            f"{self.kosten:.2f} "
        )


@dataclass
class JahresSumme:
    """Aggregierte Werte fr ein Kalenderjahr."""
    person:          str
    jahr:            int
    einsaetze:       int
    stunden:         float
    kosten:          float
    monate:          list[MonatsSumme] = field(default_factory=list)
    tage_tageweise:  int = 0     # Gesamtanzahl tageweiser Tage im Jahr

    @property
    def abgerechnete_monate(self) -> list[int]:
        return sorted({m.monat for m in self.monate if m.einsaetze > 0})


@dataclass
class BudgetStatus:
    """Budgetauswertung fr eine Person in einem Jahr (gemeinsamer Topf ab 2025)."""
    person:           str
    jahr:             int
    stundensatz:      float
    budget_gesamt:    float       # gemeinsamer Jahresbetrag

    verbraucht:       float       # bereits abgerechnet in 
    stunden_gesamt:   float
    tage_tageweise:   int = 0     # genutzte tageweise Tage

    # Kompatibilitts-Felder (werden aus budget_gesamt abgeleitet)
    @property
    def budget_basis(self) -> float:
        return self.budget_gesamt

    @property
    def budget_aufstockung(self) -> float:
        return 0.0

    @property
    def aufstockung_genutzt(self) -> float:
        return 0.0

    @property
    def restbudget_basis(self) -> float:
        return self.restbudget_gesamt

    @property
    def restbudget_gesamt(self) -> float:
        return max(0.0, self.budget_gesamt - self.verbraucht)

    @property
    def ausgeschoepft_prozent(self) -> float:
        if self.budget_gesamt == 0:
            return 0.0
        return min(100.0, self.verbraucht / self.budget_gesamt * 100)

    @property
    def ist_im_basis_budget(self) -> bool:
        return self.verbraucht <= self.budget_gesamt

    @property
    def restbudget_in_stunden(self) -> float:
        if self.stundensatz == 0:
            return 0.0
        return self.restbudget_gesamt / self.stundensatz

    @property
    def resttage_tageweise(self) -> int:
        """Noch verfgbare tageweise Einsatztage (max. 56/Jahr)."""
        return max(0, MAX_TAGE_TAGEWEISE - self.tage_tageweise)

    @property
    def tage_grenze_erreicht(self) -> bool:
        return self.tage_tageweise >= MAX_TAGE_TAGEWEISE

    def __str__(self) -> str:
        return (
            f"{self.person} / {self.jahr}\n"
            f"  Verbraucht:    {self.verbraucht:>8.2f}  "
            f"({self.ausgeschoepft_prozent:.1f} %)\n"
            f"  Restbudget:    {self.restbudget_gesamt:>8.2f}   "
            f" {self.restbudget_in_stunden:.1f} h\n"
            f"  Budget gesamt: {self.budget_gesamt:>8.2f} \n"
            f"  Tageweise:     {self.tage_tageweise}/{MAX_TAGE_TAGEWEISE} Tage"
        )


@dataclass
class Prognose:
    """Jahresprognose basierend auf bisherigem Verbrauch."""
    person:              str
    jahr:                int
    stundensatz:         float
    abgeschlossene_monate: int
    hochrechnung_stunden:  float    # linear hochgerechnet auf 12 Monate
    hochrechnung_kosten:   float
    budget_gesamt:         float
    budget_wird_ueüberschritten: bool
    hochrechnung_tage_tageweise: int = 0

    @property
    def differenz(self) -> float:
        """Positiv = Puffer; negativ = berschreitung."""
        return self.budget_gesamt - self.hochrechnung_kosten

    def __str__(self) -> str:
        warnung = "  BUDGET-BERSCHREITUNG PROGNOSTIZIERT" if self.budget_wird_ueüberschritten else ""
        return (
            f"Prognose {self.person} / {self.jahr}  "
            f"(Basis: {self.abgeschlossene_monate} Monate)\n"
            f"  Hochrechnung: {self.hochrechnung_stunden:.1f} h  "
            f"/ {self.hochrechnung_kosten:.2f} \n"
            f"  Differenz:    {self.differenz:+.2f} {warnung}"
        )


# ------------------------------------------------------------------ #
#  Berechnungsfunktionen                                               #
# ------------------------------------------------------------------ #

def berechne_kosten(eintrag: PflegeEintrag, stundensatz: float = STUNDENSATZ_DEFAULT) -> float:
    """Berechnet die Kosten eines einzelnen Eintrags."""
    return round(eintrag.stunden * stundensatz, 2)


def berechne_monats_summe(
    eintraege: list[PflegeEintrag],
    person: str,
    jahr: int,
    monat: int,
    stundensatz: float = STUNDENSATZ_DEFAULT,
) -> MonatsSumme:
    """Summiert Einstze, Stunden und Kosten fr einen Monat."""
    gefiltert = [
        e for e in eintraege
        if e.person == person and e.jahr == jahr and e.monat == monat
    ]
    stunden = sum(e.stunden for e in gefiltert)
    tage_tageweise = sum(1 for e in gefiltert if e.art == ART_TAGEWEISE)
    return MonatsSumme(
        person=person,
        jahr=jahr,
        monat=monat,
        einsaetze=len(gefiltert),
        stunden=round(stunden, 2),
        kosten=round(stunden * stundensatz, 2),
        tage_tageweise=tage_tageweise,
    )


def berechne_jahres_summe(
    eintraege: list[PflegeEintrag],
    person: str,
    jahr: int,
    stundensatz: float = STUNDENSATZ_DEFAULT,
) -> JahresSumme:
    """Erstellt eine vollständige Jahressumme mit allen Monatswerten."""
    monate = [
        berechne_monats_summe(eintraege, person, jahr, m, stundensatz)
        for m in range(1, 13)
    ]

    gesamt_stunden     = round(sum(m.stunden for m in monate), 2)
    gesamt_kosten      = round(sum(m.kosten  for m in monate), 2)
    gesamt_tage_tage   = sum(m.tage_tageweise for m in monate)

    return JahresSumme(
        person=person,
        jahr=jahr,
        einsaetze=sum(m.einsaetze for m in monate),
        stunden=gesamt_stunden,
        kosten=gesamt_kosten,
        monate=monate,
        tage_tageweise=gesamt_tage_tage,
    )


def berechne_budget_status(
    eintraege: list[PflegeEintrag],
    person: str,
    jahr: int,
    stundensatz: float = STUNDENSATZ_DEFAULT,
    budget_basis: float = 0.0,              # 0 = aus pflege_rules ermitteln
    budget_aufstockung: float = 0.0,
) -> BudgetStatus:
    """
    Berechnet den aktuellen Budgetstatus für eine Person in einem Jahr.
    Verwendet jahresspezifische Regeln aus pflege_rules.py.
    """
    regeln = get_regelwerk(jahr)
    if budget_basis == 0.0:
        budget_basis = regeln.vp_budget_jahresbetrag
    jahressumme   = berechne_jahres_summe(eintraege, person, jahr, stundensatz)
    budget_gesamt = budget_basis + budget_aufstockung

    return BudgetStatus(
        person=person,
        jahr=jahr,
        stundensatz=stundensatz,
        budget_gesamt=budget_gesamt,
        verbraucht=jahressumme.kosten,
        stunden_gesamt=jahressumme.stunden,
        tage_tageweise=jahressumme.tage_tageweise,
    )


def berechne_prognose(
    eintraege: list[PflegeEintrag],
    person: str,
    jahr: int,
    stundensatz: float = STUNDENSATZ_DEFAULT,
    budget_gesamt: float = 0.0,   # 0 = aus pflege_rules für dieses Jahr ableiten
) -> Prognose:
    """
    Lineare Hochrechnung auf 12 Monate basierend auf abgeschlossenen Monaten.
    Beinhaltet auch Prognose für tageweise Einsätze (vs. 56-Tage-Grenze).
    Verwendet jahresspezifisches Budget aus pflege_rules.py.
    """
    # Jahresspezifisches Budget — nie mehr BUDGET_GESAMT_MAX hardcoded
    if budget_gesamt == 0.0:
        budget_gesamt = get_regelwerk(jahr).vp_budget_jahresbetrag
    jahressumme = berechne_jahres_summe(eintraege, person, jahr, stundensatz)
    aktive_monate = [m for m in jahressumme.monate if m.einsaetze > 0]
    n = len(aktive_monate)

    if n == 0:
        return Prognose(
            person=person, jahr=jahr, stundensatz=stundensatz,
            abgeschlossene_monate=0,
            hochrechnung_stunden=0.0, hochrechnung_kosten=0.0,
            budget_gesamt=budget_gesamt,
            budget_wird_ueüberschritten=False,
            hochrechnung_tage_tageweise=0,
        )

    durchschnitt_stunden  = jahressumme.stunden / n
    durchschnitt_kosten   = jahressumme.kosten  / n
    durchschnitt_tage     = jahressumme.tage_tageweise / n

    hochrechnung_stunden = round(durchschnitt_stunden * 12, 2)
    hochrechnung_kosten  = round(durchschnitt_kosten  * 12, 2)
    hochrechnung_tage    = round(durchschnitt_tage    * 12)

    return Prognose(
        person=person,
        jahr=jahr,
        stundensatz=stundensatz,
        abgeschlossene_monate=n,
        hochrechnung_stunden=hochrechnung_stunden,
        hochrechnung_kosten=hochrechnung_kosten,
        budget_gesamt=budget_gesamt,
        budget_wird_ueüberschritten=hochrechnung_kosten > budget_gesamt,
        hochrechnung_tage_tageweise=hochrechnung_tage,
    )


def berechne_pflegegeld_halbierung(
    eintraege: list[PflegeEintrag],
    person: str,
    jahr: int,
    monat: int,
    pflegegrad: int = 0,
) -> dict:
    """
    Berechnet die Pflegegeld-Halbierung fr tageweise Einstze.

    Bei tageweiser VP ( 8h tglich) wird das Pflegegeld fr diese Tage
    um die Hlfte gekrzt. Gibt Hinweis-Dict zurck.
    """
    gefiltert = [
        e for e in eintraege
        if e.person == person and e.jahr == jahr
        and e.monat == monat and e.art == ART_TAGEWEISE
    ]
    tage = len(gefiltert)
    if tage == 0 or pflegegrad == 0:
        return {"tage": 0, "kuerzung_gesamt": 0.0, "hinweis": ""}

    pflegegeld_tag = PFLEGEGELD_MONATLICH.get(pflegegrad, 0.0) / 30
    kuerzung_tag   = pflegegeld_tag / 2
    kuerzung_ges   = round(kuerzung_tag * tage, 2)

    return {
        "tage": tage,
        "pflegegrad": pflegegrad,
        "pflegegeld_tag": round(pflegegeld_tag, 2),
        "kuerzung_tag": round(kuerzung_tag, 2),
        "kuerzung_gesamt": kuerzung_ges,
        "hinweis": (
            f"{tage} tageweise Einstze  Pflegegeld PG {pflegegrad} "
            f"fr {tage} Tage um je {kuerzung_tag:.2f}  gekrzt "
            f"(Gesamt: -{kuerzung_ges:.2f} )"
        ),
    }


def alle_personen_budget(
    eintraege: list[PflegeEintrag],
    jahr: int,
    stundensatz: float = STUNDENSATZ_DEFAULT,
) -> list[BudgetStatus]:
    """Berechnet den Budgetstatus fr alle Personen in einem Jahr."""
    personen = sorted({e.person for e in eintraege if e.jahr == jahr})
    return [
        berechne_budget_status(eintraege, p, jahr, stundensatz)
        for p in personen
    ]
