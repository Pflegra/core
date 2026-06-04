#!/bin/bash
echo "  [INFO] Update wird durchgeführt..."
docker compose pull
docker compose up -d
docker image prune -f
echo "  Update abgeschlossen! http://localhost:8000"
