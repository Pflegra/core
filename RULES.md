# Pflegra – Fachregeln & Gesetzliche Grundlagen

> Stand: v47 · Letzte Aktualisierung: Mai 2026
> Quelle der Wahrheit im Code: `app/pflege_rules.py`

---

## Überblick

Pflegra bildet die wichtigsten Pflegeleistungen nach SGB XI ab:

| Modul | Gesetzliche Grundlage |
|---|---|
| Verhinderungspflege | § 39 SGB XI |
| Kurzzeitpflege | § 42 SGB XI |
| Pflegegeld | § 37 SGB XI |
| Pflegesachleistungen | § 36 SGB XI |
| Tagespflege | § 41 SGB XI |
| Entlastungsbetrag | § 45b SGB XI |
| Pflegehilfsmittel | § 40 SGB XI |
| Wohnumfeldverbesserung | § 40 SGB XI |
| Digitale Pflegeanwendungen | § 40a SGB XI |
| Pflegegrad-Ermittlung | § 15 SGB XI (NBA) |

---

## § 39 / § 42 SGB XI — VP + KZP gemeinsamer Topf

| Jahr | Betrag | Änderung |
|---|---|---|
| 2024 | 3.386,00 € | — |
| 2025 | 3.539,00 € | Reform Pflegekompetenzgesetz ab 01.07.2025 |
| 2026 | 3.539,00 € | unverändert (Stand Mai 2026) |

Ab 01.07.2025: VP und KZP teilen sich einen gemeinsamen Jahresbetrag.

**56-Tage-Grenze (tageweise VP)**
- Tageweise = Einsatz ≥ 8 Stunden → zählt gegen 56-Tage-Grenze
- Stundenweise = Einsatz < 8 Stunden → keine Tages-Begrenzung

---

## § 37 SGB XI — Pflegegeld

| Pflegegrad | 2024 | 2025/2026 |
|---|---|---|
| PG 2 | 332 €/Mo | 347 €/Mo |
| PG 3 | 573 €/Mo | 599 €/Mo |
| PG 4 | 765 €/Mo | 800 €/Mo |
| PG 5 | 947 €/Mo | 990 €/Mo |

Bei tageweiser VP: Pflegegeld wird für diese Tage halbiert (§ 37 Abs. 5).

---

## § 36 SGB XI — Pflegesachleistungen

| Pflegegrad | 2024 | 2025/2026 |
|---|---|---|
| PG 2 | 761 €/Mo | 796 €/Mo |
| PG 3 | 1.432 €/Mo | 1.497 €/Mo |
| PG 4 | 1.778 €/Mo | 1.859 €/Mo |
| PG 5 | 2.200 €/Mo | 2.299 €/Mo |

---

## § 41 SGB XI — Tagespflege

| Pflegegrad | 2025/2026 |
|---|---|
| PG 2 | 721 €/Mo |
| PG 3 | 1.357 €/Mo |
| PG 4 | 1.685 €/Mo |
| PG 5 | 2.085 €/Mo |

Tagespflege kann zusätzlich zu Pflegegeld und Sachleistung in Anspruch genommen werden (§ 41 Abs. 4).

---

## § 45b SGB XI — Entlastungsbetrag

| Jahr | Betrag |
|---|---|
| 2024 | 125 €/Mo |
| 2025/2026 | 131 €/Mo |

- Ab PG 1
- Nicht verbrauchte Beträge übertragbar ins Folgejahr (bis 30. Juni)
- Vorjahrsguthaben wird in Pflegra automatisch berechnet

---

## § 40 SGB XI — Pflegehilfsmittel + Wohnumfeld

| Leistung | Betrag |
|---|---|
| Pflegehilfsmittel (Verbrauch) | 42 €/Mo |
| Wohnumfeldverbesserung | 4.180 € je Maßnahme |

---

## § 40a SGB XI — Digitale Pflegeanwendungen (DiPA)

| Leistung | Betrag |
|---|---|
| App-Kosten | 40 €/Mo |
| Ergänzende Unterstützung ambulant | 30 €/Mo |

---

## § 15 SGB XI — Pflegegrad-Ermittlung (NBA)

Das Neue Begutachtungsassessment (NBA) bewertet 6 Module:

| Modul | Gewichtung |
|---|---|
| 1 Mobilität | 10 % |
| 2+3 Kognition/Verhalten (kombiniert, höherer Wert) | 15 % |
| 4 Selbstversorgung | 40 % |
| 5 Therapieanforderungen | 20 % |
| 6 Alltagsgestaltung | 15 % |

**Pflegegrad-Grenzen (Gesamtpunkte):**

| Punkte | Pflegegrad |
|---|---|
| < 12,5 | Kein Pflegebedarf |
| 12,5 – 26,9 | PG 1 |
| 27,0 – 47,4 | PG 2 |
| 47,5 – 69,9 | PG 3 |
| 70,0 – 89,9 | PG 4 |
| ≥ 90,0 | PG 5 |

---

## Stundensatz

Kein gesetzlich vorgeschriebener Stundensatz — frei vereinbar.
Referenzwert im System: **20,00 €/Stunde** (einstellbar in Benutzereinstellungen).

---

## Code-Referenz

Alle Beträge und Regeln leben in `app/pflege_rules.py`:

```python
from pflege_rules import get_regelwerk, leistungen_fuer_pflegegrad

r = get_regelwerk(2026)
print(r.pflegegeld_monatlich(3))   # 599.0
print(r.entlastungsbetrag_monatlich)  # 131.0

leistungen = leistungen_fuer_pflegegrad(3, 2026)
```

Bei Gesetzesänderungen nur `pflege_rules.py` anpassen — alle anderen Module importieren von dort.
