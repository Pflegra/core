# Pflegra – Windows EXE bauen

## Voraussetzungen

- Windows 10/11 (oder Windows VM)
- Python 3.11+ (von python.org, **nicht** Microsoft Store)
- Git

## Einmalige Einrichtung

```cmd
cd pflegra\app
pip install pyinstaller
pip install -r requirements_web.txt
pip install reportlab odfpy openpyxl
```

## EXE bauen

```cmd
cd pflegra\app
pyinstaller pflegra.spec
```

Die fertige EXE liegt unter:
```
pflegra\app\dist\Pflegra.exe
```

## Testen

```cmd
dist\Pflegra.exe
```

Browser öffnet sich automatisch auf http://127.0.0.1:8000

Daten werden gespeichert unter:
```
%APPDATA%\Pflegra\
```

## Troubleshooting

**ModuleNotFoundError beim Start:**
→ Modul zu `hiddenimports` in `pflegra.spec` hinzufügen, neu bauen

**Templates nicht gefunden:**
→ Prüfen ob `web/templates` korrekt in `datas` der Spec-Datei steht

**Antivirus blockiert EXE:**
→ `upx=False` ist bereits gesetzt, hilft meistens
→ Langfristig: Code Signing Zertifikat

## Nächste Schritte (Phase 2)

- `console=False` in pflegra.spec → kein Konsolenfenster
- Tray-Icon (pystray)
- Inno Setup Installer (.exe Installer mit Wizard)
- Icon einbinden (favicon.ico → Pflegra.ico)
