@echo off
title Pflegra - Starten

echo.
echo ===================================
echo   Pflegra wird gestartet...
echo ===================================
echo.

REM Docker prüfen
docker info >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Docker ist nicht gestartet oder nicht installiert.
    echo.
    echo Bitte Docker Desktop installieren und starten:
    echo https://www.docker.com/products/docker-desktop
    echo.
    echo Nach der Installation diese Datei erneut doppelklicken.
    echo.
    pause
    exit /b 1
)

REM .env erstellen wenn nicht vorhanden
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [INFO] .env Konfigurationsdatei erstellt.
    )
)

REM Image lokal vorhanden?
docker image inspect ghcr.io/pflegra/core:latest >nul 2>&1
if errorlevel 1 (
    REM Image nicht lokal - TAR vorhanden?
    if exist "pflegra-image.tar" (
        echo [INFO] Lade Image aus pflegra-image.tar...
        docker load -i pflegra-image.tar
    ) else (
        echo [INFO] Lade aktuelles Pflegra-Image von GitHub...
        docker compose pull
    )
) else (
    echo [INFO] Pflegra-Image bereits vorhanden.
)

echo.
echo [INFO] Starte Pflegra...
docker compose up -d

if errorlevel 1 (
    echo.
    echo [FEHLER] Pflegra konnte nicht gestartet werden.
    pause
    exit /b 1
)

REM Warten bis bereit
echo [INFO] Warte auf Pflegra...
set VERSUCHE=0
:WARTEN
set /a VERSUCHE+=1
timeout /t 2 /nobreak >nul
docker exec pflegra python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" >nul 2>&1
if errorlevel 1 (
    if %VERSUCHE% lss 15 goto WARTEN
)

echo.
echo ===================================
echo   Pflegra laeuft!
echo   http://localhost:8000
echo.
echo   Demo-Login: demo / demo
echo ===================================
echo.

start http://localhost:8000

echo Pflegra laeuft im Hintergrund.
echo Zum Beenden: stop.bat doppelklicken.
echo.
pause
