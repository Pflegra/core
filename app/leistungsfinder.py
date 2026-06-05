"""
leistungsfinder.py — Strukturierte Leistungsberechnung nach SGB XI

Eingaben:
  - pflegegrad: 0–5
  - pflegesetting: "haeuslich" | "stationaer"
  - leistungsart: "pflegegeld" | "sachleistung" | "kombination"

Ausgabe:
  LeistungsfinderErgebnis mit monatlichen, jährlichen und einmaligen Leistungen,
  Kombinationshinweisen und Gesamtübersicht.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List

from pflege_rules import get_regelwerk


@dataclass
class Leistungsposten:
    titel:     str
    betrag:    float
    einheit:   str       # "€/Monat", "€/Jahr", "€/Maßnahme"
    paragraf:  str
    info:      str
    kategorie: str       # "geld", "sachleistung", "vp", "entlastung", "hilfsmittel", "digital", "stationaer"
    hinweis:   str = ""  # optionaler Zusatzhinweis (z.B. Kürzung bei Kombination)


@dataclass
class LeistungsfinderErgebnis:
    pflegegrad:      int
    pflegesetting:   str
    leistungsart:    str
    jahr:            int

    monatlich:       List[Leistungsposten] = field(default_factory=list)
    jaehrlich:       List[Leistungsposten] = field(default_factory=list)
    einmalig:        List[Leistungsposten] = field(default_factory=list)

    kombinations_hinweise: List[str] = field(default_factory=list)
    zusammenfassung: str = ""

    @property
    def summe_monatlich(self) -> float:
        return round(sum(p.betrag for p in self.monatlich), 2)

    @property
    def summe_jaehrlich(self) -> float:
        return round(
            sum(p.betrag for p in self.jaehrlich) +
            sum(p.betrag * 12 for p in self.monatlich),
            2
        )


def berechne_leistungen(
    pflegegrad: int,
    pflegesetting: str = "haeuslich",   # "haeuslich" | "stationaer"
    leistungsart: str = "pflegegeld",   # "pflegegeld" | "sachleistung" | "kombination"
    jahr: int = 0,
) -> LeistungsfinderErgebnis:
    if not jahr:
        jahr = date.today().year
    r = get_regelwerk(jahr)

    ergebnis = LeistungsfinderErgebnis(
        pflegegrad=pflegegrad,
        pflegesetting=pflegesetting,
        leistungsart=leistungsart,
        jahr=jahr,
    )

    if pflegegrad == 0:
        ergebnis.zusammenfassung = (
            "Bei Pflegegrad 0 besteht kein Anspruch auf Pflegeleistungen nach SGB XI. "
            "Erst ab Pflegegrad 1 sind einzelne Leistungen (Entlastungsbetrag, Hilfsmittel) möglich."
        )
        return ergebnis

    # ── Häusliche Pflege ─────────────────────────────────────────────
    if pflegesetting == "haeuslich":

        if pflegegrad >= 2:
            # Pflegegeld (§ 37)
            if leistungsart in ("pflegegeld", "kombination"):
                pg_betrag = r.pflegegeld_monatlich(pflegegrad)
                if leistungsart == "kombination":
                    # Bei Kombination: Pflegegeld anteilig (hier 50% als Beispiel — wird im Hinweis erklärt)
                    pg_betrag_kombi = round(pg_betrag * 0.5, 2)
                    ergebnis.monatlich.append(Leistungsposten(
                        titel="Pflegegeld (anteilig)",
                        betrag=pg_betrag_kombi,
                        einheit="€/Monat",
                        paragraf="§ 37 SGB XI",
                        info="Für selbst organisierte Pflege durch Angehörige oder Bekannte.",
                        kategorie="geld",
                        hinweis=f"Bei Kombination mit Sachleistung: Pflegegeld wird anteilig ausgezahlt. "
                                f"Voller Betrag: {pg_betrag:.2f} €/Monat.",
                    ))
                else:
                    ergebnis.monatlich.append(Leistungsposten(
                        titel="Pflegegeld",
                        betrag=pg_betrag,
                        einheit="€/Monat",
                        paragraf="§ 37 SGB XI",
                        info="Für selbst organisierte Pflege durch Angehörige oder Bekannte.",
                        kategorie="geld",
                    ))

            # Pflegesachleistungen (§ 36)
            if leistungsart in ("sachleistung", "kombination"):
                sl_betrag = r.sachleistung_monatlich(pflegegrad)
                ergebnis.monatlich.append(Leistungsposten(
                    titel="Pflegesachleistungen",
                    betrag=sl_betrag,
                    einheit="€/Monat",
                    paragraf="§ 36 SGB XI",
                    info="Für ambulante Pflegedienste (körperbezogene Pflege, Betreuung).",
                    kategorie="sachleistung",
                ))

            # Tagespflege (§ 41)
            tp_betrag = r.tagespflege_monatlich(pflegegrad)
            ergebnis.monatlich.append(Leistungsposten(
                titel="Tagespflege",
                betrag=tp_betrag,
                einheit="€/Monat",
                paragraf="§ 41 SGB XI",
                info="Teilstationäre Pflege tagsüber in einer Tageseinrichtung. "
                     "Anspruch zusätzlich zu Pflegegeld/Sachleistung.",
                kategorie="sachleistung",
            ))

            # Verhinderungspflege (§ 39)
            ergebnis.jaehrlich.append(Leistungsposten(
                titel="Verhinderungspflege",
                betrag=r.vp_budget_jahresbetrag,
                einheit="€/Jahr",
                paragraf="§ 39 SGB XI",
                info="Wenn die Pflegeperson verhindert ist (Urlaub, Krankheit). Max. 56 Tage/Jahr.",
                kategorie="vp",
                hinweis="Gemeinsamer Topf mit Kurzzeitpflege. Ungenutzte KZP-Mittel können für VP genutzt werden.",
            ))

            # Kurzzeitpflege (§ 42)
            ergebnis.jaehrlich.append(Leistungsposten(
                titel="Kurzzeitpflege",
                betrag=r.vp_budget_jahresbetrag,
                einheit="€/Jahr (gemeinsamer Topf VP)",
                paragraf="§ 42 SGB XI",
                info="Stationäre Kurzzeitpflege, z.B. nach Krankenhausaufenthalt.",
                kategorie="vp",
                hinweis="Gemeinsamer Topf mit Verhinderungspflege (§ 39). "
                        f"Maximal {r.vp_budget_jahresbetrag:.0f} € insgesamt.",
            ))

        # Entlastungsbetrag (§ 45b) — ab PG1
        ergebnis.monatlich.append(Leistungsposten(
            titel="Entlastungsbetrag",
            betrag=r.entlastungsbetrag_monatlich,
            einheit="€/Monat",
            paragraf="§ 45b SGB XI",
            info="Für Betreuungs- und Entlastungsangebote, Alltagshelfer, Haushaltshilfe. "
                 "Nicht verbrauchte Beträge können ins Folgejahr übertragen werden (bis 30. Juni).",
            kategorie="entlastung",
        ))

        # Pflegehilfsmittel (§ 40) — ab PG1
        ergebnis.monatlich.append(Leistungsposten(
            titel="Pflegehilfsmittel",
            betrag=r.pflegehilfsmittel_monatlich,
            einheit="€/Monat",
            paragraf="§ 40 SGB XI",
            info="Pauschale für zum Verbrauch bestimmte Pflegehilfsmittel (Handschuhe, Bettschutz etc.).",
            kategorie="hilfsmittel",
        ))

        # DiPA (§ 40a) — ab PG1
        ergebnis.monatlich.append(Leistungsposten(
            titel="Digitale Pflegeanwendungen (DiPA)",
            betrag=r.dipa_app_monatlich,
            einheit="€/Monat",
            paragraf="§ 40a SGB XI",
            info="Für zugelassene Pflege-Apps (z.B. Sturzprävention, Gedächtnistraining).",
            kategorie="digital",
        ))

        # Wohnumfeld (§ 40) — einmalig
        ergebnis.einmalig.append(Leistungsposten(
            titel="Wohnumfeldverbesserung",
            betrag=r.wohnumfeld_je_massnahme,
            einheit="€/Maßnahme",
            paragraf="§ 40 SGB XI",
            info="Einmalig je Maßnahme, z.B. Badumbau, Rampen, Treppenlifte. "
                 "Bis zu 4 Personen im Haushalt: Beträge addieren sich.",
            kategorie="hilfsmittel",
        ))

    # ── Vollstationäre Pflege ─────────────────────────────────────────
    else:
        pauschalen = {1: 0, 2: 770, 3: 1_262, 4: 1_775, 5: 2_005}
        if pflegegrad >= 2:
            ergebnis.monatlich.append(Leistungsposten(
                titel="Vollstationäre Pflege",
                betrag=float(pauschalen.get(pflegegrad, 0)),
                einheit="€/Monat",
                paragraf="§ 43 SGB XI",
                info="Pflegekassenzuschuss bei Heimunterbringung. "
                     "Deckt nur einen Teil der Heimkosten — der Eigenanteil bleibt.",
                kategorie="stationaer",
                hinweis=(
                    "Der verbleibende Eigenanteil setzt sich zusammen aus: "
                    "Pflegekosten-Eigenanteil (einrichtungseinheitlicher Eigenanteil, EEE), "
                    "Unterkunft & Verpflegung sowie Investitionskosten. "
                    "Je nach Einrichtung und Bundesland liegt der Gesamteigenanteil "
                    "typischerweise zwischen 1.500 und 3.000 €/Monat."
                ),
            ))

            # § 43c — Zuschläge zum EEE gestaffelt nach Aufenthaltsdauer
            ergebnis.kombinations_hinweise.append(
                "💡 Eigenanteil-Zuschläge (§ 43c SGB XI): Die Pflegekasse übernimmt "
                "einen gestaffelten Zuschlag zum einrichtungseinheitlichen Eigenanteil (EEE) — "
                "15 % im 1. Jahr, 30 % im 2. Jahr, 50 % im 3. Jahr, 75 % ab dem 4. Jahr. "
                "Der Eigenanteil sinkt also mit zunehmender Aufenthaltsdauer."
            )
            ergebnis.kombinations_hinweise.append(
                "💡 Sozialhilfe (§ 19 SGB XII): Reicht das Einkommen nicht für den Eigenanteil, "
                "kann beim zuständigen Sozialamt Hilfe zur Pflege beantragt werden."
            )

        # Entlastungsbetrag auch stationär — ab PG1
        ergebnis.monatlich.append(Leistungsposten(
            titel="Entlastungsbetrag",
            betrag=r.entlastungsbetrag_monatlich,
            einheit="€/Monat",
            paragraf="§ 45b SGB XI",
            info="Auch bei stationärer Pflege nutzbar, z.B. für zusätzliche Betreuungsangebote.",
            kategorie="entlastung",
        ))

    # ── Kombinationshinweise ──────────────────────────────────────────
    if pflegesetting == "haeuslich" and pflegegrad >= 2:
        if leistungsart == "kombination":
            ergebnis.kombinations_hinweise.append(
                "💡 Kombination: Pflegesachleistung + anteiliges Pflegegeld — "
                "wird nicht in Anspruch genommene Sachleistung als Pflegegeld-Anteil ausgezahlt."
            )
        ergebnis.kombinations_hinweise.append(
            "💡 Tagespflege kann zusätzlich zu Pflegegeld und Sachleistung in Anspruch genommen werden (§ 41 Abs. 4)."
        )
        ergebnis.kombinations_hinweise.append(
            "💡 VP und KZP teilen sich einen gemeinsamen Jahresbetrag von "
            f"{r.vp_budget_jahresbetrag:,.0f} €. Nicht genutzte KZP-Mittel erhöhen das VP-Budget."
        )

    # ── Zusammenfassung ───────────────────────────────────────────────
    setting_label = "häusliche Pflege" if pflegesetting == "haeuslich" else "vollstationäre Pflege"
    art_label = {"pflegegeld": "Pflegegeld", "sachleistung": "Pflegesachleistung",
                 "kombination": "Kombination"}.get(leistungsart, "")

    if pflegegrad == 1:
        ergebnis.zusammenfassung = (
            f"Bei Pflegegrad 1 und {setting_label} besteht Anspruch auf Entlastungsbetrag, "
            f"Pflegehilfsmittel, DiPA und Wohnumfeldverbesserung. "
            f"Pflegegeld und Sachleistungen sind erst ab Pflegegrad 2 möglich."
        )
    else:
        ergebnis.zusammenfassung = (
            f"Bei Pflegegrad {pflegegrad} und {setting_label} "
            f"({'mit ' + art_label if art_label else ''}) "
            f"ergibt sich ein monatlicher Leistungsanspruch von ca. {ergebnis.summe_monatlich:,.2f} €."
        )

    return ergebnis
