@echo off
title Pflegra - Update

echo.
echo ===================================
echo   Pflegra Update
echo ===================================
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Docker ist nicht gestartet.
    pause
    exit /b 1
)

echo [INFO] Neues Image wird heruntergeladen...
docker compose pull

echo.
echo [INFO] Pflegra wird neu gestartet...
docker compose up -d

echo.
echo [INFO] Altes Image wird bereinigt...
docker image prune -f >nul 2>&1

echo.
echo ===================================
echo   Update abgeschlossen!
echo   http://localhost:8000
echo ===================================
echo.
pause
