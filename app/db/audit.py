"""
db/audit.py — AuditLog: Sicherheitsrelevante Aktionen protokollieren

Jeder Eintrag unterscheidet zwischen:
  actor_user_id    — wer hat die Aktion ausgeführt (z.B. Admin)
  effective_user_id — für wen wurde gehandelt (z.B. User bei Impersonation)

Wenn kein Impersonation aktiv: actor_user_id == effective_user_id
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from db.schema import DbSchema


# ── Event-Konstanten ──────────────────────────────────────────────────────────

class AuditEvent:
    # Authentifizierung
    LOGIN_OK            = "login_ok"
    LOGIN_FEHLGESCHLAGEN = "login_fehlgeschlagen"
    LOGOUT              = "logout"

    # Impersonation
    IMPERSONATION_START = "impersonation_start"
    IMPERSONATION_ENDE  = "impersonation_ende"

    # Benutzerverwaltung
    USER_ERSTELLT       = "user_erstellt"
    USER_BEARBEITET     = "user_bearbeitet"
    USER_GELOESCHT      = "user_geloescht"
    PASSWORT_GEAENDERT  = "passwort_geaendert"
    ROLLE_GEAENDERT     = "rolle_geaendert"

    # Daten
    EXPORT_ERSTELLT     = "export_erstellt"
    IMPORT_DURCHGEFUEHRT = "import_durchgefuehrt"
    BACKUP_ERSTELLT     = "backup_erstellt"

    # Gutachten
    GUTACHTEN_ANALYSE   = "gutachten_analyse"

    # Einträge (Pflegeleistungen)
    EINTRAG_ERSTELLT    = "eintrag_erstellt"
    EINTRAG_BEARBEITET  = "eintrag_bearbeitet"
    EINTRAG_GELOESCHT   = "eintrag_geloescht"

    # Personen / Versicherte
    PERSON_ERSTELLT     = "person_erstellt"
    PERSON_GELOESCHT    = "person_geloescht"

    # Dokumente
    DOKUMENT_HOCHGELADEN = "dokument_hochgeladen"
    DOKUMENT_GELOESCHT  = "dokument_geloescht"

    # Pflegeberatung
    PFLEGEBERATUNG_ERSTELLT = "pflegeberatung_erstellt"
    PFLEGEBERATUNG_GELOESCHT = "pflegeberatung_geloescht"

    # Kontakte
    KONTAKT_ERSTELLT    = "kontakt_erstellt"
    KONTAKT_BEARBEITET  = "kontakt_bearbeitet"
    KONTAKT_GELOESCHT   = "kontakt_geloescht"


@dataclass
class AuditEintrag:
    id: int
    zeitstempel: str
    actor_user_id: int
    actor_username: str
    effective_user_id: Optional[int]
    effective_username: Optional[str]
    aktion: str
    details: str
    ip_adresse: str


@dataclass
class SystemStats:
    logins_heute: int
    logins_woche: int
    login_fehler_heute: int
    gutachten_heute: int
    gutachten_gesamt: int
    users_gesamt: int
    users_aktiv: int
    demo_logins_heute: int
    demo_logins_woche: int
    demo_logins_gesamt: int


class AuditRepo:
    def __init__(self, schema: DbSchema) -> None:
        self._schema = schema

    def _c(self):
        return self._schema.connect()

    def loggen(
        self,
        aktion: str,
        actor_user_id: int,
        effective_user_id: Optional[int] = None,
        details: str = "",
        ip_adresse: str = "",
    ) -> None:
        """Schreibt einen Audit-Eintrag."""
        if effective_user_id is None:
            effective_user_id = actor_user_id
        with self._c() as conn:
            conn.execute("""
                INSERT INTO audit_log
                    (zeitstempel, actor_user_id, effective_user_id,
                     aktion, details, ip_adresse)
                VALUES (datetime('now'), ?, ?, ?, ?, ?)
            """, (actor_user_id, effective_user_id, aktion, details, ip_adresse))

    def alle(self, limit: int = 200) -> List[AuditEintrag]:
        """Alle Einträge, neueste zuerst, mit Username-Join."""
        with self._c() as conn:
            rows = conn.execute("""
                SELECT
                    a.id,
                    a.zeitstempel,
                    a.actor_user_id,
                    COALESCE(u1.username, '?') AS actor_username,
                    a.effective_user_id,
                    COALESCE(u2.username, NULL) AS effective_username,
                    a.aktion,
                    a.details,
                    a.ip_adresse
                FROM audit_log a
                LEFT JOIN users u1 ON u1.id = a.actor_user_id
                LEFT JOIN users u2 ON u2.id = a.effective_user_id
                ORDER BY a.id DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [AuditEintrag(
            id=r["id"],
            zeitstempel=r["zeitstempel"],
            actor_user_id=r["actor_user_id"],
            actor_username=r["actor_username"],
            effective_user_id=r["effective_user_id"],
            effective_username=r["effective_username"],
            aktion=r["aktion"],
            details=r["details"],
            ip_adresse=r["ip_adresse"],
        ) for r in rows]

    def fuer_user(self, user_id: int, limit: int = 50) -> List[AuditEintrag]:
        """Alle Einträge die einen bestimmten User betreffen."""
        with self._c() as conn:
            rows = conn.execute("""
                SELECT
                    a.id, a.zeitstempel,
                    a.actor_user_id,
                    COALESCE(u1.username, '?') AS actor_username,
                    a.effective_user_id,
                    COALESCE(u2.username, NULL) AS effective_username,
                    a.aktion, a.details, a.ip_adresse
                FROM audit_log a
                LEFT JOIN users u1 ON u1.id = a.actor_user_id
                LEFT JOIN users u2 ON u2.id = a.effective_user_id
                WHERE a.actor_user_id = ? OR a.effective_user_id = ?
                ORDER BY a.id DESC
                LIMIT ?
            """, (user_id, user_id, limit)).fetchall()
        return [AuditEintrag(
            id=r["id"],
            zeitstempel=r["zeitstempel"],
            actor_user_id=r["actor_user_id"],
            actor_username=r["actor_username"],
            effective_user_id=r["effective_user_id"],
            effective_username=r["effective_username"],
            aktion=r["aktion"],
            details=r["details"],
            ip_adresse=r["ip_adresse"],
        ) for r in rows]

    def system_stats(self) -> SystemStats:
        """Aggregierte System-Statistik aus audit_log + users."""
        with self._c() as conn:
            def count(sql, params=()):
                return conn.execute(sql, params).fetchone()[0]

            logins_heute = count("""
                SELECT COUNT(*) FROM audit_log
                WHERE aktion = 'login_ok'
                AND date(zeitstempel) = date('now')
            """)
            logins_woche = count("""
                SELECT COUNT(*) FROM audit_log
                WHERE aktion = 'login_ok'
                AND zeitstempel >= datetime('now', '-7 days')
            """)
            login_fehler_heute = count("""
                SELECT COUNT(*) FROM audit_log
                WHERE aktion = 'login_fehlgeschlagen'
                AND date(zeitstempel) = date('now')
            """)
            gutachten_heute = count("""
                SELECT COUNT(*) FROM audit_log
                WHERE aktion = 'gutachten_analyse'
                AND date(zeitstempel) = date('now')
            """)
            gutachten_gesamt = count("""
                SELECT COUNT(*) FROM audit_log
                WHERE aktion = 'gutachten_analyse'
            """)
            users_gesamt = count("SELECT COUNT(*) FROM users")
            users_aktiv = count("SELECT COUNT(*) FROM users WHERE aktiv = 1")
            demo_row = conn.execute("SELECT id FROM users WHERE username='demo' LIMIT 1").fetchone()
            demo_id  = demo_row[0] if demo_row else -1
            demo_logins_heute = count(
                "SELECT COUNT(*) FROM audit_log WHERE aktion='login_ok' AND actor_user_id=? AND date(zeitstempel)=date('now')",
                (demo_id,))
            demo_logins_woche = count(
                "SELECT COUNT(*) FROM audit_log WHERE aktion='login_ok' AND actor_user_id=? AND zeitstempel>=datetime('now','-7 days')",
                (demo_id,))
            demo_logins_gesamt = count(
                "SELECT COUNT(*) FROM audit_log WHERE aktion='login_ok' AND actor_user_id=?",
                (demo_id,))

        return SystemStats(
            logins_heute=logins_heute,
            logins_woche=logins_woche,
            login_fehler_heute=login_fehler_heute,
            gutachten_heute=gutachten_heute,
            gutachten_gesamt=gutachten_gesamt,
            users_gesamt=users_gesamt,
            users_aktiv=users_aktiv,
            demo_logins_heute=demo_logins_heute,
            demo_logins_woche=demo_logins_woche,
            demo_logins_gesamt=demo_logins_gesamt,
        )
