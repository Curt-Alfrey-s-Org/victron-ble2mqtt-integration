#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f nodered.env ]]; then
  echo "Missing nodered.env (copy from nodered.env.example and set HA_LONG_LIVED_TOKEN)." >&2
  exit 1
fi
docker compose -f docker-compose.nodered.yml build
docker compose -f docker-compose.nodered.yml up -d
sleep 3
cid=$(docker ps -q -f name=nodered-solar)
if [[ -z "$cid" ]]; then
  echo "nodered-solar container not running" >&2
  exit 1
fi
docker cp flows/solar_plant_diagram.json "${cid}:/data/flows.json"
docker restart nodered-solar
echo "Node-RED: http://127.0.0.1:1880/ (LAN: http://192.168.0.105:1880/)"
echo "Import/update flow tab: Solar plant diagram"
