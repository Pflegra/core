# Pflegra v1.6.2 Releaseabschluss

## Freigabeentscheidung

```text
GO für GitHub Release v1.6.2
```

Das offizielle Releasepaket wurde aus dem auf Live und Test Bench geprüften v1.6.2-Quellstand erstellt, vollständig geprüft und reproduzierbar verifiziert.

## Releaseartefakt

| Merkmal | Wert |
|---|---|
| Artefakt | `Pflegra_v1.6.2_release.zip` |
| Dateigröße | 3.688.881 Byte |
| Dateien im ZIP | 233 |
| SHA-256 | `c6fc8287bb97b27e1a101f1f7b10804cfa7b8b1e50858fadc7b1f9903f50552e` |
| Checksum-Datei | `Pflegra_v1.6.2_release.sha256` |
| Release Notes | `Pflegra_v1.6.2_Release_Notes.md` |

## Reproduzierbarkeit

Das ZIP wurde deterministisch erzeugt mit:

* alphabetisch sortierten Archiveinträgen
* festem ZIP-Zeitstempel `22.06.2026 00:00:00`
* festen Dateirechten für normale Dateien und Shellskripte
* fester Deflate-Kompressionsstufe
* expliziter Datei-Allowlist

Ein zweiter unabhängiger Paketlauf erzeugte:

```text
Größe: 3.688.881 Byte
SHA-256: c6fc8287bb97b27e1a101f1f7b10804cfa7b8b1e50858fadc7b1f9903f50552e
Bytevergleich: identisch
```

## Inhalt

Enthalten:

* `app/`
* `app/tests/`
* gespiegelte Tests unter `tests/`
* `docs/`
* `Dockerfile`
* `Dockerfile.standalone`
* `docker-compose.yml`
* `docker-compose.dev.yml`
* `config.yaml`
* `build.yaml`
* `README.md`
* `CHANGELOG.md`
* `LICENSE`
* Start-, Stop-, Update- und Deploymentskripte
* Architektur-, Datenschutz- und Deploymentdokumentation
* öffentliche Release Notes unter `release_docs/`

## Ausschlussprüfung

Nicht enthalten:

* produktive oder Test-Datenbanken
* SQLite-WAL-/SHM-Dateien
* Backups
* Gutachtendaten
* private Nutzerdaten
* `.git`
* `.env`
* `.secret_key`
* `__pycache__`
* `*.pyc`

Der Archivscan ergab:

```text
CRC-Fehler: 0
Verbotene Pfade/Dateien: 0
Fehlende Pflichtinhalte: 0
```

Die Secret-Prüfung fand ausschließlich Quellcodebezeichner, leere Umgebungsvariablenreferenzen und den fest als Testwert verwendeten Schlüssel `test-secret-key-12345`. Es wurde kein produktives Secret gefunden.

## Versionsprüfung

| Prüfung | Ergebnis |
|---|---|
| `config.yaml` | 1.6.2 |
| FastAPI-Version | 1.6.2 |
| `APP_VERSION` | 1.6.2 |
| Docker `version.txt` | 1.6.2 |
| Compose-Image | `pflegra:1.6.2` |
| Schema-Konstante | 24 |

## Teststatus

### Releasepaket

* ZIP erfolgreich entpackt
* Python-Compileall erfolgreich
* 19 von 19 Terminservice-/Schema-Tests aus dem entpackten ZIP bestanden

### Test Bench

* Container `pflegra_test:1.6.2`
* Docker Health healthy
* API-Health ok
* Datenbankintegrität ok
* Schema v24
* 19 von 19 Service-/Schema-Tests bestanden
* 9 von 9 Router-/Filter-/Template-Tests bestanden

### Live

* Container `pflegra:1.6.2`
* Docker Health healthy
* API-Health ok
* Datenbankintegrität ok
* Schema v24
* 19 von 19 Service-/Schema-Tests bestanden
* 9 von 9 Router-/Filter-/Template-Tests bestanden
* realer Dashboard-Regressionsfall erfolgreich

## Deploymentstatus

```text
Test Bench: deployed, healthy, GO
Live: deployed, healthy, GO
```

Die zentralen Kalender-Fixdateien sind zwischen lokaler Paketquelle, Live und Test Bench byteidentisch.

## Datenbankstatus

```text
Schema: v24 unverändert
Migration: keine
Datenbankänderungen durch Releasepaket-Erstellung: keine
```

## Bekannte Restpunkte

Bewusst nicht Teil des Kalender Quality Release:

* mobile Agendaansicht
* Terminliste mit nächstem Serienvorkommen und Zeitgruppierung
* Kalender-Quellenfilter und Deduplizierung
* zusätzliche Queryparameter-Härtung
* weitergehende strukturierte Fehlerprotokollierung

Diese Restpunkte sind dokumentiert und blockieren v1.6.2 nicht.

## Abschluss

Alle Anforderungen an Inhalt, Ausschlüsse, Versionierung, Tests, Prüfsummen und Reproduzierbarkeit sind erfüllt.

```text
GitHub Release v1.6.2: GO
```
