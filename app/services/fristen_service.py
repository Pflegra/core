"""
services/fristen_service.py — Fristenberechnung für Pflegra

Berechnet aktive Fristen und Hinweise für das Dashboard:
  - Entlastungsbetrag-Übertrag (bis 30. Juni des Folgejahres)
  - VP-Budget Jahresende
  - Jahreswechsel-Hinweise
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List


@dataclass
class Frist:
    titel:      str
    beschreibung: str
    faellig:    date
    dringlichkeit: str   # "ok", "bald", "kritisch"
    person:     str = ""
    link:       str = ""
    betrag:     float = 0.0
    paragraf:   str = ""

    @property
    def tage_bis_faellig(self) -> int:
        return (self.faellig - date.today()).days

    @property
    def ist_abgelaufen(self) -> bool:
        return self.tage_bis_faellig < 0

    @property
    def faellig_str(self) -> str:
        return self.faellig.strftime("%d.%m.%Y")


def berechne_fristen(
    personen_daten: list,   # [{name, vers, bericht, entlastung_verbrauch}]
    aktuelles_jahr: int,
    regelwerk,
    stichtag: date | None = None,
) -> List[Frist]:
    """
    Berechnet alle relevanten Fristen für das Dashboard.

    personen_daten: Liste von Dicts mit Person + Budgetstatus
    """
    fristen = []
    heute = stichtag or date.today()
    monat = heute.month
    jahr = heute.year

    for pd in personen_daten:
        person = pd["name"]
        bericht = pd.get("bericht")
        entlastung_verbrauch = pd.get("entlastung_verbrauch_gesamt", 0.0)
        vers = pd.get("vers")

        # ── Entlastungsbetrag-Übertrag ─────────────────────────────────────
        # Nicht verbrauchte Beträge aus dem Vorjahr können bis 30. Juni
        # des laufenden Jahres für das Vorjahr abgerechnet werden
        if monat <= 6:
            uebertrag_frist = date(jahr, 6, 30)
            monatlich = regelwerk.entlastungsbetrag_monatlich
            max_vorjahr = monatlich * 12
            # Wenn weniger als 80% des Jahresbudgets verbraucht — Hinweis
            if entlastung_verbrauch < max_vorjahr * 0.5:
                tage = (uebertrag_frist - heute).days
                if tage <= 60:
                    dringlichkeit = "kritisch" if tage <= 14 else "bald" if tage <= 30 else "ok"
                    fristen.append(Frist(
                        titel="Entlastungsbetrag-Übertrag",
                        beschreibung=(
                            f"Nicht verbrauchte Entlastungsbeträge aus {jahr-1} "
                            f"können noch bis zum 30. Juni {jahr} abgerechnet werden."
                        ),
                        faellig=uebertrag_frist,
                        dringlichkeit=dringlichkeit,
                        person=person,
                        link="/entlastung/",
                        betrag=monatlich,
                        paragraf="§ 45b SGB XI",
                    ))

        # ── VP-Budget Jahresende ───────────────────────────────────────────
        if bericht and monat >= 10:  # ab Oktober warnen
            jahresende = date(aktuelles_jahr, 12, 31)
            verfuegbar = bericht.budget.verfuegbar_euro
            tage = (jahresende - heute).days

            if verfuegbar > 200 and tage <= 90:
                dringlichkeit = "kritisch" if tage <= 30 else "bald" if tage <= 60 else "ok"
                fristen.append(Frist(
                    titel="VP-Budget läuft ab",
                    beschreibung=(
                        f"Noch {verfuegbar:,.0f} € VP-Budget verfügbar. "
                        f"Nicht genutztes Budget verfällt zum Jahresende."
                    ),
                    faellig=jahresende,
                    dringlichkeit=dringlichkeit,
                    person=person,
                    link="/budget/",
                    betrag=verfuegbar,
                    paragraf="§ 39 SGB XI",
                ))

        # ── Entlastungsbetrag aktueller Monat ungenutzt ────────────────────
        monatlich = regelwerk.entlastungsbetrag_monatlich
        verbrauch_monat = pd.get("entlastung_verbrauch_monat", 0.0)
        # Letzter Tag des Monats
        if monat == 12:
            letzter_tag = date(jahr, 12, 31)
        else:
            letzter_tag = date(jahr, monat + 1, 1) - timedelta(days=1)
        tage_monat = (letzter_tag - heute).days

        if verbrauch_monat < monatlich * 0.1 and tage_monat <= 7:
            fristen.append(Frist(
                titel="Entlastungsbetrag diesen Monat noch ungenutzt",
                beschreibung=(
                    f"Der Entlastungsbetrag für {_monat_name(monat)} ({monatlich:.0f} €) "
                    f"wurde noch nicht genutzt. Beträge können ins nächste Monat übertragen werden, "
                    f"jedoch verfallen sie nach dem 30. Juni des Folgejahres."
                ),
                faellig=letzter_tag,
                dringlichkeit="bald",
                person=person,
                link="/entlastung/",
                betrag=monatlich,
                paragraf="§ 45b SGB XI",
            ))

        # ── Pflegegrad-Überprüfung empfehlen ──────────────────────────────
        if vers and vers.pflegegrad > 0:
            # Wenn letzter Verlaufs-Eintrag älter als 6 Monate
            letztes_pg_datum = pd.get("letztes_pg_datum")
            if letztes_pg_datum:
                alter_tage = (heute - letztes_pg_datum).days
                if alter_tage >= 180:
                    fristen.append(Frist(
                        titel="Pflegegrad-Einschätzung veraltet",
                        beschreibung=(
                            f"Die letzte Pflegegrad-Einschätzung für {person} "
                            f"ist {alter_tage // 30} Monate alt. "
                            f"Bei Veränderungen des Pflegebedarfs lohnt eine neue Einschätzung."
                        ),
                        faellig=letztes_pg_datum + timedelta(days=180),
                        dringlichkeit="ok",
                        person=person,
                        link="/pflegegrad/",
                        paragraf="§ 15 SGB XI",
                    ))

    # Sortieren: kritisch → bald → ok, dann nach Fälligkeitsdatum
    rang = {"kritisch": 0, "bald": 1, "ok": 2}
    fristen.sort(key=lambda f: (rang[f.dringlichkeit], f.faellig))

    return fristen


def _monat_name(monat: int) -> str:
    namen = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
             "Juli", "August", "September", "Oktober", "November", "Dezember"]
    return namen[monat] if 1 <= monat <= 12 else ""
