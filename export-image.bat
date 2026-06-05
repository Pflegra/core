@echo off
title Pflegra - Image exportieren

echo.
echo [INFO] Exportiere Pflegra-Image fuer Offline-Nutzung...
echo [INFO] Dies kann einige Minuten dauern (~200 MB)
echo.

docker image inspect ghcr.io/pflegra/core:latest >nul 2>&1
if errorlevel 1 (
    echo [INFO] Image wird zuerst heruntergeladen...
    docker pull ghcr.io/pflegra/core:latest
)

docker save ghcr.io/pflegra/core:latest -o pflegra-image.tar

echo.
echo [INFO] Fertig! pflegra-image.tar wurde erstellt.
echo [INFO] Diese Datei zusammen mit start.bat auf USB-Stick kopieren.
echo [INFO] Pflegra startet dann auch ohne Internet.
echo.
pause
