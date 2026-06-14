"""
services/erinnerungen_service.py
Berechnet fällige Erinnerungen und versendet sie per E-Mail und/oder Push.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

log = logging.getLogger(__name__)


# ── Konfiguration ─────────────────────────────────────────────────────────────

@dataclass
class ErinnerungenConfig:
    """Globale Admin-Konfiguration für Erinnerungen."""
    vorlauf_pflegeberatung:    int = 14
    vorlauf_entlastungsbetrag: int = 30
    vorlauf_fristen:           int = 14
    smtp_host:        str = ""
    smtp_port:        int = 587
    smtp_user:        str = ""
    smtp_passwort:    str = ""
    smtp_absender:    str = ""
    smtp_tls:         bool = True
    push_vapid_public:  str = ""
    push_vapid_private: str = ""
    push_aktiv:       bool = False
    erinnerung_stunde: int = 8

    @classmethod
    def aus_db(cls, db) -> "ErinnerungenConfig":
        """Lädt Konfiguration aus erinnerungen_config Tabelle."""
        try:
            with db._schema.connect() as conn:
                rows = conn.execute("SELECT schluessel, wert FROM erinnerungen_config").fetchall()
            cfg = {r["schluessel"]: r["wert"] for r in rows}
            return cls(
                vorlauf_pflegeberatung=int(cfg.get("vorlauf_pflegeberatung", 14)),
                vorlauf_entlastungsbetrag=int(cfg.get("vorlauf_entlastungsbetrag", 30)),
                vorlauf_fristen=int(cfg.get("vorlauf_fristen", 14)),
                smtp_host=cfg.get("smtp_host", ""),
                smtp_port=int(cfg.get("smtp_port", 587)),
                smtp_user=cfg.get("smtp_user", ""),
                smtp_passwort=cfg.get("smtp_passwort", ""),
                smtp_absender=cfg.get("smtp_absender", ""),
                smtp_tls=cfg.get("smtp_tls", "1") == "1",
                push_vapid_public=cfg.get("push_vapid_public", ""),
                push_vapid_private=cfg.get("push_vapid_private", ""),
                push_aktiv=cfg.get("push_aktiv", "0") == "1",
                erinnerung_stunde=int(cfg.get("erinnerung_stunde", 8)),
            )
        except Exception as e:
            log.error("ErinnerungenConfig laden fehlgeschlagen: %s", e)
            return cls()

    def speichern(self, db) -> None:
        """Speichert Konfiguration in erinnerungen_config Tabelle."""
        werte = {
            "vorlauf_pflegeberatung": str(self.vorlauf_pflegeberatung),
            "vorlauf_entlastungsbetrag": str(self.vorlauf_entlastungsbetrag),
            "vorlauf_fristen": str(self.vorlauf_fristen),
            "smtp_host": self.smtp_host,
            "smtp_port": str(self.smtp_port),
            "smtp_user": self.smtp_user,
            "smtp_passwort": self.smtp_passwort,
            "smtp_absender": self.smtp_absender,
            "smtp_tls": "1" if self.smtp_tls else "0",
            "push_vapid_public": self.push_vapid_public,
            "push_vapid_private": self.push_vapid_private,
            "push_aktiv": "1" if self.push_aktiv else "0",
            "erinnerung_stunde": str(self.erinnerung_stunde),
        }
        with db._schema.connect() as conn:
            for k, v in werte.items():
                conn.execute(
                    "INSERT OR REPLACE INTO erinnerungen_config (schluessel, wert) VALUES (?, ?)",
                    (k, v)
                )

    @property
    def smtp_konfiguriert(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_passwort)


# ── Fällige Erinnerungen berechnen ────────────────────────────────────────────

@dataclass
class Erinnerung:
    typ:    str   # "pflegeberatung" | "entlastungsbetrag" | "frist"
    person: str
    titel:  str
    datum:  date
    tage:   int   # Tage bis zur Fälligkeit


def berechne_faellige_erinnerungen(db, owner_id: int, cfg: ErinnerungenConfig) -> list[Erinnerung]:
    """
    Berechnet welche Erinnerungen heute ausgelöst werden sollen.
    Eine Erinnerung wird genau einmal ausgelöst: wenn heute == faellig_datum - vorlauf_tage.
    """
    heute = date.today()
    erinnerungen: list[Erinnerung] = []

    # Pflegeberatungen
    try:
        with db._schema.connect() as conn:
            rows = conn.execute(
                "SELECT person, datum FROM pflegeberatung WHERE owner_id=? ORDER BY datum DESC",
                (owner_id,)
            ).fetchall()
        seen_personen = set()
        for row in rows:
            person = row["person"]
            if person in seen_personen:
                continue
            seen_personen.add(person)
            try:
                letzte = date.fromisoformat(row["datum"])
                # Nächste Beratung = 6 Monate später
                monat = letzte.month + 6
                jahr = letzte.year + (monat - 1) // 12
                monat = ((monat - 1) % 12) + 1
                naechste = letzte.replace(year=jahr, month=monat)
                ziel = naechste - timedelta(days=cfg.vorlauf_pflegeberatung)
                if ziel == heute:
                    tage = (naechste - heute).days
                    erinnerungen.append(Erinnerung(
                        typ="pflegeberatung",
                        person=person,
                        titel=f"Pflegeberatung fällig am {naechste.strftime('%d.%m.%Y')}",
                        datum=naechste,
                        tage=tage,
                    ))
            except Exception:
                pass
    except Exception as e:
        log.error("Pflegeberatung-Erinnerungen Fehler: %s", e)

    # Entlastungsbetrag (Jahresende-Übertrag)
    try:
        jahresende = date(heute.year, 12, 31)
        ziel = jahresende - timedelta(days=cfg.vorlauf_entlastungsbetrag)
        if ziel == heute:
            # Für alle Personen mit Einträgen
            with db._schema.connect() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT person FROM pflege_eintraege WHERE owner_id=?",
                    (owner_id,)
                ).fetchall()
            for row in rows:
                erinnerungen.append(Erinnerung(
                    typ="entlastungsbetrag",
                    person=row["person"],
                    titel=f"Entlastungsbetrag-Übertrag prüfen (Jahresende {heute.year})",
                    datum=jahresende,
                    tage=cfg.vorlauf_entlastungsbetrag,
                ))
    except Exception as e:
        log.error("Entlastungsbetrag-Erinnerungen Fehler: %s", e)

    # Allgemeine Fristen (aus Aufgaben-Service)
    try:
        from services.aufgaben_service import berechne_aufgaben
        from services.fristen_service import berechne_fristen
        from pflege_rules import get_regelwerk

        aktuelles_jahr = heute.year
        with db._schema.connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT person FROM pflege_eintraege WHERE owner_id=?",
                (owner_id,)
            ).fetchall()
            personen_daten = []
            for row in rows:
                ev = conn.execute(
                    "SELECT COALESCE(SUM(betrag),0) as s FROM entlastung_buchungen WHERE owner_id=? AND strftime('%Y',datum)=?",
                    (owner_id, str(aktuelles_jahr))
                ).fetchone()
                personen_daten.append({
                    "name": row["person"],
                    "bericht": None,
                    "entlastung_verbrauch_gesamt": ev["s"] if ev else 0.0,
                    "entlastung_verbrauch_monat": 0.0,
                    "letztes_pg_datum": None,
                    "vers": None,
                })

        regelwerk = get_regelwerk(aktuelles_jahr)
        fristen = berechne_fristen(personen_daten, aktuelles_jahr, regelwerk)
        aufgaben = berechne_aufgaben(fristen, [])

        for a in aufgaben:
            if a.faellig_datum:
                ziel = a.faellig_datum - timedelta(days=cfg.vorlauf_fristen)
                if ziel == heute and a.typ not in ("entlastungsbetrag",):
                    erinnerungen.append(Erinnerung(
                        typ="frist",
                        person=a.person,
                        titel=a.titel,
                        datum=a.faellig_datum,
                        tage=a.tage,
                    ))
    except Exception as e:
        log.error("Fristen-Erinnerungen Fehler: %s", e)

    return erinnerungen



# ── Verlauf loggen ─────────────────────────────────────────────────────────────

def _log_erinnerung(db, owner_id: int, kanal: str, e: "Erinnerung", erfolg: bool) -> None:
    try:
        with db._schema.connect() as conn:
            conn.execute("""
                INSERT INTO erinnerungen_log (owner_id, kanal, person, typ, titel, datum, erfolg)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (owner_id, kanal, e.person, e.typ, e.titel, e.datum.isoformat(), 1 if erfolg else 0))
    except Exception as ex:
        log.warning("Verlauf-Log fehlgeschlagen: %s", ex)


# ── E-Mail versenden ──────────────────────────────────────────────────────────

def versende_email(
    cfg: ErinnerungenConfig,
    empfaenger: str,
    empfaenger_name: str,
    erinnerungen: list[Erinnerung],
) -> bool:
    """Versendet eine Erinnerungs-E-Mail. Gibt True bei Erfolg zurück."""
    if not cfg.smtp_konfiguriert:
        log.warning("SMTP nicht konfiguriert — E-Mail nicht versendet")
        return False
    if not empfaenger:
        log.warning("Kein Empfänger — E-Mail nicht versendet")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Pflegra – {len(erinnerungen)} Erinnerung{'en' if len(erinnerungen) != 1 else ''}"
        msg["From"] = f"Pflegra <{cfg.smtp_absender or cfg.smtp_user}>"
        msg["To"] = empfaenger

        # Textversion
        zeilen = [f"Hallo {empfaenger_name or 'Pflegeperson'},\n"]
        zeilen.append("folgende Erinnerungen stehen in Pflegra an:\n")
        for e in erinnerungen:
            zeilen.append(f"  • {e.person}: {e.titel} (in {e.tage} Tagen, am {e.datum.strftime('%d.%m.%Y')})")
        zeilen.append("\nDiese E-Mail wurde automatisch von Pflegra verschickt.")
        text = "\n".join(zeilen)

        # HTML-Version
        items = ""
        for e in erinnerungen:
            items += f"""
            <tr>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-weight:600">{e.person}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb">{e.titel}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;white-space:nowrap">{e.datum.strftime('%d.%m.%Y')}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#6b7280">in {e.tage} Tagen</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html>
<body style="font-family:system-ui,sans-serif;color:#111827;max-width:600px;margin:0 auto;padding:24px">
  <div style="background:#2C5F8A;padding:16px 24px;border-radius:8px 8px 0 0">
    <span style="color:#fff;font-size:1.2rem;font-weight:700">🏠 Pflegra</span>
    <span style="color:#bfdbfe;font-size:.9rem;margin-left:8px">Erinnerungen</span>
  </div>
  <div style="border:1px solid #e5e7eb;border-top:none;padding:24px;border-radius:0 0 8px 8px">
    <p>Hallo {empfaenger_name or 'Pflegeperson'},</p>
    <p>folgende Erinnerungen stehen an:</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
      <thead>
        <tr style="background:#f9fafb">
          <th style="padding:8px 12px;text-align:left;font-size:.8rem;color:#6b7280">Person</th>
          <th style="padding:8px 12px;text-align:left;font-size:.8rem;color:#6b7280">Aufgabe</th>
          <th style="padding:8px 12px;text-align:left;font-size:.8rem;color:#6b7280">Datum</th>
          <th style="padding:8px 12px;text-align:left;font-size:.8rem;color:#6b7280">Fälligkeit</th>
        </tr>
      </thead>
      <tbody>{items}</tbody>
    </table>
    <p style="color:#6b7280;font-size:.85rem">Diese E-Mail wurde automatisch von Pflegra verschickt.</p>
  </div>
</body>
</html>"""

        msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        if cfg.smtp_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(cfg.smtp_user, cfg.smtp_passwort)
                server.sendmail(cfg.smtp_absender or cfg.smtp_user, empfaenger, msg.as_string())
        else:
            with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port) as server:
                server.login(cfg.smtp_user, cfg.smtp_passwort)
                server.sendmail(cfg.smtp_absender or cfg.smtp_user, empfaenger, msg.as_string())

        log.info("E-Mail versendet an %s (%d Erinnerungen)", empfaenger, len(erinnerungen))
        return True

    except Exception as e:
        log.error("E-Mail Versand fehlgeschlagen: %s", e, exc_info=True)
        return False


# ── Push-Benachrichtigung ─────────────────────────────────────────────────────

def versende_push(
    cfg: ErinnerungenConfig,
    db,
    owner_id: int,
    erinnerungen: list[Erinnerung],
) -> int:
    """
    Versendet Web-Push-Benachrichtigungen.
    Gibt Anzahl erfolgreich versendeter Nachrichten zurück.
    Benötigt pywebpush (optional installiert).
    """
    if not cfg.push_aktiv or not cfg.push_vapid_private:
        return 0

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        log.warning("pywebpush nicht installiert — Push nicht verfügbar")
        return 0

    # Push-Subscriptions aus DB laden
    try:
        with db._schema.connect() as conn:
            rows = conn.execute(
                "SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE owner_id=?",
                (owner_id,)
            ).fetchall()
    except Exception:
        return 0

    if not rows:
        return 0

    titel = f"{len(erinnerungen)} Erinnerung{'en' if len(erinnerungen) != 1 else ''} in Pflegra"
    body_teile = [f"{e.person}: {e.titel}" for e in erinnerungen[:3]]
    if len(erinnerungen) > 3:
        body_teile.append(f"und {len(erinnerungen) - 3} weitere...")
    body = "\n".join(body_teile)

    import json
    payload = json.dumps({"title": titel, "body": body, "icon": "/static/icons/icon-192.png"})

    erfolge = 0
    for row in rows:
        try:
            webpush(
                subscription_info={
                    "endpoint": row["endpoint"],
                    "keys": {"p256dh": row["p256dh"], "auth": row["auth"]},
                },
                data=payload,
                vapid_private_key=cfg.push_vapid_private,
                vapid_claims={"sub": f"mailto:{cfg.smtp_user or 'pflegra@localhost'}"},
            )
            erfolge += 1
        except WebPushException as e:
            log.warning("Push fehlgeschlagen für %s: %s", row["endpoint"][:40], e)

    log.info("Push versendet: %d/%d erfolgreich", erfolge, len(rows))
    return erfolge


# ── Hauptfunktion: alle Nutzer prüfen ────────────────────────────────────────

def erinnerungen_lauf(db) -> None:
    """
    Wird täglich vom Scheduler aufgerufen.
    Prüft alle aktiven Nutzer und versendet fällige Erinnerungen.
    """
    cfg = ErinnerungenConfig.aus_db(db)

    if not cfg.smtp_konfiguriert and not cfg.push_aktiv:
        log.debug("Erinnerungen: weder SMTP noch Push konfiguriert — übersprungen")
        return

    try:
        with db._schema.connect() as conn:
            users = conn.execute(
                "SELECT u.id, u.username, s.absender_mail, s.absender_name, "
                "s.benachrichtigung_email, s.benachrichtigung_push "
                "FROM users u "
                "LEFT JOIN user_settings s ON s.user_id = u.id "
                "WHERE u.aktiv = 1 AND u.username != 'demo'"
            ).fetchall()
    except Exception as e:
        log.error("Erinnerungen: Nutzer laden fehlgeschlagen: %s", e)
        return

    for user in users:
        owner_id = user["id"]
        per_email = bool(user["benachrichtigung_email"])
        per_push  = bool(user["benachrichtigung_push"])

        if not per_email and not per_push:
            continue

        erinnerungen = berechne_faellige_erinnerungen(db, owner_id, cfg)
        if not erinnerungen:
            continue

        log.info("Nutzer %s: %d Erinnerung(en) fällig", user["username"], len(erinnerungen))

        if per_email:
            ok_email = versende_email(cfg, user["absender_mail"], user["absender_name"], erinnerungen)
            for e in erinnerungen:
                _log_erinnerung(db, owner_id, "email", e, ok_email)

        if per_push and cfg.push_aktiv:
            anzahl = versende_push(cfg, db, owner_id, erinnerungen)
            for e in erinnerungen:
                _log_erinnerung(db, owner_id, "push", e, anzahl > 0)
