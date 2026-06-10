"""
Pflegra – Pflege-Regelwerk
Zentrale Quelle für alle gesetzlichen Beträge, Grenzen und Regeln.

Struktur:
    PflegeRegeln(jahr)  →  gibt das Regelwerk für ein bestimmtes Jahr zurück
    REGELN_AKTUELL      →  Alias für das aktuell gültige Jahr

Quellen:
    § 39 SGB XI  – Verhinderungspflege
    § 36 SGB XI  – Pflegesachleistungen
    § 37 SGB XI  – Pflegegeld
    § 44a SGB XI – Kurzzeitpflege

Hinweis:
    Bei Gesetzesänderungen nur diese Datei anpassen.
    Alle anderen Module importieren von hier.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Optional


@dataclass(frozen=True)
class PflegeGeldSaetze:
    """Monatliche Pflegegeld-Sätze nach Pflegegrad (§ 37 SGB XI)."""
    pg1: float = 0.0
    pg2: float = 0.0
    pg3: float = 0.0
    pg4: float = 0.0
    pg5: float = 0.0

    def fuer_grad(self, pflegegrad: int) -> float:
        mapping = {1: self.pg1, 2: self.pg2, 3: self.pg3, 4: self.pg4, 5: self.pg5}
        return mapping.get(pflegegrad, 0.0)



@dataclass(frozen=True)
class SachleistungSaetze:
    """Monatliche Pflegesachleistungen nach Pflegegrad (§ 36 SGB XI)."""
    pg1: float = 0.0
    pg2: float = 0.0
    pg3: float = 0.0
    pg4: float = 0.0
    pg5: float = 0.0

    def fuer_grad(self, pflegegrad: int) -> float:
        mapping = {1: self.pg1, 2: self.pg2, 3: self.pg3, 4: self.pg4, 5: self.pg5}
        return mapping.get(pflegegrad, 0.0)


@dataclass(frozen=True)
class TagespflegeSaetze:
    """Monatliche Tagespflege-Beträge nach Pflegegrad (§ 41 SGB XI)."""
    pg1: float = 0.0
    pg2: float = 0.0
    pg3: float = 0.0
    pg4: float = 0.0
    pg5: float = 0.0

    def fuer_grad(self, pflegegrad: int) -> float:
        mapping = {1: self.pg1, 2: self.pg2, 3: self.pg3, 4: self.pg4, 5: self.pg5}
        return mapping.get(pflegegrad, 0.0)

@dataclass(frozen=True)
class PflegeRegeln:
    """
    Vollständiges Regelwerk für ein Kalenderjahr.
    Alle Beträge in Euro, alle Grenzen in Ganzzahlen.
    """
    jahr: int

    # § 39 SGB XI – Verhinderungspflege
    vp_budget_jahresbetrag: float = 3_539.00    # gemeinsamer Topf VP + KZP
    vp_max_tage_tageweise: int = 56             # Kalenderjahr
    vp_stunden_grenze_tageweise: float = 8.0    # ab 8h gilt als "tageweise"

    # § 37 SGB XI – Pflegegeld
    pflegegeld: PflegeGeldSaetze = field(default_factory=PflegeGeldSaetze)

    # § 36 SGB XI – Pflegesachleistungen
    sachleistung: SachleistungSaetze = field(default_factory=SachleistungSaetze)

    # § 41 SGB XI – Tagespflege
    tagespflege: TagespflegeSaetze = field(default_factory=TagespflegeSaetze)

    # § 45b SGB XI – Entlastungsbetrag (alle Pflegegrade)
    entlastungsbetrag_monatlich: float = 131.00

    # § 40 SGB XI – Pflegehilfsmittel (Pauschale)
    pflegehilfsmittel_monatlich: float = 42.00

    # § 40 SGB XI – Wohnumfeldverbessernde Maßnahmen (einmalig je Maßnahme)
    wohnumfeld_je_massnahme: float = 4_180.00

    # Hausnotruf (kein gesetzlicher Festbetrag – marktüblich)
    hausnotruf_monatlich: float = 25.50

    # § 40a SGB XI – DiPA (Digitale Pflegeanwendungen)
    dipa_app_monatlich: float = 40.00          # App-Kosten
    dipa_unterstuetzung_monatlich: float = 30.00  # ergänzende Unterstützung ambulant

    # Stundensatz (kein Gesetz – projektspezifisch, hier als Referenzwert)
    stundensatz_referenz: float = 20.00

    # Gültigkeitszeitraum
    gueltig_ab: Optional[date] = None
    gueltig_bis: Optional[date] = None

    def pflegegeld_monatlich(self, pflegegrad: int) -> float:
        return self.pflegegeld.fuer_grad(pflegegrad)

    def pflegegeld_halbierung_pro_tag(self, pflegegrad: int) -> float:
        """Kürzungsbetrag pro tageweisem VP-Einsatz (§ 37 Abs. 5 SGB XI)."""
        return round(self.pflegegeld_monatlich(pflegegrad) / 30 / 2, 2)

    def sachleistung_monatlich(self, pflegegrad: int) -> float:
        return self.sachleistung.fuer_grad(pflegegrad)

    def tagespflege_monatlich(self, pflegegrad: int) -> float:
        return self.tagespflege.fuer_grad(pflegegrad)

    def tageweise_grenze_erreicht(self, tage: int) -> bool:
        return tage >= self.vp_max_tage_tageweise

    def tageweise_grenze_nahe(self, tage: int, schwelle: float = 0.8) -> bool:
        return tage >= int(self.vp_max_tage_tageweise * schwelle)


# ── Regelwerke nach Jahr ──────────────────────────────────────────────────────

REGELWERKE: Dict[int, PflegeRegeln] = {

    2024: PflegeRegeln(
        jahr=2024,
        vp_budget_jahresbetrag=3_386.00,
        vp_max_tage_tageweise=56,
        vp_stunden_grenze_tageweise=8.0,
        pflegegeld=PflegeGeldSaetze(pg1=0.0, pg2=332.0, pg3=573.0, pg4=765.0, pg5=947.0),
        sachleistung=SachleistungSaetze(pg1=0.0, pg2=761.0, pg3=1_432.0, pg4=1_778.0, pg5=2_200.0),
        tagespflege=TagespflegeSaetze(pg1=0.0, pg2=689.0, pg3=1_298.0, pg4=1_612.0, pg5=1_995.0),
        entlastungsbetrag_monatlich=125.00,
        pflegehilfsmittel_monatlich=42.00,
        wohnumfeld_je_massnahme=4_180.00,
        hausnotruf_monatlich=25.50,
        dipa_app_monatlich=40.00,
        dipa_unterstuetzung_monatlich=30.00,
        stundensatz_referenz=20.00,
        gueltig_ab=date(2024, 1, 1),
        gueltig_bis=date(2024, 12, 31),
    ),

    2025: PflegeRegeln(
        jahr=2025,
        vp_budget_jahresbetrag=3_539.00,
        vp_max_tage_tageweise=56,
        vp_stunden_grenze_tageweise=8.0,
        pflegegeld=PflegeGeldSaetze(pg1=0.0, pg2=347.0, pg3=599.0, pg4=800.0, pg5=990.0),
        sachleistung=SachleistungSaetze(pg1=0.0, pg2=796.0, pg3=1497.0, pg4=1859.0, pg5=2299.0),
        tagespflege=TagespflegeSaetze(pg1=0.0, pg2=721.0, pg3=1357.0, pg4=1685.0, pg5=2085.0),
        entlastungsbetrag_monatlich=131.0,
        pflegehilfsmittel_monatlich=42.00,
        wohnumfeld_je_massnahme=4_180.00,
        hausnotruf_monatlich=25.50,
        dipa_app_monatlich=40.00,
        dipa_unterstuetzung_monatlich=30.00,
        stundensatz_referenz=20.00,
        gueltig_ab=date(2025, 1, 1),
        gueltig_bis=date(2025, 12, 31),
    ),

    2026: PflegeRegeln(
        jahr=2026,
        vp_budget_jahresbetrag=3_539.00,    # Stand: keine Änderung bekannt
        vp_max_tage_tageweise=56,
        vp_stunden_grenze_tageweise=8.0,
        pflegegeld=PflegeGeldSaetze(pg1=0.0, pg2=347.0, pg3=599.0, pg4=800.0, pg5=990.0),
        sachleistung=SachleistungSaetze(pg1=0.0, pg2=796.0, pg3=1497.0, pg4=1859.0, pg5=2299.0),
        tagespflege=TagespflegeSaetze(pg1=0.0, pg2=721.0, pg3=1357.0, pg4=1685.0, pg5=2085.0),
        entlastungsbetrag_monatlich=131.0,
        pflegehilfsmittel_monatlich=42.00,
        wohnumfeld_je_massnahme=4_180.00,
        hausnotruf_monatlich=25.50,
        dipa_app_monatlich=40.00,
        dipa_unterstuetzung_monatlich=30.00,
        stundensatz_referenz=20.00,
        gueltig_ab=date(2026, 1, 1),
        gueltig_bis=date(2026, 12, 31),
    ),
}

# Fallback: aktuelles Jahr
REGELN_AKTUELL = REGELWERKE.get(date.today().year, REGELWERKE[2026])


def get_regelwerk(jahr: int) -> PflegeRegeln:
    """
    Gibt das Regelwerk für ein bestimmtes Jahr zurück.
    Fallback: nächstälteres bekanntes Jahr, dann aktuelles.
    """
    if jahr in REGELWERKE:
        return REGELWERKE[jahr]
    # Nächstälteres Jahr suchen
    bekannte = sorted(REGELWERKE.keys(), reverse=True)
    for j in bekannte:
        if j <= jahr:
            return REGELWERKE[j]
    return REGELN_AKTUELL


def get_regelwerk_fuer_datum(datum: date) -> PflegeRegeln:
    return get_regelwerk(datum.year)


# ── Leistungsübersicht je Pflegegrad ─────────────────────────────────────────

def leistungen_fuer_pflegegrad(pflegegrad: int, jahr: int = 0) -> list:
    """
    Gibt alle Leistungen zurück auf die ein Pflegegrad Anspruch hat.
    Rückgabe: Liste von dicts mit {titel, betrag, einheit, paragraf, info, verfuegbar}
    verfuegbar: True = Anspruch besteht, False = kein Anspruch bei diesem PG
    """
    from datetime import date as _date
    if not jahr:
        jahr = _date.today().year
    r = get_regelwerk(jahr)

    leistungen = []

    # § 37 – Pflegegeld
    pg_betrag = r.pflegegeld_monatlich(pflegegrad)
    leistungen.append({
        "titel": "Pflegegeld",
        "betrag": pg_betrag,
        "einheit": "€/Monat",
        "paragraf": "§ 37 SGB XI",
        "info": "Für selbst organisierte Pflege durch Angehörige oder Bekannte.",
        "verfuegbar": pflegegrad >= 2,
        "kategorie": "geld",
    })

    # § 36 – Pflegesachleistungen
    sl_betrag = r.sachleistung_monatlich(pflegegrad)
    leistungen.append({
        "titel": "Pflegesachleistungen",
        "betrag": sl_betrag,
        "einheit": "€/Monat",
        "paragraf": "§ 36 SGB XI",
        "info": "Für ambulante Pflegedienste (körperbezogene Pflege, Betreuung).",
        "verfuegbar": pflegegrad >= 2,
        "kategorie": "sachleistung",
    })

    # § 39 – Verhinderungspflege
    leistungen.append({
        "titel": "Verhinderungspflege",
        "betrag": r.vp_budget_jahresbetrag,
        "einheit": "€/Jahr",
        "paragraf": "§ 39 SGB XI",
        "info": "Wenn die Pflegeperson verhindert ist (Urlaub, Krankheit). Max. 56 Tage/Jahr.",
        "verfuegbar": pflegegrad >= 2,
        "kategorie": "vp",
    })

    # § 42 – Kurzzeitpflege (aus VP-Budget)
    leistungen.append({
        "titel": "Kurzzeitpflege",
        "betrag": r.vp_budget_jahresbetrag,
        "einheit": "€/Jahr (gemeinsamer Topf VP)",
        "paragraf": "§ 42 SGB XI",
        "info": "Stationäre Kurzzeit-Pflege, z.B. nach Krankenhausaufenthalt. Gemeinsamer Topf mit VP.",
        "verfuegbar": pflegegrad >= 2,
        "kategorie": "vp",
    })

    # § 41 – Tagespflege
    tp_betrag = r.tagespflege_monatlich(pflegegrad)
    leistungen.append({
        "titel": "Tagespflege",
        "betrag": tp_betrag,
        "einheit": "€/Monat",
        "paragraf": "§ 41 SGB XI",
        "info": "Teilstationäre Pflege tagsüber in einer Tageseinrichtung.",
        "verfuegbar": pflegegrad >= 2,
        "kategorie": "sachleistung",
    })

    # § 45b – Entlastungsbetrag
    leistungen.append({
        "titel": "Entlastungsbetrag",
        "betrag": r.entlastungsbetrag_monatlich,
        "einheit": "€/Monat",
        "paragraf": "§ 45b SGB XI",
        "info": "Für Betreuungs- und Entlastungsangebote, Alltagshelfer, Haushaltshilfe.",
        "verfuegbar": pflegegrad >= 1,
        "kategorie": "entlastung",
    })

    # § 40 – Pflegehilfsmittel
    leistungen.append({
        "titel": "Pflegehilfsmittel",
        "betrag": r.pflegehilfsmittel_monatlich,
        "einheit": "€/Monat",
        "paragraf": "§ 40 SGB XI",
        "info": "Pauschale für zum Verbrauch bestimmte Pflegehilfsmittel (Handschuhe, Bettschutz etc.).",
        "verfuegbar": pflegegrad >= 1,
        "kategorie": "hilfsmittel",
    })

    # § 40 – Wohnumfeld
    leistungen.append({
        "titel": "Wohnumfeldverbesserung",
        "betrag": r.wohnumfeld_je_massnahme,
        "einheit": "€/Maßnahme",
        "paragraf": "§ 40 SGB XI",
        "info": "Einmalig je Maßnahme, z.B. Badumbau, Rampen, Treppenlifte.",
        "verfuegbar": pflegegrad >= 1,
        "kategorie": "hilfsmittel",
    })

    # § 40a – DiPA
    leistungen.append({
        "titel": "Digitale Pflegeanwendungen (DiPA)",
        "betrag": r.dipa_app_monatlich,
        "einheit": "€/Monat",
        "paragraf": "§ 40a SGB XI",
        "info": "Für zugelassene Pflege-Apps (z.B. Sturzprävention, Gedächtnistraining).",
        "verfuegbar": pflegegrad >= 1,
        "kategorie": "digital",
    })

    # § 38a – Pflegewohngemeinschaft (ab PG2)
    leistungen.append({
        "titel": "Wohngruppen-Zuschlag",
        "betrag": 214.0,
        "einheit": "€/Monat",
        "paragraf": "§ 38a SGB XI",
        "info": "Für ambulant betreute Wohngruppen mit mind. 3 Pflegebedürftigen.",
        "verfuegbar": pflegegrad >= 2,
        "kategorie": "geld",
    })

    # § 43 – Vollstationäre Pflege (ab PG2)
    pauschalen = {2: 770, 3: 1_262, 4: 1_775, 5: 2_005}
    leistungen.append({
        "titel": "Vollstationäre Pflege",
        "betrag": float(pauschalen.get(pflegegrad, 0)),
        "einheit": "€/Monat",
        "paragraf": "§ 43 SGB XI",
        "info": "Pflegekassenzuschuss bei Unterbringung im Pflegeheim.",
        "verfuegbar": pflegegrad >= 2,
        "kategorie": "stationaer",
    })

    return leistungen
