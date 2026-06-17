"""
Pflegra – Demo-User Reset
Löscht alle Daten des Demo-Users und legt Musterdaten neu an.
Wird aufgerufen beim Logout von demo sowie alle 60 Minuten automatisch.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import date, timedelta

log = logging.getLogger(__name__)

DEMO_USERNAME   = "demo"
RESET_INTERVALL = 60 * 60  # 60 Minuten

# Musterdaten
DEMO_PERSON     = "Max Mustermann"
DEMO_ADRESSE    = "Musterstraße 1\n12345 Musterhausen"
DEMO_VSNR       = "M123456789"
DEMO_KK         = "AOK Musterland"
DEMO_KK_ADR     = "Musterplatz 1\n12345 Musterhausen"
DEMO_GEBURT     = "01.01.1955"
DEMO_PFLEGEGRAD = 3


def demo_user_id(db) -> int | None:
    """Gibt die user_id des Demo-Users zurück oder None."""
    u = db.user_laden_by_username(DEMO_USERNAME)
    return u.id if u else None


def demo_reset(db) -> None:
    """
    Löscht alle Daten des Demo-Users und legt Musterdaten neu an.
    Thread-sicher, fängt alle Fehler ab.
    """
    try:
        uid = demo_user_id(db)
        if uid is None:
            return

        with db._schema.connect() as conn:
            # Alles löschen
            conn.execute("DELETE FROM pflege_eintraege WHERE owner_id=?",  (uid,))
            conn.execute("DELETE FROM versicherte WHERE owner_id=?",       (uid,))
            conn.execute("DELETE FROM personen WHERE owner_id=?",          (uid,))
            conn.execute("DELETE FROM ersatzpflegekraefte WHERE owner_id=?", (uid,))
            conn.execute("DELETE FROM budget_planung WHERE owner_id=?",    (uid,))
            conn.execute("DELETE FROM entlastung_buchungen WHERE owner_id=?", (uid,))
            conn.execute("DELETE FROM pflegegrad_verlauf WHERE owner_id=?", (uid,))

            # Musterperson anlegen
            conn.execute(
                "INSERT OR IGNORE INTO personen (name, owner_id) VALUES (?, ?)",
                (DEMO_PERSON, uid)
            )

            # Demo user_settings (Muster-Absenderdaten)
            conn.execute("""
                INSERT INTO user_settings
                    (user_id, absender_name, absender_adresse, absender_mail,
                     absender_geburtsdatum, stundensatz)
                VALUES (?, 'Max Mustermann', 'Musterstraße 1\n12345 Musterhausen',
                        'demo@example.com', '01.01.1970', 20.0)
                ON CONFLICT(user_id) DO UPDATE SET
                    absender_name='Anna Muster',
                    absender_adresse='Musterweg 5\n12345 Musterhausen',
                    absender_mail='demo@example.com',
                    absender_geburtsdatum='15.06.1975',
                    stundensatz=20.0
            """, (uid,))
            conn.execute("""
                INSERT OR REPLACE INTO versicherte
                    (person_name, adresse, versicherungsnr, krankenkasse,
                     krankenkasse_adresse, pflegegrad, geburtsdatum, mail, notiz, owner_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, '', 'Demo-Versicherter', ?)
            """, (DEMO_PERSON, DEMO_ADRESSE, DEMO_VSNR, DEMO_KK,
                  DEMO_KK_ADR, DEMO_PFLEGEGRAD, DEMO_GEBURT, uid))

            # Muster-Ersatzpflegekraft - erst löschen dann neu
            conn.execute("""
                DELETE FROM ersatzpflegekraefte WHERE owner_id=?
            """, (uid,))
            conn.execute("""
                INSERT INTO ersatzpflegekraefte (person, name, geburtsdatum, adresse, art, notiz, owner_id)
                VALUES (?, 'Maria Muster', '15.03.1980', 'Musterstraße 3, 12345 Musterhausen',
                        'Privatperson', 'Demo-Ersatzpflegekraft', ?)
            """, (DEMO_PERSON, uid))

            # Muster-Einträge: letzten 3 Monate, je 2× pro Woche
            heute = date.today()
            start = heute - timedelta(days=90)
            tag   = start
            count = 0
            while tag <= heute and count < 24:
                wochentag = tag.weekday()
                if wochentag in (1, 4):  # Dienstag und Freitag
                    von = "17:00"
                    bis = "19:00" if count % 3 != 0 else "20:00"
                    std = 2.0    if count % 3 != 0 else 3.0
                    conn.execute("""
                        INSERT INTO pflege_eintraege
                            (datum, monat, jahr, von, bis, stunden, person, wochentag,
                             art, grund, ersatz_name, ersatz_art, ersatz_adresse, notiz, owner_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'stundenweise', 'Erholungsurlaub',
                                'Maria Muster', 'Privatperson', '', 'Demo-Eintrag', ?)
                    """, (tag.isoformat(), tag.month, tag.year, von, bis, std,
                          DEMO_PERSON, ["Mo","Di","Mi","Do","Fr","Sa","So"][wochentag], uid))
                    count += 1
                tag += timedelta(days=1)

        log.info("Demo-User zurückgesetzt (%d Einträge angelegt)", count)

        # Muster-Pflegegrad-Verlauf
        with db._schema.connect() as conn:
            heute = date.today()
            conn.execute("""
                INSERT INTO pflegegrad_verlauf
                    (owner_id, person, datum, pflegegrad, gesamtpunkte, notiz, antworten_json)
                VALUES (?, ?, ?, 3, 58.8, 'Demo-Einschätzung', '{}')
            """, (uid, DEMO_PERSON, heute.isoformat()))
            log.info("Demo-Pflegegrad-Verlauf angelegt")

        # Muster-Tagebucheinträge
        with db._schema.connect() as conn:
            conn.execute("DELETE FROM pflegetagebuch WHERE owner_id=?", (uid,))
            heute = date.today()
            def d(tage): return (heute - timedelta(days=tage)).isoformat()
            demo_eintraege = [
                (uid, DEMO_PERSON, d(0),  "09:00", "allgemein",    "Guter Morgen",         "Max hat heute gut geschlafen und war beim Frühstück guter Stimmung.", 4, ""),
                (uid, DEMO_PERSON, d(1),  "14:30", "koerperpflege","Körperpflege",          "Vollbad durchgeführt. Max hat gut mitgemacht, nur beim Anziehen etwas Unterstützung benötigt.", 3, "körperpflege,bad"),
                (uid, DEMO_PERSON, d(2),  "11:00", "arzt",         "Hausarzt Termin",       "Kontrolltermin beim Hausarzt. Blutdruck 135/85, Medikation bleibt unverändert.", 3, "arzt,blutdruck"),
                (uid, DEMO_PERSON, d(3),  "16:00", "stimmung",     "Unruhige Phase",        "Max war am Nachmittag unruhig und hat mehrfach nach seiner Frau gefragt. Beruhigung durch Musik geholfen.", 2, "unruhe,demenz"),
                (uid, DEMO_PERSON, d(4),  "12:00", "ernaehrung",   "Mittagessen",           "Guter Appetit heute. Suppe und Hauptgericht vollständig gegessen. Trinkmenge ca. 1,5 Liter.", 4, "essen,trinken"),
                (uid, DEMO_PERSON, d(5),  "10:00", "medikamente",  "Medikamente angepasst", "Nach Rücksprache mit Dr. Müller: Blutdruckmittel auf 5mg reduziert. Nächste Kontrolle in 3 Wochen.", 3, "medikamente,arzt"),
                (uid, DEMO_PERSON, d(6),  "15:00", "soziales",     "Besuch der Tochter",    "Lisa war zu Besuch. Max hat sich sehr gefreut, war den ganzen Nachmittag aufgeweckt und gesprächig.", 5, "besuch,familie"),
                (uid, DEMO_PERSON, d(8),  "08:30", "allgemein",    "Schlechte Nacht",       "Max hat schlecht geschlafen, war mehrfach wach. Tagsüber müde aber ruhig.", 2, "schlaf"),
                (uid, DEMO_PERSON, d(10), "13:00", "arzt",         "MD-Termin vorbereiten", "Unterlagen für den MD-Termin zusammengestellt: Pflegetagebuch, Medikamentenliste, Arztberichte.", 3, "md,vorbereitung"),
                (uid, DEMO_PERSON, d(12), "17:00", "koerperpflege","Rasur und Körperpflege","Rasur durchgeführt, Haut gepflegt. Max war entspannt und hat den Prozess gut toleriert.", 4, "körperpflege"),
                (uid, DEMO_PERSON, d(14), "11:30", "ernaehrung",   "Appetitlosigkeit",      "Max hat heute kaum gegessen. Nur etwas Suppe und Joghurt. Auf ausreichend Trinken geachtet.", 2, "essen,appetit"),
                (uid, DEMO_PERSON, d(16), "09:00", "allgemein",    "Spaziergang im Park",   "Kurzer Spaziergang im Stadtpark. Max war gut zu Fuß, ca. 20 Minuten. Wetter war schön.", 5, "bewegung,spaziergang"),
            ]
            for e in demo_eintraege:
                conn.execute("""
                    INSERT INTO pflegetagebuch
                        (owner_id, person, datum, uhrzeit, kategorie, titel, inhalt, stimmung, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, e)
            log.info("Demo-Tagebucheinträge angelegt (%d)", len(demo_eintraege))

        # Muster-Entlastungsbuchungen — Budget grün (nicht überschritten)
        with db._schema.connect() as conn:
            heute = date.today()
            demo_buchungen = []
            # Nur für vergangene Monate bis einschließlich letzten Monat
            for m in range(1, heute.month):
                demo_buchungen += [
                    (uid, DEMO_PERSON, f"{heute.year}-{m:02d}-05", 65.00,
                     "Ambulanter Pflegedienst Muster", "Hauswirtschaftliche Versorgung", f"RE-{heute.year}{m:02d}-001"),
                    (uid, DEMO_PERSON, f"{heute.year}-{m:02d}-20", 55.00,
                     "Betreuungsgruppe Musterhausen", "Tagesbetreuung", f"RE-{heute.year}{m:02d}-002"),
                ]
            conn.executemany("""
                INSERT INTO entlastung_buchungen
                    (owner_id, person, datum, betrag, anbieter, beschreibung, beleg_nr)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, demo_buchungen)
            log.info("Demo-Entlastungsbuchungen angelegt (%d Buchungen)", len(demo_buchungen))

        # Muster-Pflegeberatung
        with db._schema.connect() as conn:
            conn.execute("DELETE FROM pflegeberatung WHERE owner_id=?", (uid,))
            heute = date.today()
            # Letzter Beratungseinsatz vor ~4 Monaten
            letzter = heute - timedelta(days=120)
            conn.execute("""
                INSERT INTO pflegeberatung
                    (owner_id, person, datum, berater, notiz, datei_pfad, datei_name)
                VALUES (?, ?, ?, ?, ?, '', '')
            """, (uid, DEMO_PERSON, letzter.isoformat(), "Pflegedienst", "Pflegeberatung nach § 37.3 SGB XI"))
            log.info("Demo-Pflegeberatung angelegt")

        # Muster-Dokumente
        with db._schema.connect() as conn:
            conn.execute("DELETE FROM dokumente WHERE owner_id=?", (uid,))
            heute = date.today()
            demo_docs = [
                (uid, DEMO_PERSON, "gutachten", "MD-Gutachten Pflegegrad 3",
                 "", "MD_Gutachten_2024.pdf", 0, "Begutachtung durch MDK", f"{heute.year-1}-11-15"),
                (uid, DEMO_PERSON, "pflegekasse", "Bescheid Pflegegrad 3",
                 "", "Bescheid_PG3_AOK.pdf", 0, "Anerkennungsbescheid der AOK", f"{heute.year-1}-12-01"),
                (uid, DEMO_PERSON, "pflegeberatung", f"Beratungsnachweis {letzter.strftime('%B %Y')}",
                 "", f"Beratungsnachweis_{letzter.year}_{letzter.month:02d}.pdf", 0, "", letzter.isoformat()),
            ]
            conn.executemany("""
                INSERT INTO dokumente
                    (owner_id, person, kategorie, titel, datei_pfad, datei_name, datei_groesse, notiz, datum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, demo_docs)
            log.info("Demo-Dokumente angelegt (%d)", len(demo_docs))

        # Muster-Kontakte
        with db._schema.connect() as conn:
            conn.execute("DELETE FROM kontakte WHERE owner_id=?", (uid,))
            heute = date.today()
            demo_kontakte = [
                (uid, DEMO_PERSON, "hausarzt", "Dr. med. Thomas Müller",
                 "Sprechstundenhilfe Petra", "0234 / 56789-0", "praxis@dr-mueller-muster.de",
                 "Musterstraße 12, 12345 Musterhausen", "", "Hausarzt seit 2018"),
                (uid, DEMO_PERSON, "pflegekasse", "AOK Musterland",
                 "Frau Schmidt", "0800 / 1234567", "info@aok-musterland.de",
                 "Musterplatz 1, 12345 Musterhausen", "M123456789", "Kundenservice Mo–Fr 8–18 Uhr"),
                (uid, DEMO_PERSON, "pflegedienst", "Pflegedienst Sonnenschein",
                 "Frau Weber", "0234 / 98765-0", "info@pflegedienst-sonnenschein.de",
                 "Gartenweg 3, 12345 Musterhausen", "", "Einsätze Di und Fr 17–19 Uhr"),
                (uid, DEMO_PERSON, "beratungsstelle", "Pflegestützpunkt Musterhausen",
                 "Herr Klein", "0234 / 11223-0", "beratung@pflegestuetzpunkt-muster.de",
                 "Rathausplatz 5, 12345 Musterhausen", "", "Beratung nach § 37.3 SGB XI"),
                (uid, DEMO_PERSON, "sonstiges", "Apotheke Am Markt",
                 "", "0234 / 44556-0", "",
                 "Marktstraße 1, 12345 Musterhausen", "", "Medikamente und Pflegehilfsmittel"),
            ]
            conn.executemany("""
                INSERT INTO kontakte
                    (owner_id, person, typ, name, ansprechpartner, telefon, email, adresse, kundennummer, notiz)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, demo_kontakte)
            log.info("Demo-Kontakte angelegt (%d)", len(demo_kontakte))

        # Muster-Fristen
        with db._schema.connect() as conn:
            conn.execute("DELETE FROM eigene_fristen WHERE owner_id=?", (uid,))
            heute = date.today()
            demo_fristen = [
                (uid, DEMO_PERSON, "Schwerbehindertenausweis verlängern",
                 (heute + timedelta(days=9)).isoformat(),
                 "behoerde", "Ausweis läuft Ende Juni ab — Verlängerung beim Versorgungsamt beantragen", 0),
                (uid, DEMO_PERSON, "Entlastungsbetrag-Übertrag prüfen",
                 (heute + timedelta(days=13)).isoformat(),
                 "antrag", "Übertrag des Vorjahresguthabens läuft am 30.06. ab", 0),
                (uid, DEMO_PERSON, "Pflegeberatung § 37.3",
                 (heute + timedelta(days=62)).isoformat(),
                 "termin", "Halbjährliche Pflegeberatung fällig — Pflegedienst Sonnenschein kontaktieren", 0),
                (uid, DEMO_PERSON, "Hausarzt Kontrolltermin",
                 (heute + timedelta(days=21)).isoformat(),
                 "arzt", "Blutdruckkontrolle und Medikamenten-Check bei Dr. Müller", 0),
                (uid, DEMO_PERSON, "Vollmacht aktualisieren",
                 (heute + timedelta(days=45)).isoformat(),
                 "dokument", "Vorsorgevollmacht wurde 2019 ausgestellt — Überprüfung empfohlen", 0),
            ]
            conn.executemany("""
                INSERT INTO eigene_fristen
                    (owner_id, person, titel, datum, kategorie, notiz, erledigt)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, demo_fristen)
            log.info("Demo-Fristen angelegt (%d)", len(demo_fristen))

    except Exception as exc:
        log.error("Demo-Reset Fehler: %s", exc, exc_info=True)


def starte_demo_reset_scheduler(db_factory) -> None:
    """
    Startet einen Background-Thread der alle 60 Minuten den Demo-User zurücksetzt.
    db_factory ist ein callable das die DB-Instanz zurückgibt.
    """
    def _loop():
        while True:
            time.sleep(RESET_INTERVALL)
            try:
                db = db_factory()
                demo_reset(db)
            except Exception as exc:
                log.error("Demo-Scheduler Fehler: %s", exc)

    t = threading.Thread(target=_loop, daemon=True, name="demo-reset-scheduler")
    t.start()
    log.info("Demo-Reset-Scheduler gestartet (alle %d Min.)", RESET_INTERVALL // 60)
