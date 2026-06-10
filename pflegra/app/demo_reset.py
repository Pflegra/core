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
            demo_eintraege = [
                (uid, DEMO_PERSON, heute.isoformat(), "09:00", "allgemein",
                 "Guter Morgen", "Max hat heute gut geschlafen und war beim Frühstück guter Stimmung.", 4, ""),
                (uid, DEMO_PERSON, (heute.replace(day=heute.day-1) if heute.day > 1 else heute).isoformat(),
                 "14:30", "koerperpflege",
                 "Körperpflege", "Vollbad durchgeführt. Max hat gut mitgemacht, nur beim Anziehen etwas Unterstützung benötigt.", 3, "körperpflege,bad"),
                (uid, DEMO_PERSON, (heute.replace(day=heute.day-2) if heute.day > 2 else heute).isoformat(),
                 "11:00", "arzt",
                 "Hausarzt Termin", "Kontrolltermin beim Hausarzt. Blutdruck 135/85, Medikation bleibt unverändert.", 3, "arzt,blutdruck"),
                (uid, DEMO_PERSON, (heute.replace(day=heute.day-3) if heute.day > 3 else heute).isoformat(),
                 "16:00", "stimmung",
                 "Unruhige Phase", "Max war am Nachmittag unruhig und hat mehrfach nach seiner Frau gefragt. Beruhigung durch Musik geholfen.", 2, "unruhe,demenz"),
                (uid, DEMO_PERSON, (heute.replace(day=heute.day-4) if heute.day > 4 else heute).isoformat(),
                 "12:00", "ernaehrung",
                 "Mittagessen", "Guter Appetit heute. Suppe und Hauptgericht vollständig gegessen. Trinkmenge ca. 1,5 Liter.", 4, "essen,trinken"),
            ]
            for e in demo_eintraege:
                conn.execute("""
                    INSERT INTO pflegetagebuch
                        (owner_id, person, datum, uhrzeit, kategorie, titel, inhalt, stimmung, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, e)
            log.info("Demo-Tagebucheinträge angelegt (%d)", len(demo_eintraege))

        # Muster-Entlastungsbuchungen
        with db._schema.connect() as conn:
            heute = date.today()
            demo_buchungen = []
            for m in range(1, heute.month + 1):
                # 1-3 Buchungen pro Monat, zusammen max 131€
                demo_buchungen += [
                    (uid, DEMO_PERSON, f"{heute.year}-{m:02d}-05", 45.00,
                     "Ambulanter Pflegedienst Muster", "Hauswirtschaftliche Versorgung", f"RE-{heute.year}{m:02d}-001"),
                    (uid, DEMO_PERSON, f"{heute.year}-{m:02d}-18", 50.00,
                     "Betreuungsgruppe Musterhausen", "Tagesbetreuung", f"RE-{heute.year}{m:02d}-002"),
                ]
                if m % 2 == 0:
                    demo_buchungen.append(
                        (uid, DEMO_PERSON, f"{heute.year}-{m:02d}-25", 36.00,
                         "Ambulanter Pflegedienst Muster", "Betreuungsleistung", f"RE-{heute.year}{m:02d}-003")
                    )
            conn.executemany("""
                INSERT INTO entlastung_buchungen
                    (owner_id, person, datum, betrag, anbieter, beschreibung, beleg_nr)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, demo_buchungen)
            log.info("Demo-Entlastungsbuchungen angelegt (%d Buchungen)", len(demo_buchungen))
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
