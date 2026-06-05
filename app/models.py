"""
models.py — Pflegra Datenbankfassade (v46z1)

Alle Klassen und Repos leben jetzt in db/:
  db/schema.py       — DbSchema (Verbindung + Migration)
  db/eintraege.py    — PflegeEintrag, EintragsRepo, Konstanten
  db/personen.py     — PersonenRepo
  db/versicherte.py  — Versicherter, VersicherterRepo
  db/users.py        — User, UserRepo
  db/ersatzpflege.py — Ersatzpflegekraft, ErsatzRepo
  db/settings.py     — UserSettings, UserSettingsRepo, PlanungsRepo
  db/entlastung.py   — EntlastungBuchung, EntlastungRepo

Diese Datei re-exportiert alles für Rückwärtskompatibilität.
"""
from __future__ import annotations

from pathlib import Path

# Schema + Verbindung
from db.schema import DbSchema, DB_PATH

# Einträge
from db.eintraege import (
    PflegeEintrag, EintragsRepo, _row_to_eintrag,
    WOCHENTAGE,
    ART_STUNDENWEISE, ART_TAGEWEISE, PFLEGE_ARTEN,
    GRUND_URLAUB, GRUND_KRANKHEIT, GRUND_SONSTIGES, PFLEGE_GRUENDE,
    ERSATZ_PRIVAT, ERSATZ_DIENST, ERSATZ_ARTEN,
)

# Personen
from db.personen import PersonenRepo

# Versicherter
from db.versicherte import Versicherter, VersicherterRepo

# User
from db.users import User, UserRepo

# Ersatzpflege
from db.ersatzpflege import Ersatzpflegekraft, ErsatzRepo

# Settings + Planung
from db.settings import UserSettings, UserSettingsRepo, PlanungsRepo

# Entlastung
from db.entlastung import EntlastungBuchung, EntlastungRepo
from db.pflegegrad_verlauf import PflegegradEintrag, PflegegradVerlaufRepo
from db.tagebuch import TagebuchEintrag, TagebuchRepo, KATEGORIEN, KATEGORIEN_LABELS, STIMMUNG_LABELS

MONATE_DE = [
    "", "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]


class PflegraDB:
    """
    Fassade über alle Repos.
    Alle bestehenden Aufrufe im Code bleiben unverändert.
    """

    SCHEMA_VERSION = DbSchema.SCHEMA_VERSION

    def __init__(self, db_path=DB_PATH) -> None:
        self.db_path        = db_path
        self._schema        = DbSchema(db_path)
        self._eintraege     = EintragsRepo(self._schema)
        self._personen      = PersonenRepo(self._schema)
        self._vers          = VersicherterRepo(self._schema)
        self._planung       = PlanungsRepo(self._schema)
        self._ersatz        = ErsatzRepo(self._schema)
        self._users         = UserRepo(self._schema)
        self._user_settings = UserSettingsRepo(self._schema)
        self._entlastung    = EntlastungRepo(self._schema)
        self._pg_verlauf    = PflegegradVerlaufRepo(self._schema)
        self._tagebuch      = TagebuchRepo(self._schema)
        self._schema.migrate()

    # -- Einträge --------------------------------------------------
    def insert(self, eintrag):                               return self._eintraege.insert(eintrag)
    def insert_many(self, eintraege):                        return self._eintraege.insert_many(eintraege)
    def alle(self, owner_id: int = 0):                       return self._eintraege.alle(owner_id)
    def nach_person_und_jahr(self, person, jahr, owner_id=0): return self._eintraege.nach_person_und_jahr(person, jahr, owner_id)
    def nach_monat(self, person, jahr, monat, owner_id=0):   return self._eintraege.nach_monat(person, jahr, monat, owner_id)
    def jahre(self, owner_id: int = 0):                      return self._eintraege.jahre(owner_id)
    def update(self, eintrag):                               return self._eintraege.update(eintrag)
    def loeschen(self, eintrag_id):                          return self._eintraege.loeschen(eintrag_id)
    def bulk_loeschen(self, ids):                            return self._eintraege.bulk_loeschen(ids)
    def duplikate_finden(self):                              return self._eintraege.duplikate_finden()
    def suche(self, suchbegriff):                            return self._eintraege.suche(suchbegriff)
    def statistik(self, owner_id: int = 0):                  return self._eintraege.statistik(owner_id)

    # -- Planung ---------------------------------------------------
    def planung_laden(self, person, jahr):                   return self._planung.laden(person, jahr)
    def planung_bulk_speichern(self, person, jahr, planung): return self._planung.bulk_speichern(person, jahr, planung)
    def planung_loeschen(self, person, jahr):                return self._planung.loeschen(person, jahr)

    # -- Personen --------------------------------------------------
    def person_anlegen(self, name, notiz="", owner_id=0):             return self._personen.anlegen(name, notiz, owner_id)
    def person_umbenennen(self, alter, neu):                          return self._personen.umbenennen(alter, neu)
    def person_loeschen(self, name, owner_id=0):                      return self._personen.loeschen(name, owner_id)
    def person_loeschen_mit_eintraegen(self, name, owner_id=0):       return self._personen.loeschen_mit_eintraegen(name, owner_id)
    def personen(self, owner_id: int = 0):                            return self._personen.namen(owner_id)
    def personen_liste(self, owner_id: int = 0):                      return self._personen.liste(owner_id)

    # -- Versicherter ----------------------------------------------
    def versicherter_laden(self, person_name):               return self._vers.laden(person_name)
    def versicherter_speichern(self, v):                     return self._vers.speichern(v)
    def versicherter_loeschen(self, person_name):            return self._vers.loeschen(person_name)

    # -- UserSettings ----------------------------------------------
    def user_settings_laden(self, user_id):                  return self._user_settings.laden(user_id)
    def user_settings_speichern(self, s):                    return self._user_settings.speichern(s)

    # -- User ------------------------------------------------------
    def user_alle(self):                                     return self._users.alle()
    def user_laden(self, user_id):                           return self._users.laden_by_id(user_id)
    def user_laden_by_username(self, username):              return self._users.laden_by_username(username)
    def user_speichern(self, u):                             return self._users.speichern(u)
    def user_loeschen(self, user_id):                        return self._users.loeschen(user_id)
    def user_anzahl(self):                                   return self._users.anzahl()
    def user_admin_existiert(self):                          return self._users.admin_existiert()

    # -- Schema ----------------------------------------------------
    def schema_version(self):                                return self._schema.schema_version()

    # -- Ersatzpflegekräfte ----------------------------------------
    def ersatz_alle(self, person, owner_id: int = 0):        return self._ersatz.alle(person, owner_id)
    def ersatz_speichern(self, e):                           return self._ersatz.speichern(e)
    def ersatz_loeschen(self, ersatz_id, person):            return self._ersatz.loeschen(ersatz_id, person)
    def ersatz_laden(self, ersatz_id):                       return self._ersatz.laden(ersatz_id)
    def ersatz_letzten(self, person):                        return self._ersatz.letzten_fuer_person(person)

    # -- Entlastungsbetrag -----------------------------------------
    def entlastung_alle(self, person, owner_id, jahr=None):         return self._entlastung.alle(person, owner_id, jahr)
    def entlastung_speichern(self, b):                              return self._entlastung.speichern(b)
    def entlastung_loeschen(self, buchung_id, owner_id):            return self._entlastung.loeschen(buchung_id, owner_id)
    def entlastung_summe(self, person, owner_id, jahr, monat=None): return self._entlastung.summe(person, owner_id, jahr, monat)

    # -- Pflegegrad-Verlauf ----------------------------------------
    def pg_verlauf_speichern(self, eintrag):                        return self._pg_verlauf.speichern(eintrag)
    def pg_verlauf_alle(self, owner_id, person=""):                 return self._pg_verlauf.alle(owner_id, person)
    def pg_verlauf_loeschen(self, eintrag_id, owner_id):            return self._pg_verlauf.loeschen(eintrag_id, owner_id)
    def pg_verlauf_personen(self, owner_id):                        return self._pg_verlauf.personen(owner_id)

    # -- Pflegetagebuch --------------------------------------------
    def tagebuch_speichern(self, e):                                return self._tagebuch.speichern(e)
    def tagebuch_alle(self, owner_id, person="", kategorie="", limit=0): return self._tagebuch.alle(owner_id, person, kategorie, limit)
    def tagebuch_laden(self, eintrag_id, owner_id):                 return self._tagebuch.laden(eintrag_id, owner_id)
    def tagebuch_loeschen(self, eintrag_id, owner_id):              return self._tagebuch.loeschen(eintrag_id, owner_id)
    def tagebuch_personen(self, owner_id):                          return self._tagebuch.personen(owner_id)
    def tagebuch_statistik(self, owner_id, person=""):              return self._tagebuch.statistik(owner_id, person)
