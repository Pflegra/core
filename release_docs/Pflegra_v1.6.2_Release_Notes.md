# Pflegra v1.6.2 Release Notes

## Kalender Quality Release

Pflegra v1.6.2 verbessert die Zuverlässigkeit und Bedienbarkeit des bestehenden Kalender- und Terminmoduls. Das Release bleibt bei der bewusst einfachen Terminlogik und führt keine neue Datenbankmigration ein.

## Behobene P1-Probleme

### Dashboard-Terminlogik

Heute bereits beendete Uhrzeit-Termine werden nicht mehr als „Nächster Termin“ angezeigt. Bei wiederkehrenden Terminen springt Pflegra auf das nächste gültige Vorkommen.

Ganztagstermine und Termine ohne Endzeit bleiben am betreffenden Tag weiterhin sichtbar.

### Automatische Fristen

Automatische Fristen werden im Kalender anhand des sichtbaren Monats und Jahres berechnet. Beim Wechsel in andere Monate oder Jahre entstehen dadurch keine Berechnungen mehr auf Basis eines abweichenden Standardjahres oder des aktuellen Aufrufstags.

### Weitere Tagesereignisse

Enthält ein Kalendertag mehr als zwei Ereignisse, können alle weiteren Einträge über ein natives, tastatur- und touchbedienbares Aufklappelement angezeigt werden.

### Einheitliche Personenfilter

Gefilterte Termin- und Fristenansichten zeigen nun einheitlich:

* Einträge der ausgewählten Person
* allgemeine Einträge ohne Personenzuordnung

Personennamen bleiben beim Monatswechsel URL-sicher erhalten.

## Teststatus

### Lokal

* Python-Syntaxprüfung erfolgreich
* 19 von 19 Terminservice-/Schema-Tests bestanden

### Test Bench

* Image `pflegra_test:1.6.2`
* Healthcheck grün
* Datenbankintegrität `ok`
* 19 von 19 Service-/Schema-Tests bestanden
* 9 von 9 Router-/Filter-/Template-Tests bestanden

### Live

* Image `pflegra:1.6.2`
* Healthcheck grün
* Datenbankintegrität `ok`
* 19 von 19 Service-/Schema-Tests bestanden
* 9 von 9 Router-/Filter-/Template-Tests bestanden
* realer Regressionstest für einen bereits beendeten Serientermin erfolgreich

## Datenbank

```text
Schema: v24
Migration: keine
```

v1.6.2 verändert keine Tabellen, Constraints oder Bestandsdaten.

## Deploymentstatus

```text
Test Bench: GO
Live: GO
```

Beide Systeme laufen auf dem identischen geprüften Kalender-Fixstand.

## Bekannte Restpunkte

Nicht Bestandteil von v1.6.2:

* mobile Agendaansicht als Ersatz für die horizontal scrollende Kalendertabelle
* Terminliste mit nächstem Serienvorkommen und Vergangen/Zukünftig-Gruppierung
* Quellenfilter und Deduplizierung im Kalender
* zusätzliche Begrenzung ungültiger Monats-/Jahresparameter
* weitergehende strukturierte Fehlerprotokollierung

Weiterhin nicht vorgesehen:

* iCal-Anbindung
* RRULE-Editor
* komplexe Serienausnahmen
* Erinnerungsplattform

## Freigabe

```text
Pflegra v1.6.2: GO
```
