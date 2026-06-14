# Changelog

## v1.4.0 (14.06.2026)

### Neu

- Aufgabenübersicht: zentrale Seite mit allen offenen Aufgaben und Fristen
  - Ampelfarben zeigen Dringlichkeit: rot (überfällig), orange (1–7 Tage), gelb (8–30 Tage), grün (> 30 Tage)
- Zeitachse: chronologische Ereignisübersicht pro versicherter Person
  - Pflegeberatungen, Gutachten, Pflegegrad-Änderungen, Dokumente, Entlastungsbuchungen und Fristen auf einen Blick

### Verbessert

- Dashboard neu strukturiert und auf die versicherten Personen fokussiert
- Wichtige Informationen wie Aufgaben, Budget und nächste Termine sind jetzt direkt auf den Personenkarten sichtbar
- Pflegegrad-Badge, Aufgaben-Badge und Nächste-Aufgabe-Bereich sind direkt anklickbar und führen zur passenden Aufgabenübersicht
- Bei einer einzelnen versicherten Person wird die Karte automatisch zentriert dargestellt
- Statistik-Kacheln entfernt, da diese Informationen auf den Personenkarten vollständig abgebildet sind

## v1.3.3 (12.06.2026)

### Neu

- Pflegeberatungs-Kachel auf dem Dashboard
- Nächste-Aktion-Kachel auf dem Dashboard
- Dokumentenarchiv pro versicherter Person

## v1.3.0 (10.06.2026)

### Neu

- PWA-Verbesserungen: Manifest-Shortcuts, Offline-Fallback, Cache-first Service Worker
- PWA-Installationsbanner mit 7-Tage-Dismissal
- Mobile- und Touch-UI verbessert

## v1.2.1 (08.06.2026)

### Sicherheit

- Backup und Wiederherstellung sind jetzt vollständig auf Administratoren beschränkt
- Der Menüpunkt für Backups wird nur noch Administratoren angezeigt

### Neu

- Nutzungsstatistik im Bereich „Admin & Systemstatus"
  - Logins heute und diese Woche
  - Fehlgeschlagene Anmeldungen
  - Anzahl der Gutachten-Analysen
  - Aktive und registrierte Benutzer
- Gutachten-Analysen werden jetzt zusätzlich im Audit-Log erfasst

## v1.2.0 (07.06.2026)

### Neu

- Gutachten-Analyse für MD- und MDK-Gutachten
- PDF-Dateien können direkt hochgeladen und ausgewertet werden
- Erkennung von Pflegegrad, Gesamtpunkten und den Bewertungen aller sechs Module
- Erkennung von Gutachtentyp, Datum und Diagnosen
- Unterstützung für gescannte PDFs durch OCR (Tesseract)
- Anzeige der Analysequalität für die erkannten Daten
- Analyseergebnisse werden benutzerbezogen gespeichert und können jederzeit erneut aufgerufen werden
- Maximale Dateigröße für Uploads: 50 MB

## v1.1.0 (05.06.2026)

### Neu

- Benutzervertretung: Administratoren können sich temporär als anderer Benutzer anmelden
- Audit-Log für Anmeldungen, Benutzerverwaltung und Benutzervertretung
- Windows-Version überarbeitet
  - Kein Konsolenfenster mehr
  - Tray-Symbol integriert
  - Schutz vor mehrfach gestarteten Instanzen
- Unterstützung für eine lokale `.env`-Datei zur Konfiguration des Datenverzeichnisses

### Behoben

- Fehler bei der Benutzervertretung behoben, wodurch Daten teilweise dem falschen Benutzer zugeordnet werden konnten

## v1.0.0 (04.06.2026)

Erste stabile Version von Pflegra.

### Enthaltene Funktionen

- Verwaltung von Verhinderungs- und Kurzzeitpflege
- Budgetverwaltung mit Jahresübersicht und Prognose
- Pflegegradrechner nach § 15 SGB XI
- Leistungsfinder für Pflegeleistungen
- Verwaltung des Entlastungsbetrags
- PDF-Exporte für Nachweise, Berichte und Schreiben
- Verwaltung von Ersatzpflegekräften
- Mehrbenutzerbetrieb mit Rollen und Datentrennung
- Integriertes Demo-System
- Deutsche und englische Oberfläche
- Automatische Backups
- Fernzugriff über Tailscale
- Docker-Unterstützung für amd64 und arm64
- Windows-Schnellstart
