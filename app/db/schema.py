"""
db/schema.py — DbSchema: Verbindung + Migration
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("pflegra.db")


class DbSchema:
    """Verbindungs- und Migrations-Logik. Wird von allen Repos genutzt."""

    SCHEMA_VERSION = 22

    def __init__(self, db_path) -> None:
        self.db_path = db_path

    def connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        # WAL für bessere Concurrency (mehrere Leser, ein Schreiber)
        conn.execute("PRAGMA journal_mode=WAL;")
        # Foreign Key Constraints aktivieren
        conn.execute("PRAGMA foreign_keys=ON;")
        # Synchronous NORMAL — guter Kompromiss zwischen Sicherheit und Performance
        conn.execute("PRAGMA synchronous=NORMAL;")
        # Cache: 8 MB (Standard 2 MB)
        conn.execute("PRAGMA cache_size=-8000;")
        # Temp-Tabellen im Speicher
        conn.execute("PRAGMA temp_store=MEMORY;")
        # Busy-Timeout: 5 Sekunden warten bei Lock
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def integrity_check(self) -> bool:
        """Prüft DB-Integrität. Gibt True zurück wenn OK."""
        try:
            with self.connect() as conn:
                result = conn.execute("PRAGMA integrity_check;").fetchone()
                return result[0] == "ok"
        except Exception:
            return False

    def vacuum(self) -> None:
        """Komprimiert die Datenbank (gibt ungenutzten Speicher frei)."""
        try:
            conn = self.connect()
            conn.execute("VACUUM;")
            conn.close()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("VACUUM fehlgeschlagen: %s", exc)

    def wal_checkpoint(self) -> None:
        """WAL-Checkpoint: schreibt ausstehende Änderungen in Hauptdatei."""
        try:
            with self.connect() as conn:
                conn.execute("PRAGMA wal_checkpoint(FULL);")
        except Exception:
            pass

    def migrate(self) -> None:
        with self.connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER NOT NULL
                )
            """)
            row = conn.execute("SELECT version FROM schema_version").fetchone()
            v = row["version"] if row else 0

            if v < 1:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pflege_eintraege (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        datum TEXT NOT NULL, monat INTEGER NOT NULL,
                        jahr INTEGER NOT NULL, von TEXT NOT NULL,
                        bis TEXT NOT NULL, stunden REAL NOT NULL,
                        person TEXT NOT NULL, wochentag TEXT NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_person_jahr ON pflege_eintraege (person, jahr, monat)")
                conn.execute("INSERT INTO schema_version VALUES (1)" if v == 0 else "UPDATE schema_version SET version = 1")

            if v < 2:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS personen (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE, notiz TEXT DEFAULT ''
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_personen_name ON personen (name)")
                conn.execute("INSERT OR IGNORE INTO personen (name) SELECT DISTINCT person FROM pflege_eintraege")
                conn.execute("UPDATE schema_version SET version = 2")

            if v < 3:
                for spalte, default in [
                    ("art", "'stundenweise'"), ("grund", "'Erholungsurlaub'"),
                    ("ersatz_name", "''"), ("ersatz_art", "'Privatperson'"),
                    ("ersatz_adresse", "''"), ("notiz", "''"),
                ]:
                    try:
                        conn.execute(f"ALTER TABLE pflege_eintraege ADD COLUMN {spalte} TEXT NOT NULL DEFAULT {default}")
                    except Exception:
                        pass
                conn.execute("UPDATE schema_version SET version = 3")

            if v < 4:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS versicherte (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        person_name TEXT NOT NULL UNIQUE,
                        adresse TEXT NOT NULL DEFAULT '',
                        versicherungsnr TEXT NOT NULL DEFAULT '',
                        krankenkasse TEXT NOT NULL DEFAULT '',
                        pflegegrad INTEGER NOT NULL DEFAULT 0,
                        notiz TEXT NOT NULL DEFAULT ''
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_versicherte_person ON versicherte (person_name)")
                conn.execute("UPDATE schema_version SET version = 4")

            if v < 5:
                # Neue Felder für Versicherter: geburtsdatum, mail, krankenkasse_adresse
                for col, default in [
                    ("krankenkasse_adresse", "''"),
                    ("geburtsdatum", "''"),
                    ("mail", "''"),
                ]:
                    try:
                        conn.execute(f"ALTER TABLE versicherte ADD COLUMN {col} TEXT NOT NULL DEFAULT {default}")
                    except Exception:
                        pass  # Spalte existiert bereits
                conn.execute("UPDATE schema_version SET version = 5")

            if v < 6:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS budget_planung (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        person      TEXT    NOT NULL,
                        jahr        INTEGER NOT NULL,
                        monat       INTEGER NOT NULL,
                        stunden     REAL    NOT NULL DEFAULT 0.0,
                        notiz       TEXT    NOT NULL DEFAULT '',
                        UNIQUE(person, jahr, monat)
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_planung_person_jahr ON budget_planung (person, jahr)")
                conn.execute("UPDATE schema_version SET version = 6")

            if v < 7:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ersatzpflegekraefte (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        person       TEXT    NOT NULL,
                        name         TEXT    NOT NULL,
                        geburtsdatum TEXT    NOT NULL DEFAULT '',
                        adresse      TEXT    NOT NULL DEFAULT '',
                        art          TEXT    NOT NULL DEFAULT 'Privatperson',
                        notiz        TEXT    NOT NULL DEFAULT '',
                        UNIQUE(person, name)
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ersatz_person ON ersatzpflegekraefte (person)")
                conn.execute("UPDATE schema_version SET version = 7")

            if v < 8:
                # User-Tabelle
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        username     TEXT    NOT NULL UNIQUE,
                        passwort     TEXT    NOT NULL,
                        rolle        TEXT    NOT NULL DEFAULT 'user',
                        aktiv        INTEGER NOT NULL DEFAULT 1,
                        erstellt_am  TEXT    NOT NULL DEFAULT (datetime('now')),
                        notiz        TEXT    NOT NULL DEFAULT ''
                    )
                """)
                # owner_id zu allen relevanten Tabellen hinzufügen
                for tabelle in ["personen", "pflege_eintraege", "versicherte",
                                 "ersatzpflegekraefte", "budget_planung"]:
                    try:
                        conn.execute(f"ALTER TABLE {tabelle} ADD COLUMN owner_id INTEGER NOT NULL DEFAULT 1")
                    except Exception:
                        pass  # Spalte existiert bereits
                conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_personen_owner ON personen (owner_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_eintraege_owner ON pflege_eintraege (owner_id)")
                conn.execute("UPDATE schema_version SET version = 8")

            if v < 9:
                # Fix UNIQUE constraint: (person, name) → (person, name, owner_id)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ersatzpflegekraefte_new (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        person       TEXT    NOT NULL,
                        name         TEXT    NOT NULL,
                        geburtsdatum TEXT    NOT NULL DEFAULT '',
                        adresse      TEXT    NOT NULL DEFAULT '',
                        art          TEXT    NOT NULL DEFAULT 'Privatperson',
                        notiz        TEXT    NOT NULL DEFAULT '',
                        owner_id     INTEGER NOT NULL DEFAULT 1,
                        UNIQUE(person, name, owner_id)
                    )
                """)
                conn.execute("""
                    INSERT OR IGNORE INTO ersatzpflegekraefte_new
                        (id, person, name, geburtsdatum, adresse, art, notiz, owner_id)
                    SELECT id, person, name, geburtsdatum, adresse, art, notiz,
                           COALESCE(owner_id, 1)
                    FROM ersatzpflegekraefte
                """)
                conn.execute("DROP TABLE ersatzpflegekraefte")
                conn.execute("ALTER TABLE ersatzpflegekraefte_new RENAME TO ersatzpflegekraefte")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ersatz_person ON ersatzpflegekraefte (person)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ersatz_owner ON ersatzpflegekraefte (owner_id)")
                conn.execute("UPDATE schema_version SET version = 9")

            if v < 10:
                # Fix personen UNIQUE: name → (name, owner_id)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS personen_new (
                        id       INTEGER PRIMARY KEY AUTOINCREMENT,
                        name     TEXT    NOT NULL,
                        notiz    TEXT    DEFAULT '',
                        owner_id INTEGER NOT NULL DEFAULT 1,
                        UNIQUE(name, owner_id)
                    )
                """)
                conn.execute("""
                    INSERT OR IGNORE INTO personen_new (id, name, notiz, owner_id)
                    SELECT id, name, notiz, COALESCE(owner_id, 1) FROM personen
                """)
                conn.execute("DROP TABLE personen")
                conn.execute("ALTER TABLE personen_new RENAME TO personen")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_personen_name ON personen (name)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_personen_owner ON personen (owner_id)")
                # user_settings Tabelle
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_settings (
                        user_id            INTEGER PRIMARY KEY,
                        absender_name      TEXT NOT NULL DEFAULT '',
                        absender_adresse   TEXT NOT NULL DEFAULT '',
                        absender_mail      TEXT NOT NULL DEFAULT '',
                        absender_geburtsdatum TEXT NOT NULL DEFAULT '',
                        stundensatz        REAL NOT NULL DEFAULT 20.0,
                        standard_person    TEXT NOT NULL DEFAULT '',
                        standard_jahr      INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                """)
                conn.execute("UPDATE schema_version SET version = 10")

            if v < 11:
                # personen UNIQUE bereits in v10 gefixt — nur Version bump
                conn.execute("UPDATE schema_version SET version = 11")

            if v < 12:
                # FK von versicherte → personen entfernen (inkompatibel mit UNIQUE(name, owner_id))
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS versicherte_new (
                        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                        person_name          TEXT    NOT NULL UNIQUE,
                        adresse              TEXT    NOT NULL DEFAULT '',
                        versicherungsnr      TEXT    NOT NULL DEFAULT '',
                        krankenkasse         TEXT    NOT NULL DEFAULT '',
                        krankenkasse_adresse TEXT    NOT NULL DEFAULT '',
                        pflegegrad           INTEGER NOT NULL DEFAULT 0,
                        geburtsdatum         TEXT    NOT NULL DEFAULT '',
                        mail                 TEXT    NOT NULL DEFAULT '',
                        notiz                TEXT    NOT NULL DEFAULT '',
                        owner_id             INTEGER NOT NULL DEFAULT 1
                    )
                """)
                conn.execute("""
                    INSERT OR IGNORE INTO versicherte_new
                        (id, person_name, adresse, versicherungsnr, krankenkasse,
                         krankenkasse_adresse, pflegegrad, geburtsdatum, mail, notiz, owner_id)
                    SELECT id, person_name, adresse, versicherungsnr, krankenkasse,
                           COALESCE(krankenkasse_adresse, ''), COALESCE(pflegegrad, 0),
                           COALESCE(geburtsdatum, ''), COALESCE(mail, ''), notiz,
                           COALESCE(owner_id, 1)
                    FROM versicherte
                """)
                conn.execute("DROP TABLE versicherte")
                conn.execute("ALTER TABLE versicherte_new RENAME TO versicherte")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_versicherte_person ON versicherte (person_name)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_versicherte_owner ON versicherte (owner_id)")
                conn.execute("UPDATE schema_version SET version = 12")

            if v < 13:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS entlastung_buchungen (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id     INTEGER NOT NULL DEFAULT 1,
                        person       TEXT    NOT NULL,
                        datum        TEXT    NOT NULL,
                        betrag       REAL    NOT NULL,
                        anbieter     TEXT    NOT NULL DEFAULT '',
                        beschreibung TEXT    NOT NULL DEFAULT '',
                        beleg_nr     TEXT    NOT NULL DEFAULT '',
                        created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_entlastung_person ON entlastung_buchungen (person, owner_id)")
                conn.execute("UPDATE schema_version SET version = 13")

            if v < 14:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pflegegrad_verlauf (
                        id             INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id       INTEGER NOT NULL DEFAULT 1,
                        person         TEXT    NOT NULL DEFAULT '',
                        datum          TEXT    NOT NULL,
                        pflegegrad     INTEGER NOT NULL,
                        gesamtpunkte   REAL    NOT NULL,
                        notiz          TEXT    NOT NULL DEFAULT '',
                        antworten_json TEXT    NOT NULL DEFAULT '',
                        created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_pg_verlauf_owner ON pflegegrad_verlauf (owner_id, person, datum)")
                conn.execute("UPDATE schema_version SET version = 14")

            if v < 15:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pflegetagebuch (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id     INTEGER NOT NULL DEFAULT 1,
                        person       TEXT    NOT NULL DEFAULT '',
                        datum        TEXT    NOT NULL,
                        uhrzeit      TEXT    NOT NULL DEFAULT '',
                        kategorie    TEXT    NOT NULL DEFAULT 'allgemein',
                        titel        TEXT    NOT NULL DEFAULT '',
                        inhalt       TEXT    NOT NULL DEFAULT '',
                        stimmung     INTEGER,
                        tags         TEXT    NOT NULL DEFAULT '',
                        created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tagebuch_owner ON pflegetagebuch (owner_id, person, datum)")
                conn.execute("UPDATE schema_version SET version = 15")


            if v < 16:
                # Audit-Log Tabelle
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id                INTEGER PRIMARY KEY AUTOINCREMENT,
                        zeitstempel       TEXT    NOT NULL DEFAULT (datetime('now')),
                        actor_user_id     INTEGER NOT NULL,
                        effective_user_id INTEGER NOT NULL,
                        aktion            TEXT    NOT NULL,
                        details           TEXT    NOT NULL DEFAULT '',
                        ip_adresse        TEXT    NOT NULL DEFAULT '',
                        FOREIGN KEY (actor_user_id)     REFERENCES users(id),
                        FOREIGN KEY (effective_user_id) REFERENCES users(id)
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log (actor_user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_effective ON audit_log (effective_user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_aktion ON audit_log (aktion)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_zeit ON audit_log (zeitstempel)")
                conn.execute("UPDATE schema_version SET version = 16")

            if v < 17:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pflegeberatung (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id     INTEGER NOT NULL DEFAULT 1,
                        person       TEXT    NOT NULL DEFAULT '',
                        datum        TEXT    NOT NULL,
                        berater      TEXT    NOT NULL DEFAULT '',
                        notiz        TEXT    NOT NULL DEFAULT '',
                        datei_pfad   TEXT    NOT NULL DEFAULT '',
                        datei_name   TEXT    NOT NULL DEFAULT '',
                        created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_pflegeberatung_owner ON pflegeberatung (owner_id, person, datum)")
                conn.execute("UPDATE schema_version SET version = 17")

            if v < 18:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS dokumente (
                        id           INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id     INTEGER NOT NULL DEFAULT 1,
                        person       TEXT    NOT NULL DEFAULT '',
                        kategorie    TEXT    NOT NULL DEFAULT 'sonstiges',
                        titel        TEXT    NOT NULL DEFAULT '',
                        datei_pfad   TEXT    NOT NULL DEFAULT '',
                        datei_name   TEXT    NOT NULL DEFAULT '',
                        datei_groesse INTEGER NOT NULL DEFAULT 0,
                        notiz        TEXT    NOT NULL DEFAULT '',
                        datum        TEXT    NOT NULL DEFAULT '',
                        created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_dokumente_owner ON dokumente (owner_id, person, kategorie)")
                conn.execute("UPDATE schema_version SET version = 18")

            if v < 19:
                # Erinnerungs-Konfiguration (Admin-global)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS erinnerungen_config (
                        schluessel  TEXT PRIMARY KEY,
                        wert        TEXT NOT NULL DEFAULT ''
                    )
                """)
                # Standard-Vorlaufzeiten eintragen
                defaults = [
                    ("vorlauf_pflegeberatung", "14"),
                    ("vorlauf_entlastungsbetrag", "30"),
                    ("vorlauf_fristen", "14"),
                    ("smtp_host", ""),
                    ("smtp_port", "587"),
                    ("smtp_user", ""),
                    ("smtp_passwort", ""),
                    ("smtp_absender", ""),
                    ("smtp_tls", "1"),
                    ("push_vapid_public", ""),
                    ("push_vapid_private", ""),
                    ("push_aktiv", "0"),
                    ("erinnerung_stunde", "8"),
                ]
                for k, v_default in defaults:
                    conn.execute(
                        "INSERT OR IGNORE INTO erinnerungen_config (schluessel, wert) VALUES (?, ?)",
                        (k, v_default)
                    )
                # Benachrichtigungseinstellungen in user_settings ergänzen
                conn.execute("ALTER TABLE user_settings ADD COLUMN benachrichtigung_email INTEGER NOT NULL DEFAULT 0")
                conn.execute("ALTER TABLE user_settings ADD COLUMN benachrichtigung_push  INTEGER NOT NULL DEFAULT 0")
                # Push-Subscriptions Tabelle
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS push_subscriptions (
                        id        INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id  INTEGER NOT NULL,
                        endpoint  TEXT NOT NULL UNIQUE,
                        p256dh    TEXT NOT NULL DEFAULT \'\',
                        auth      TEXT NOT NULL DEFAULT \'\',
                        created_at TEXT NOT NULL DEFAULT (datetime(\'now\'))
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_push_owner ON push_subscriptions (owner_id)")
                # Erinnerungsverlauf
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS erinnerungen_log (
                        id         INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id   INTEGER NOT NULL,
                        zeitpunkt  TEXT NOT NULL DEFAULT (datetime('now')),
                        kanal      TEXT NOT NULL DEFAULT 'email',
                        person     TEXT NOT NULL DEFAULT '',
                        typ        TEXT NOT NULL DEFAULT '',
                        titel      TEXT NOT NULL DEFAULT '',
                        datum      TEXT NOT NULL DEFAULT '',
                        erfolg     INTEGER NOT NULL DEFAULT 1
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_erinnerungen_log_owner ON erinnerungen_log (owner_id, zeitpunkt)")
                conn.execute("UPDATE schema_version SET version = 19")

            if v < 20:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS kontakte (
                        id               INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id         INTEGER NOT NULL DEFAULT 1,
                        person           TEXT    NOT NULL DEFAULT '',
                        typ              TEXT    NOT NULL DEFAULT 'sonstiges',
                        name             TEXT    NOT NULL DEFAULT '',
                        ansprechpartner  TEXT    NOT NULL DEFAULT '',
                        telefon          TEXT    NOT NULL DEFAULT '',
                        email            TEXT    NOT NULL DEFAULT '',
                        adresse          TEXT    NOT NULL DEFAULT '',
                        kundennummer     TEXT    NOT NULL DEFAULT '',
                        notiz            TEXT    NOT NULL DEFAULT '',
                        created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_kontakte_owner ON kontakte (owner_id, person, typ)")
                conn.execute("UPDATE schema_version SET version = 20")

            if v < 21:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS eigene_fristen (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        owner_id    INTEGER NOT NULL DEFAULT 1,
                        person      TEXT    NOT NULL DEFAULT '',
                        titel       TEXT    NOT NULL DEFAULT '',
                        datum       TEXT    NOT NULL DEFAULT '',
                        kategorie   TEXT    NOT NULL DEFAULT 'sonstiges',
                        notiz       TEXT    NOT NULL DEFAULT '',
                        erledigt    INTEGER NOT NULL DEFAULT 0,
                        created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_eigene_fristen_owner ON eigene_fristen (owner_id, person, datum)")
                conn.execute("UPDATE schema_version SET version = 21")

            if v < 22:
                # Fix: versicherte.person_name war global UNIQUE statt UNIQUE(person_name, owner_id)
                # Das verhinderte, dass zwei Nutzer eine Person mit demselben Namen anlegen konnten.
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS versicherte_v22 (
                        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                        person_name          TEXT    NOT NULL,
                        adresse              TEXT    NOT NULL DEFAULT '',
                        versicherungsnr      TEXT    NOT NULL DEFAULT '',
                        krankenkasse         TEXT    NOT NULL DEFAULT '',
                        krankenkasse_adresse TEXT    NOT NULL DEFAULT '',
                        pflegegrad           INTEGER NOT NULL DEFAULT 0,
                        geburtsdatum         TEXT    NOT NULL DEFAULT '',
                        mail                 TEXT    NOT NULL DEFAULT '',
                        notiz                TEXT    NOT NULL DEFAULT '',
                        owner_id             INTEGER NOT NULL DEFAULT 1,
                        UNIQUE(person_name, owner_id)
                    )
                """)
                conn.execute("""
                    INSERT OR IGNORE INTO versicherte_v22
                        (id, person_name, adresse, versicherungsnr, krankenkasse,
                         krankenkasse_adresse, pflegegrad, geburtsdatum, mail, notiz, owner_id)
                    SELECT id, person_name, adresse, versicherungsnr, krankenkasse,
                           krankenkasse_adresse, pflegegrad, geburtsdatum, mail, notiz,
                           COALESCE(owner_id, 1)
                    FROM versicherte
                """)
                conn.execute("DROP TABLE versicherte")
                conn.execute("ALTER TABLE versicherte_v22 RENAME TO versicherte")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_versicherte_person ON versicherte (person_name)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_versicherte_owner ON versicherte (owner_id)")
                conn.execute("UPDATE schema_version SET version = 22")

    def schema_version(self) -> int:
        try:
            with self.connect() as conn:
                row = conn.execute("SELECT version FROM schema_version").fetchone()
            return row["version"] if row else 0
        except Exception:
            return 0


#  EintragsRepo

# Migration v16 wird in migrate() ergänzt — siehe unten

# v19 wird in migrate() ergänzt — Erinnerungen
