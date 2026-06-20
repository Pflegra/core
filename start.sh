#!/bin/bash
# Pflegra – Startscript für Linux/Mac

set -e

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║         Pflegra wird gestartet       ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# Docker prüfen
if ! docker info > /dev/null 2>&1; then
    echo "  [FEHLER] Docker ist nicht gestartet oder nicht installiert."
    echo "  Bitte installieren: https://docs.docker.com/get-docker/"
    exit 1
fi

# .env erstellen
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp .env.example .env
    echo "  [INFO] .env aus .env.example erstellt."
fi

# Starten
echo "  [INFO] Lade aktuelles Pflegra-Image..."
docker compose pull

echo "  [INFO] Starte Pflegra..."
docker compose up -d

# Warten
echo "  [INFO] Warte auf Pflegra..."
for i in $(seq 1 15); do
    sleep 2
    if docker exec pflegra python3 -c \
        "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" \
        > /dev/null 2>&1; then
        break
    fi
done

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║   Pflegra läuft!                     ║"
echo "  ║   http://localhost:8000              ║"
echo "  ║                                      ║"
echo "  ║   Demo-Login: demo / demo            ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# Browser öffnen
sleep 1
if command -v xdg-open > /dev/null; then
    xdg-open http://localhost:8000
elif command -v open > /dev/null; then
    open http://localhost:8000
fi
