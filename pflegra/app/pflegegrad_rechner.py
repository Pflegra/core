"""
pflegegrad_rechner.py — NBA-Begutachtungsinstrument (BI) nach § 15 SGB XI

Umsetzung des Neuen Begutachtungsassessments (NBA):
  6 Module → gewichtete Punkte → Gesamtpunktzahl → Pflegegrad

Quellen:
  § 15 SGB XI + Begutachtungsrichtlinien MDS (2017)
  Richtlinien zur Feststellung von Pflegebedürftigkeit, GKV-SV
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ── Modul-Definitionen ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Kriterium:
    id: str
    bezeichnung: str
    optionen: List[tuple]   # [(wert, bezeichnung), ...]
    hilfe: str = ""         # Alltagserklärung für Benutzer


@dataclass(frozen=True)
class Modul:
    id: int
    bezeichnung: str
    gewichtung: float
    kriterien: List[Kriterium]
    max_rohpunkte: int


_OPTS_SELBST = [
    (0, "Selbständig"),
    (1, "Überwiegend selbständig"),
    (2, "Überwiegend unselbständig"),
    (3, "Unselbständig"),
]
_OPTS_VORHANDEN = [
    (0, "Vorhanden"),
    (1, "Größtenteils vorhanden"),
    (2, "In geringem Maße vorhanden"),
    (3, "Nicht vorhanden"),
]
_OPTS_HAEUFIG = [
    (0, "Nie oder sehr selten"),
    (1, "Selten (1–3×/Woche)"),
    (2, "Häufig (mehrmals/Woche, nicht täglich)"),
    (3, "Täglich"),
]
_OPTS_ENTFAELLT = [
    (0, "Entfällt/selbständig"),
    (1, "Überwiegend selbständig"),
    (2, "Überwiegend unselbständig"),
    (3, "Unselbständig"),
]


# ── Modul 1: Mobilität ────────────────────────────────────────────────────────
MODUL_1 = Modul(
    id=1, bezeichnung="Mobilität", gewichtung=0.10, max_rohpunkte=10,
    kriterien=[
        Kriterium("1.1", "Positionswechsel im Bett", _OPTS_SELBST,
            "Kann die Person sich im Bett alleine umdrehen, z.B. vom Rücken auf die Seite, "
            "oder sich im Bett aufsetzen — ohne Hilfe einer anderen Person?"),
        Kriterium("1.2", "Halten einer stabilen Sitzposition", _OPTS_SELBST,
            "Kann die Person aufrecht auf einem Stuhl oder dem Bettrand sitzen, "
            "ohne umzukippen oder sich festhalten zu müssen?"),
        Kriterium("1.3", "Umsetzen", _OPTS_SELBST,
            "Kann die Person selbständig vom Bett in den Rollstuhl oder auf einen Stuhl wechseln "
            "— und zurück? Zählt auch mit Hilfsmittel (z.B. Rutschbrett), aber ohne Personenhilfe."),
        Kriterium("1.4", "Fortbewegen innerhalb des Wohnbereichs", _OPTS_SELBST,
            "Kann die Person sich in der eigenen Wohnung von Zimmer zu Zimmer bewegen — "
            "zu Fuß, mit Rollator oder Rollstuhl? Gemeint ist der normale Alltagsweg, "
            "nicht Treppen."),
        Kriterium("1.5", "Treppensteigen", _OPTS_SELBST,
            "Kann die Person mindestens eine Etage Treppen steigen — mit oder ohne Geländer, "
            "mit oder ohne Gehhilfe, aber ohne dass eine andere Person körperlich hilft?"),
    ],
)

# ── Modul 2: Kognitive und kommunikative Fähigkeiten ─────────────────────────
MODUL_2 = Modul(
    id=2, bezeichnung="Kognitive und kommunikative Fähigkeiten", gewichtung=0.0, max_rohpunkte=15,
    kriterien=[
        Kriterium("2.1", "Erkennen von Personen aus dem näheren Umfeld", _OPTS_VORHANDEN,
            "Erkennt die Person Familienmitglieder, enge Freunde oder regelmäßige Pflegepersonen "
            "— weiß sie wer diese Menschen sind, nicht nur dass sie bekannt wirken?"),
        Kriterium("2.2", "Örtliche Orientierung", _OPTS_VORHANDEN,
            "Weiß die Person wo sie sich befindet — kennt sie ihre eigene Wohnung, "
            "weiß sie in welcher Stadt oder welchem Ort sie lebt?"),
        Kriterium("2.3", "Zeitliche Orientierung", _OPTS_VORHANDEN,
            "Weiß die Person ungefähr welcher Tag, welcher Monat oder welches Jahr es ist? "
            "Kleine Abweichungen sind normal — gemeint ist die grundsätzliche zeitliche Einordnung."),
        Kriterium("2.4", "Erinnern an wesentliche Ereignisse oder Beobachtungen", _OPTS_VORHANDEN,
            "Kann die Person sich an wichtige Dinge des Alltags erinnern, z.B. dass heute "
            "ein Arzttermin war, dass jemand zu Besuch kommt, oder was sie heute gegessen hat?"),
        Kriterium("2.5", "Steuern von mehrschrittigen Alltagshandlungen", _OPTS_VORHANDEN,
            "Kann die Person Aufgaben mit mehreren Schritten selbständig ausführen, "
            "z.B. Kaffee kochen (Wasser, Filter, Maschine einschalten) oder sich anziehen "
            "(Reihenfolge der Kleidungsstücke)? Gemeint ist die geistige Steuerung, "
            "nicht die körperliche Fähigkeit."),
        Kriterium("2.6", "Treffen von Entscheidungen im Alltag", _OPTS_VORHANDEN,
            "Kann die Person einfache Alltagsentscheidungen selbst treffen, "
            "z.B. was sie essen möchte, wann sie schlafen gehen will, "
            "welche Kleidung sie anziehen möchte?"),
        Kriterium("2.7", "Verstehen von Sachverhalten und Informationen", _OPTS_VORHANDEN,
            "Versteht die Person einfache Erklärungen und Zusammenhänge des Alltags, "
            "z.B. warum sie ein Medikament nehmen soll, oder was bei einem Arztbesuch "
            "besprochen wurde?"),
        Kriterium("2.8", "Erkennen von Risiken und Gefahren", _OPTS_VORHANDEN,
            "Erkennt die Person alltägliche Gefahren — z.B. dass ein heißer Herd gefährlich ist, "
            "dass man beim Überqueren der Straße auf Autos achten muss, "
            "oder dass offenes Feuer gefährlich ist?"),
        Kriterium("2.9", "Mitteilen von elementaren Bedürfnissen", _OPTS_VORHANDEN,
            "Kann die Person mitteilen wenn sie Hunger, Durst, Schmerzen, Kälte "
            "oder Toilettenbedarf hat — durch Sprache, Gesten oder andere Signale?"),
        Kriterium("2.10", "Verstehen von Aufforderungen", _OPTS_VORHANDEN,
            "Versteht die Person einfache Anweisungen und Bitten im Alltag, "
            "z.B. 'Bitte setz dich', 'Hier ist dein Essen' oder 'Nimm jetzt die Tablette'?"),
        Kriterium("2.11", "Beteiligen an einem Gespräch", _OPTS_VORHANDEN,
            "Kann die Person an einem einfachen Gespräch teilnehmen — zuhören, "
            "antworten und auf das Gesagte eingehen? Gemeint ist ein normales Alltagsgespräch, "
            "kein komplexes Thema."),
    ],
)

# ── Modul 3: Verhaltensweisen und psychische Problemlagen ────────────────────
MODUL_3 = Modul(
    id=3, bezeichnung="Verhaltensweisen und psychische Problemlagen",
    gewichtung=0.15, max_rohpunkte=65,
    kriterien=[
        Kriterium("3.1", "Motorisch geprägte Verhaltensauffälligkeiten", _OPTS_HAEUFIG,
            "Zeigt die Person ruheloses Umherlaufen, zielloses Hantieren, ständiges Aufstehen "
            "und Hinsetzen oder ähnliche unruhige Bewegungen — ohne erkennbaren Grund?"),
        Kriterium("3.2", "Nächtliche Unruhe", _OPTS_HAEUFIG,
            "Schläft die Person nachts schlecht, steht nachts wiederholt auf, "
            "wacht andere auf oder ist nachts so unruhig, dass Betreuung notwendig ist?"),
        Kriterium("3.3", "Selbstschädigendes und autoaggressives Verhalten", _OPTS_HAEUFIG,
            "Verletzt sich die Person absichtlich selbst, z.B. durch Kratzen, Beißen, "
            "Schlagen gegen den eigenen Körper oder andere selbstgefährdende Handlungen?"),
        Kriterium("3.4", "Beschädigen von Gegenständen", _OPTS_HAEUFIG,
            "Beschädigt oder zerstört die Person Gegenstände in ihrer Umgebung — "
            "wirft Dinge, zerreißt Kleidung, schlägt auf Möbel ein?"),
        Kriterium("3.5", "Physisch aggressives Verhalten gegenüber anderen", _OPTS_HAEUFIG,
            "Schlägt, kratzt, beißt oder greift die Person andere Menschen körperlich an — "
            "Pflegepersonen, Familienmitglieder oder andere Bewohner?"),
        Kriterium("3.6", "Verbale Aggression", _OPTS_HAEUFIG,
            "Beschimpft, bedroht oder schreit die Person andere Menschen an — "
            "wiederholt und ohne für Außenstehende nachvollziehbaren Anlass?"),
        Kriterium("3.7", "Andere pflegerelevante vokale Auffälligkeiten", _OPTS_HAEUFIG,
            "Schreit, stöhnt, ruft oder macht die Person wiederholt Geräusche ohne erkennbaren Grund — "
            "z.B. dauerhaftes Rufen nach Personen oder Hilferufe ohne akute Not?"),
        Kriterium("3.8", "Abwehr pflegerischer und anderer unterstützender Maßnahmen", _OPTS_HAEUFIG,
            "Wehrt sich die Person gegen notwendige Pflege — z.B. gegen das Waschen, "
            "Anziehen, Medikamentengabe oder medizinische Behandlungen — "
            "obwohl sie auf diese Hilfe angewiesen ist?"),
        Kriterium("3.9", "Wahnvorstellungen", _OPTS_HAEUFIG,
            "Hat die Person anhaltende falsche Überzeugungen die sich durch Aufklärung nicht "
            "korrigieren lassen — z.B. glaubt sie verfolgt zu werden, bestohlen zu werden, "
            "oder hält sie fremde Personen für Familienangehörige?"),
        Kriterium("3.10", "Ängste", _OPTS_HAEUFIG,
            "Zeigt die Person ausgeprägte, situationsunangemessene Ängste — "
            "z.B. starke Angst beim Waschen, beim Verlassen der Wohnung, "
            "vor bestimmten Personen oder Situationen des Alltags?"),
        Kriterium("3.11", "Antriebslosigkeit bei depressiver Stimmungslage", _OPTS_HAEUFIG,
            "Ist die Person anhaltend niedergeschlagen, teilnahmslos oder antriebslos — "
            "zieht sie sich zurück, verweigert Aktivitäten die ihr früher Freude machten, "
            "oder wirkt sie dauerhaft traurig und hoffnungslos?"),
        Kriterium("3.12", "Sozial inadäquate Verhaltensweisen", _OPTS_HAEUFIG,
            "Verhält sich die Person in sozialen Situationen unangemessen — "
            "z.B. macht sie anzügliche Bemerkungen, entkleidet sich in der Öffentlichkeit, "
            "greift nach fremden Sachen oder hält keine sozialen Grenzen ein?"),
        Kriterium("3.13", "Sonstige pflegerelevante inadäquate Handlungen", _OPTS_HAEUFIG,
            "Gibt es andere pflegerisch relevante Verhaltensweisen die Betreuung erschweren, "
            "z.B. versteckt die Person Essen, sammelt Gegenstände zwanghaft, "
            "oder führt gefährliche Handlungen durch (z.B. Herd einschalten und vergessen)?"),
    ],
)

# ── Modul 4: Selbstversorgung ─────────────────────────────────────────────────
MODUL_4 = Modul(
    id=4, bezeichnung="Selbstversorgung", gewichtung=0.40, max_rohpunkte=42,
    kriterien=[
        Kriterium("4.1", "Waschen des vorderen Oberkörpers", _OPTS_SELBST,
            "Kann die Person Gesicht, Hals, Brust und Bauch selbst waschen — "
            "mit Waschlappen oder unter der Dusche? Gemeint ist nur der vordere Oberkörper, "
            "nicht Rücken oder Beine."),
        Kriterium("4.2", "Körperpflege im Bereich des Kopfes", _OPTS_SELBST,
            "Kann die Person Zähne putzen (oder Zahnprothese reinigen), "
            "Haare kämmen und das Gesicht pflegen — einschließlich Rasieren bei Männern?"),
        Kriterium("4.3", "Waschen des Intimbereichs", _OPTS_SELBST,
            "Kann die Person den Intimbereich selbständig waschen und reinigen — "
            "auch nach dem Toilettengang? Dies ist das sensibelste Kriterium für Würde und Selbständigkeit."),
        Kriterium("4.4", "Duschen und Baden einschließlich Waschen der Haare", _OPTS_SELBST,
            "Kann die Person vollständig duschen oder baden — inklusive Haare waschen — "
            "ohne Hilfe einer anderen Person? Hilfsmittel wie Duschstuhl zählen als selbständig."),
        Kriterium("4.5", "An- und Auskleiden des Oberkörpers", _OPTS_SELBST,
            "Kann die Person Hemd, Pullover, BH oder Jacke selbst an- und ausziehen — "
            "einschließlich Knöpfe, Reißverschlüsse und Ärmeln?"),
        Kriterium("4.6", "An- und Auskleiden des Unterkörpers", _OPTS_SELBST,
            "Kann die Person Hose, Unterwäsche, Strümpfe und Schuhe selbst an- und ausziehen — "
            "auch wenn sie sich dafür setzen oder bücken muss?"),
        Kriterium("4.7", "Mundgerechtes Zubereiten der Nahrung und Eingießen von Getränken", _OPTS_SELBST,
            "Kann die Person ein bereits vorbereitetes Essen auf dem Teller mundgerecht zerteilen "
            "und sich selbst ein Glas einschenken? Nicht gemeint ist das Kochen — "
            "nur die unmittelbare Vorbereitung direkt vor dem Essen."),
        Kriterium("4.8", "Essen", _OPTS_SELBST,
            "Kann die Person selbständig essen — Besteck benutzen, Essen zum Mund führen, "
            "kauen und schlucken? Auch mit Hilfsmitteln (z.B. Spezialbesteck) gilt als selbständig."),
        Kriterium("4.9", "Trinken", _OPTS_SELBST,
            "Kann die Person selbständig trinken — ein Glas oder eine Tasse halten, "
            "zum Mund führen und trinken, ohne zu verschütten oder zu verschlucken?"),
        Kriterium("4.10", "Benutzen einer Toilette oder eines Toilettenstuhls", _OPTS_SELBST,
            "Kann die Person die Toilette selbständig benutzen — hinsetzen, "
            "sich säubern und wieder aufstehen? Auch mit Toilettensitzerhöhung oder "
            "Haltegriffen gilt als selbständig, solange keine Person helfen muss."),
        Kriterium("4.11", "Bewältigen der Folgen einer Harninkontinenz und Umgang mit Dauerkatheter",
            _OPTS_ENTFAELLT,
            "Nur relevant wenn Harninkontinenz oder ein Dauerkatheter vorhanden ist. "
            "Kann die Person Inkontinenzmaterial selbst wechseln bzw. den Katheter selbst versorgen? "
            "Wenn keine Inkontinenz vorliegt: 'Entfällt/selbständig' wählen."),
        Kriterium("4.12", "Bewältigen der Folgen einer Stuhlinkontinenz und Umgang mit Stoma",
            _OPTS_ENTFAELLT,
            "Nur relevant wenn Stuhlinkontinenz oder ein künstlicher Darmausgang (Stoma) vorhanden ist. "
            "Kann die Person die Versorgung selbst übernehmen? "
            "Wenn nicht zutreffend: 'Entfällt/selbständig' wählen."),
        Kriterium("4.13", "Ernährung parenteral oder über Sonde", _OPTS_ENTFAELLT,
            "Nur relevant wenn die Person über eine Magensonde (PEG) oder intravenös ernährt wird. "
            "Kann die Person die Sondenernährung selbst handhaben? "
            "Wenn normale Ernährung möglich: 'Entfällt/selbständig' wählen."),
    ],
)

# ── Modul 5: Umgang mit krankheits-/therapiebedingten Anforderungen ──────────
MODUL_5 = Modul(
    id=5, bezeichnung="Umgang mit krankheits-/therapiebedingten Anforderungen",
    gewichtung=0.20, max_rohpunkte=27,
    kriterien=[
        Kriterium("5.1", "Medikation", _OPTS_SELBST,
            "Kann die Person ihre Medikamente selbst einnehmen — die richtigen Tabletten "
            "zur richtigen Zeit in der richtigen Dosierung? Auch mit Hilfe eines Wochendosettes "
            "gilt als selbständig, solange keine Person täglich kontrolliert."),
        Kriterium("5.2", "Injektionen (subcutan oder intramuskulär)", _OPTS_ENTFAELLT,
            "Nur relevant wenn regelmäßige Injektionen notwendig sind (z.B. Insulin). "
            "Kann die Person diese Injektionen selbst durchführen? "
            "Wenn keine Injektionen erforderlich: 'Entfällt/selbständig' wählen."),
        Kriterium("5.3", "Versorgung intravenöser Zugänge", _OPTS_ENTFAELLT,
            "Nur relevant wenn ein dauerhafter venöser Zugang (Port, PICC) vorhanden ist. "
            "Kann die Person diesen selbst pflegen? "
            "Wenn nicht zutreffend: 'Entfällt/selbständig' wählen."),
        Kriterium("5.4", "Absaugen und Sauerstoffgabe", _OPTS_ENTFAELLT,
            "Nur relevant wenn regelmäßiges Absaugen von Sekreten oder Sauerstoffgabe notwendig ist. "
            "Kann die Person dies selbst handhaben? "
            "Wenn nicht zutreffend: 'Entfällt/selbständig' wählen."),
        Kriterium("5.5", "Einreibungen sowie Kälte- und Wärmeanwendungen", _OPTS_ENTFAELLT,
            "Nur relevant wenn regelmäßige Einreibungen (z.B. Salben, therapeutische Kälte/Wärme) "
            "verordnet sind. Kann die Person diese selbst durchführen? "
            "Wenn nicht zutreffend: 'Entfällt/selbständig' wählen."),
        Kriterium("5.6", "Messung und Deutung von Körperzuständen", _OPTS_SELBST,
            "Kann die Person selbst Blutdruck, Blutzucker, Körpertemperatur oder Gewicht messen "
            "und die Ergebnisse richtig einordnen — also erkennen ob ein Wert auffällig ist?"),
        Kriterium("5.7", "Körpernahe Hilfsmittel", _OPTS_SELBST,
            "Kann die Person ihre Hilfsmittel selbst anlegen und ablegen — "
            "z.B. Kompressionsstrümpfe, Prothesen, Orthesen, Hörgerät oder Brille?"),
        Kriterium("5.8", "Verbandswechsel und Wundversorgung", _OPTS_ENTFAELLT,
            "Nur relevant wenn regelmäßige Verbandswechsel oder Wundversorgung notwendig sind. "
            "Kann die Person dies selbst durchführen? "
            "Wenn keine Wunden vorhanden: 'Entfällt/selbständig' wählen."),
        Kriterium("5.9", "Einhalten einer Diät oder besonderer Ernährungsform", _OPTS_ENTFAELLT,
            "Nur relevant wenn eine ärztlich verordnete Diät oder besondere Ernährungsform "
            "eingehalten werden muss (z.B. Diabetes-Diät, Schluckstörung). "
            "Hält die Person diese selbständig ein? "
            "Wenn keine Diät erforderlich: 'Entfällt/selbständig' wählen."),
    ],
)

# ── Modul 6: Gestaltung des Alltagslebens und sozialer Kontakte ───────────────
MODUL_6 = Modul(
    id=6, bezeichnung="Gestaltung des Alltagslebens und sozialer Kontakte",
    gewichtung=0.15, max_rohpunkte=18,
    kriterien=[
        Kriterium("6.1", "Gestaltung des Tagesablaufs und Anpassung an Veränderungen", _OPTS_SELBST,
            "Kann die Person ihren Tag selbst strukturieren — wann sie aufsteht, isst, "
            "schläft und Aktivitäten nachgeht? Und kann sie sich anpassen wenn sich etwas "
            "unerwartet ändert (z.B. Besuch kommt früher)?"),
        Kriterium("6.2", "Ruhen und Schlafen", _OPTS_SELBST,
            "Kann die Person selbst entscheiden wann sie ruht oder schläft, "
            "und dies auch umsetzen — also ins Bett gehen, sich hinlegen und aufstehen "
            "wenn sie ausgeruht ist?"),
        Kriterium("6.3", "Sich Beschäftigen", _OPTS_SELBST,
            "Kann die Person selbständig einer Beschäftigung nachgehen — "
            "z.B. lesen, fernsehen, Handarbeiten, Spiele, Gartenarbeit oder Hobbys? "
            "Gemeint ist ob sie die Initiative ergreift und die Tätigkeit ausführt."),
        Kriterium("6.4", "Vornehmen von in die Zukunft gerichteten Planungen", _OPTS_SELBST,
            "Kann die Person einfache Dinge für die Zukunft planen und vorbereiten — "
            "z.B. einen Arzttermin vereinbaren, Einkäufe planen oder einen Besuch organisieren?"),
        Kriterium("6.5", "Interaktion mit Personen im direkten Kontakt", _OPTS_SELBST,
            "Kann die Person mit Menschen in ihrer unmittelbaren Umgebung angemessen umgehen — "
            "ein Gespräch führen, gemeinsam essen, jemanden begrüßen oder verabschieden?"),
        Kriterium("6.6", "Kontaktpflege zu Personen außerhalb des direkten Umfelds", _OPTS_SELBST,
            "Kann die Person selbständig Kontakt zu Freunden, Bekannten oder entfernteren "
            "Familienmitgliedern halten — z.B. telefonieren, Briefe schreiben oder Besuche planen?"),
    ],
)

ALLE_MODULE = [MODUL_1, MODUL_2, MODUL_3, MODUL_4, MODUL_5, MODUL_6]


# ── Bewertungslogik ───────────────────────────────────────────────────────────

@dataclass
class ModulErgebnis:
    modul_id: int
    bezeichnung: str
    rohpunkte: int
    gewichtete_punkte: float
    schweregrad: str


@dataclass
class RechnerErgebnis:
    gesamtpunkte: float
    pflegegrad: int
    pflegegrad_bezeichnung: str
    modul_ergebnisse: List[ModulErgebnis]
    begruendung: str
    hinweise: List[str]
    haupttreiber: List[dict] = field(default_factory=list)   # [{modul_id, bezeichnung, punkte, icon}]
    dokumentations_tipps: List[str] = field(default_factory=list)


_SCHWEREGRAD_GRENZEN = {
    1: [(0,0,"Keine Beeinträchtigungen"),(1,2,"Geringe Beeinträchtigungen"),
        (3,4,"Erhebliche Beeinträchtigungen"),(5,999,"Schwere/schwerste Beeinträchtigungen")],
    2: [(0,0,"Keine Beeinträchtigungen"),(1,4,"Geringe Beeinträchtigungen"),
        (5,10,"Erhebliche Beeinträchtigungen"),(11,999,"Schwere/schwerste Beeinträchtigungen")],
    3: [(0,2,"Keine/geringe Beeinträchtigungen"),(3,11,"Erhebliche Beeinträchtigungen"),
        (12,20,"Schwere Beeinträchtigungen"),(21,999,"Schwerste Beeinträchtigungen")],
    4: [(0,2,"Keine/geringe Beeinträchtigungen"),(3,7,"Erhebliche Beeinträchtigungen"),
        (8,17,"Schwere Beeinträchtigungen"),(18,999,"Schwerste Beeinträchtigungen")],
    5: [(0,0,"Keine Beeinträchtigungen"),(1,3,"Geringe Beeinträchtigungen"),
        (4,8,"Erhebliche Beeinträchtigungen"),(9,999,"Schwere/schwerste Beeinträchtigungen")],
    6: [(0,0,"Keine Beeinträchtigungen"),(1,3,"Geringe Beeinträchtigungen"),
        (4,9,"Erhebliche Beeinträchtigungen"),(10,999,"Schwere/schwerste Beeinträchtigungen")],
}

_GEWICHTUNGSTABELLE = {
    1: [(0,0,0.0),(1,2,2.5),(3,4,5.0),(5,999,10.0)],
    2: [(0,0,0.0),(1,4,3.75),(5,10,7.5),(11,999,15.0)],
    3: [(0,2,0.0),(3,11,3.75),(12,20,7.5),(21,999,15.0)],
    4: [(0,2,0.0),(3,7,10.0),(8,17,20.0),(18,999,40.0)],
    5: [(0,0,0.0),(1,3,5.0),(4,8,10.0),(9,999,20.0)],
    6: [(0,0,0.0),(1,3,3.75),(4,9,7.5),(10,999,15.0)],
}

_PFLEGEGRAD_GRENZEN = [
    (0.0,12.4,0,"Kein Pflegebedarf"),
    (12.5,26.9,1,"Pflegegrad 1 — geringe Beeinträchtigungen"),
    (27.0,47.4,2,"Pflegegrad 2 — erhebliche Beeinträchtigungen"),
    (47.5,69.9,3,"Pflegegrad 3 — schwere Beeinträchtigungen"),
    (70.0,89.9,4,"Pflegegrad 4 — schwerste Beeinträchtigungen"),
    (90.0,100.0,5,"Pflegegrad 5 — schwerste Beeinträchtigungen mit Sonderregelung"),
]


def _lookup_gewichtet(modul_id: int, rohpunkte: int) -> float:
    for (lo,hi,punkte) in _GEWICHTUNGSTABELLE[modul_id]:
        if lo <= rohpunkte <= hi:
            return punkte
    return 0.0


def _lookup_schweregrad(modul_id: int, rohpunkte: int) -> str:
    for (lo,hi,label) in _SCHWEREGRAD_GRENZEN[modul_id]:
        if lo <= rohpunkte <= hi:
            return label
    return "Unbekannt"


def berechne_pflegegrad(antworten: dict) -> RechnerErgebnis:
    modul_ergebnisse = []
    rohpunkte_pro_modul = {}
    for modul in ALLE_MODULE:
        roh = sum(antworten.get(k.id, 0) for k in modul.kriterien)
        rohpunkte_pro_modul[modul.id] = roh

    gew_m2 = _lookup_gewichtet(2, rohpunkte_pro_modul[2])
    gew_m3 = _lookup_gewichtet(3, rohpunkte_pro_modul[3])
    gew_m2_m3 = max(gew_m2, gew_m3)

    for modul in ALLE_MODULE:
        roh = rohpunkte_pro_modul[modul.id]
        gew = gew_m2_m3 if modul.id in (2,3) else _lookup_gewichtet(modul.id, roh)
        sg = _lookup_schweregrad(modul.id, roh)
        modul_ergebnisse.append(ModulErgebnis(
            modul_id=modul.id, bezeichnung=modul.bezeichnung,
            rohpunkte=roh, gewichtete_punkte=gew, schweregrad=sg,
        ))

    gesamtpunkte = (
        _lookup_gewichtet(1, rohpunkte_pro_modul[1]) +
        gew_m2_m3 +
        _lookup_gewichtet(4, rohpunkte_pro_modul[4]) +
        _lookup_gewichtet(5, rohpunkte_pro_modul[5]) +
        _lookup_gewichtet(6, rohpunkte_pro_modul[6])
    )

    pflegegrad, pg_bez = 0, "Kein Pflegebedarf"
    for (lo,hi,pg,bez) in _PFLEGEGRAD_GRENZEN:
        if lo <= gesamtpunkte <= hi:
            pflegegrad, pg_bez = pg, bez
            break

    begruendung = _erstelle_begruendung(gesamtpunkte, pflegegrad, modul_ergebnisse, rohpunkte_pro_modul)
    hinweise = _erstelle_hinweise(pflegegrad, modul_ergebnisse, antworten)
    haupttreiber = _erstelle_haupttreiber(modul_ergebnisse)
    dokumentations_tipps = _erstelle_dokumentations_tipps(pflegegrad, modul_ergebnisse)

    return RechnerErgebnis(
        gesamtpunkte=round(gesamtpunkte,1),
        pflegegrad=pflegegrad,
        pflegegrad_bezeichnung=pg_bez,
        modul_ergebnisse=modul_ergebnisse,
        begruendung=begruendung,
        hinweise=hinweise,
        haupttreiber=haupttreiber,
        dokumentations_tipps=dokumentations_tipps,
    )


def _erstelle_haupttreiber(module: List[ModulErgebnis]) -> List[dict]:
    """Top-3 Module mit tatsächlichem Punktbeitrag, mit Icon."""
    _ICONS = {1: "🦵", 2: "🧠", 3: "💭", 4: "🤲", 5: "💊", 6: "👥"}
    relevant = [m for m in module if m.gewichtete_punkte > 0]
    # Deduplizieren: M2 und M3 zeigen beide den kombinierten Wert → nur den höheren Roh nehmen
    seen_m2m3 = False
    dedup = []
    for m in sorted(relevant, key=lambda x: x.gewichtete_punkte, reverse=True):
        if m.modul_id in (2, 3):
            if seen_m2m3:
                continue
            seen_m2m3 = True
        dedup.append(m)
    return [
        {
            "modul_id": m.modul_id,
            "bezeichnung": m.bezeichnung,
            "punkte": m.gewichtete_punkte,
            "schweregrad": m.schweregrad,
            "icon": _ICONS.get(m.modul_id, "•"),
        }
        for m in dedup[:3]
    ]


# Dokumentations-Tipps je Modul — welche Beobachtungen im Pflegetagebuch helfen
_DOKU_TIPPS = {
    1: "Dokumentieren Sie wie weit und wie sicher die Person geht, ob Hilfsmittel nötig sind "
       "und ob Stürze vorkommen.",
    2: "Notieren Sie Situationen in denen die Person sich örtlich oder zeitlich nicht orientiert, "
       "oder bekannte Personen nicht erkennt.",
    3: "Führen Sie ein kurzes Protokoll über Verhaltensauffälligkeiten: Uhrzeit, Auslöser, Dauer.",
    4: "Dokumentieren Sie konkret welche Pflegehandlungen täglich anfallen — "
       "z.B. vollständige Körperpflege, Ankleiden, Toilettengänge.",
    5: "Notieren Sie alle Medikamente, Verbandswechsel und medizinischen Maßnahmen mit Zeitaufwand.",
    6: "Halten Sie fest ob die Person Tagesstruktur braucht, soziale Kontakte abbricht "
       "oder Alltagsaktivitäten verweigert.",
}


def _erstelle_dokumentations_tipps(pflegegrad: int, module: List[ModulErgebnis]) -> List[str]:
    if pflegegrad == 0:
        return []
    tipps = []
    # Alle Module mit erheblicher oder höherer Beeinträchtigung
    relevante = [
        m for m in module
        if m.rohpunkte > 0 and "Keine" not in m.schweregrad and m.modul_id not in (2,)
        # M2 wird durch M3 abgedeckt wenn M3 dominiert
    ]
    # Deduplizieren M2/M3
    seen_m2m3 = False
    for m in sorted(relevante, key=lambda x: x.gewichtete_punkte, reverse=True):
        if m.modul_id in (2, 3):
            if seen_m2m3:
                continue
            seen_m2m3 = True
        if m.modul_id in _DOKU_TIPPS:
            tipps.append(f"{['🦵','🧠','💭','🤲','💊','👥'][m.modul_id-1]} Modul {m.modul_id}: {_DOKU_TIPPS[m.modul_id]}")
        if len(tipps) >= 3:
            break

    if pflegegrad >= 2 and tipps:
        tipps.append("📅 Ein Pflegetagebuch über 2–4 Wochen stärkt Ihren Antrag erheblich.")

    return tipps


def _erstelle_begruendung(gesamtpunkte, pflegegrad, module, rohpunkte):
    teile = []
    if pflegegrad == 0:
        teile.append(
            f"Mit {gesamtpunkte:.1f} Gesamtpunkten wird die Mindestgrenze von 12,5 Punkten "
            f"für Pflegegrad 1 nicht erreicht. Es besteht kein Anspruch auf Pflegeleistungen nach SGB XI."
        )
    else:
        teile.append(
            f"Die Begutachtung nach dem NBA ergibt {gesamtpunkte:.1f} gewichtete Gesamtpunkte. "
            f"Dies entspricht {_pflegegrad_bezeichnung_kurz(pflegegrad)}."
        )
    dominate = sorted(module, key=lambda m: m.gewichtete_punkte, reverse=True)[:3]
    if dominate[0].gewichtete_punkte > 0:
        teile.append(
            f"Besonders relevant: Modul {dominate[0].modul_id} ({dominate[0].bezeichnung}) "
            f"mit {dominate[0].gewichtete_punkte:.1f} gewichteten Punkten "
            f"({dominate[0].schweregrad})."
        )
    m4 = next(m for m in module if m.modul_id == 4)
    if m4.rohpunkte > 0:
        teile.append(
            f"Modul 4 (Selbstversorgung) ist mit 40 % das stärkste Gewichtungsmodul "
            f"und erreicht {m4.gewichtete_punkte:.1f} von maximal 40,0 Punkten."
        )
    return " ".join(teile)


def _pflegegrad_bezeichnung_kurz(pg):
    return {
        1: "Pflegegrad 1 (geringe Beeinträchtigungen, 12,5–26,9 Punkte)",
        2: "Pflegegrad 2 (erhebliche Beeinträchtigungen, 27,0–47,4 Punkte)",
        3: "Pflegegrad 3 (schwere Beeinträchtigungen, 47,5–69,9 Punkte)",
        4: "Pflegegrad 4 (schwerste Beeinträchtigungen, 70,0–89,9 Punkte)",
        5: "Pflegegrad 5 (schwerste Beeinträchtigungen mit besonderem Bedarf, 90,0–100,0 Punkte)",
    }.get(pg, "unbekannter Pflegegrad")


def _erstelle_hinweise(pflegegrad, module, antworten):
    hinweise = []
    hinweise.append(
        "⚠️ Dieses Ergebnis ist eine Orientierungshilfe und ersetzt keine "
        "offizielle Begutachtung durch den MDK/Medicproof."
    )
    if pflegegrad >= 2:
        hinweise.append(
            "📋 Tipp: Beantragen Sie Pflegeleistungen bei Ihrer Pflegekasse. "
            "Der MDK-Gutachter bewertet alle Module vor Ort."
        )
    if pflegegrad >= 3:
        hinweise.append(
            "💡 Bei Pflegegrad 3–5 besteht Anspruch auf erhöhte Verhinderungs- "
            "und Kurzzeitpflege-Leistungen nach § 39 SGB XI."
        )
    m3 = next(m for m in module if m.modul_id == 3)
    if m3.rohpunkte >= 3:
        hinweise.append(
            "🧠 Verhaltensauffälligkeiten/psychische Problemlagen festgestellt: "
            "Beratung durch Pflegestützpunkt empfohlen."
        )
    return hinweise
