@echo off
title Pflegra - Status

echo.
echo ===================================
echo   Pflegra Status
echo ===================================
echo.

docker compose ps
echo.

docker exec pflegra python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" >nul 2>&1
if errorlevel 1 (
    echo Status: NICHT ERREICHBAR
) else (
    echo Status: LAEUFT  -  http://localhost:8000
)
echo.
pause
