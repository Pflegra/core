# Privacy & Datenschutz

## Grundsatz

Pflegra wurde von Grund auf nach dem Prinzip **"Daten gehören dir"** entwickelt.

Alle Daten, die du in Pflegra eingibst, bleiben ausschließlich auf deinem eigenen System — ohne Ausnahme.

---

## Was Pflegra speichert

Pflegra speichert alle Daten lokal in einer SQLite-Datenbank (`pflegra.db`) auf deinem Server:

- Versicherte Personen und ihre Stammdaten
- Pflege-Einträge (Datum, Zeit, Art, Ersatzpflegekraft)
- Budgetplanungen
- Entlastungsbetrag-Buchungen
- Pflegegrad-Einschätzungen und Verlauf
- Benutzerkonten (Benutzername + bcrypt-Hash des Passworts)
- Benutzerspezifische Einstellungen (Absender, Stundensatz)

---

## Was Pflegra **nicht** tut

- ❌ Keine Übertragung von Daten an externe Server
- ❌ Keine Telemetrie, kein Analytics, kein Tracking
- ❌ Keine Cloud-Anbindung
- ❌ Keine Werbung
- ❌ Keine Weitergabe von Daten an Dritte

---

## Cookies

Pflegra setzt zwei Cookies im Browser:

**Session-Cookie (`pflegra_session`)**
- Enthält nur eine signierte Benutzer-ID (keine persönlichen Daten)
- Ist `HttpOnly` (nicht per JavaScript auslesbar)
- Ist bei HTTPS-Betrieb `Secure`
- Läuft nach 12 Stunden ab

**Sprach-Cookie (`pflegra_lang`)**
- Speichert die gewählte Sprache (z.B. `de` oder `en`)
- Enthält keine persönlichen Daten
- Läuft nach 365 Tagen ab oder wird beim nächsten Sprachwechsel aktualisiert

---

## Demo-Nutzer

Der eingebaute Demo-Nutzer (`demo/demo`) enthält ausschließlich fiktive Musterdaten (Max Mustermann). Diese Daten werden automatisch zurückgesetzt — beim Abmelden und alle 60 Minuten.

---

## Backups

Automatische Backups werden lokal im Verzeichnis `/share/pflegra/backups/` gespeichert. Sie verlassen das System nicht automatisch.

---

## Externe Dienste

Pflegra selbst nutzt keine externen Dienste. Wenn du Tailscale für den Fernzugriff konfigurierst, gelten die Datenschutzbestimmungen von [Tailscale Inc.](https://tailscale.com/privacy-policy) für die VPN-Verbindung — nicht für die Pflegra-Daten selbst.

---

## Verantwortung

Da Pflegra selbst gehostet wird, bist du als Betreiber für die Datensicherheit deiner Instanz verantwortlich. Dazu gehören:

- Sichere Passwörter
- Regelmäßige Backups
- Absicherung des Netzwerkzugangs
- Aktuelle Software-Updates

---

## Kontakt

Bei Fragen zum Datenschutz: [s.l.neu@web.de](mailto:s.l.neu@web.de)

---

*Pflegra ist unter AGPLv3 lizenziert. © 2024–2026 Stefan Neu. Kommerzielle Nutzung unter den Bedingungen der AGPLv3 ist gestattet. Für alternative Lizenzbedingungen: [s.l.neu@web.de](mailto:s.l.neu@web.de). Es wird keine Verantwortung für Datenverlust oder Sicherheitslücken übernommen, die durch fehlerhafte Konfiguration oder veraltete Software entstehen.*
