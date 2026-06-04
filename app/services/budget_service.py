"""
Pflegra  BudgetService
Kapselt alle Budgetberechnungen. GUI ruft nur noch diesen Service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from models import PflegeEintrag, PflegraDB, MONATE_DE
from calculations import (
    berechne_budget_status, berechne_prognose, berechne_jahres_summe,
    berechne_monats_summe, alle_personen_budget,
    BudgetStatus, Prognose, JahresSumme, MonatsSumme,
    STUNDENSATZ_DEFAULT, BUDGET_JAHRESBETRAG,
    BUDGET_VERHINDERUNGSPFLEGE, BUDGET_AUFSTOCKUNG_MAX, BUDGET_GESAMT_MAX,
    MAX_TAGE_TAGEWEISE,
)
from config import Konfiguration


@dataclass
class PersonenBudgetBericht:
    """Vollstndiger Budgetbericht fr eine Person in einem Jahr."""
    person:       str
    jahr:         int
    budget:       BudgetStatus
    prognose:     Prognose
    jahressumme:  JahresSumme
    monatshefte:  list[MonatsSumme] = field(default_factory=list)

    @property
    def ampel(self) -> str:
        """Gibt 'gruen', 'gelb' oder 'rot' zurck."""
        if self.budget.ausgeschoepft_prozent >= 100:
            return "rot"
        if (self.budget.ausgeschoepft_prozent >= 80
                or self.prognose.budget_wird_ueüberschritten):
            return "gelb"
        return "gruen"


class BudgetService:
    """
    Zentrale Geschftslogik fr Budgetberechnungen.
    Wird von BudgetView und ExportView verwendet.
    """

    def __init__(self, db: PflegraDB, konfig: Konfiguration):
        self._db     = db
        self._konfig = konfig

    @property
    def stundensatz(self) -> float:
        return self._konfig.stundensatz

    @property
    def budget_basis(self) -> float:
        return self._konfig.budget_basis

    @property
    def budget_gesamt(self) -> float:
        return self._konfig.budget_gesamt

    def bericht_fuer_person(
        self,
        person: str,
        jahr: int,
        eintraege: Optional[list[PflegeEintrag]] = None,
        stundensatz: Optional[float] = None,
    ) -> PersonenBudgetBericht:
        """Erstellt einen vollständigen Budgetbericht fr eine Person.

        stundensatz berschreibt den Config-Wert (z.B. aus GUI-Eingabefeld).
        """
        if eintraege is None:
            eintraege = self._db.alle()
        sz = stundensatz if stundensatz is not None else self.stundensatz

        budget     = berechne_budget_status(
            eintraege, person, jahr, sz,
            self.budget_basis, self._konfig.budget_aufstockung_max,
        )
        prognose   = berechne_prognose(
            eintraege, person, jahr, sz, self.budget_gesamt,
        )
        jahressumme = berechne_jahres_summe(
            eintraege, person, jahr, sz,
        )
        return PersonenBudgetBericht(
            person=person,
            jahr=jahr,
            budget=budget,
            prognose=prognose,
            jahressumme=jahressumme,
            monatshefte=jahressumme.monate,
        )

    def alle_berichte(
        self,
        jahr: int,
        eintraege: Optional[list[PflegeEintrag]] = None,
        stundensatz: Optional[float] = None,
    ) -> list[PersonenBudgetBericht]:
        """Erstellt Berichte fr alle Personen in einem Jahr.

        stundensatz berschreibt den Config-Wert (z.B. aus GUI-Eingabefeld).
        """
        if eintraege is None:
            eintraege = self._db.alle()
        personen = sorted({e.person for e in eintraege if e.jahr == jahr})
        return [self.bericht_fuer_person(p, jahr, eintraege, stundensatz) for p in personen]

    def restbudget_in_stunden(self, person: str, jahr: int) -> float:
        """Schnellabfrage: Wie viele Stunden sind noch im Budget?"""
        eintraege = self._db.nach_person_und_jahr(person, jahr)
        bs = berechne_budget_status(
            eintraege, person, jahr, self.stundensatz,
            self.budget_basis, self._konfig.budget_aufstockung_max,
        )
        return bs.restbudget_in_stunden

    def warnung_fuer_alle(self, jahr: int, eintraege=None) -> list[dict]:
        """
        Gibt strukturierte Warnungen zurück — sprachunabhängig.
        Jede Warnung: {"typ": str, "person": str, "werte": dict}
        Typen: "ausgeschoepft", "prognose", "prozent", "tage_grenze", "tage_fast"
        """
        berichte = self.alle_berichte(jahr, eintraege=eintraege)
        warnungen = []
        for b in berichte:
            if b.ampel == "rot":
                warnungen.append({
                    "typ":    "ausgeschoepft",
                    "person": b.person,
                    "werte":  {"verbraucht": b.budget.verbraucht, "budget": self.budget_gesamt},
                })
            elif b.ampel == "gelb":
                if b.prognose.budget_wird_ueüberschritten:
                    warnungen.append({
                        "typ":    "prognose",
                        "person": b.person,
                        "werte":  {"differenz": -b.prognose.differenz, "hochrechnung": b.prognose.hochrechnung_kosten},
                    })
                else:
                    warnungen.append({
                        "typ":    "prozent",
                        "person": b.person,
                        "werte":  {"prozent": b.budget.ausgeschoepft_prozent},
                    })
            if b.budget.tage_grenze_erreicht:
                warnungen.append({
                    "typ":    "tage_grenze",
                    "person": b.person,
                    "werte":  {"tage": b.budget.tage_tageweise, "max": MAX_TAGE_TAGEWEISE},
                })
            elif b.budget.tage_tageweise >= int(MAX_TAGE_TAGEWEISE * 0.8):
                warnungen.append({
                    "typ":    "tage_fast",
                    "person": b.person,
                    "werte":  {"tage": b.budget.tage_tageweise, "max": MAX_TAGE_TAGEWEISE,
                               "rest": b.budget.resttage_tageweise},
                })
        return warnungen
