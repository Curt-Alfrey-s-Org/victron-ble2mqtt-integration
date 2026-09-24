#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f nodered.env ]]; then
  echo "Missing nodered.env (copy from nodered.env.example and set HA_LONG_LIVED_TOKEN)." >&2
  exit 1
fi
# Production on .105 is systemd user nodered-solar.service (host :1880), not Docker.
if docker ps -q -f name=nodered-solar 2>/dev/null | grep -q .; then
  docker compose -f docker-compose.nodered.yml down || true
fi
python3 scripts/sync_nodered_systemd_data.py
systemctl --user restart nodered-solar.service
sleep 3
if ! curl -fsS --max-time 10 http://127.0.0.1:1880/ >/dev/null; then
  echo "Node-RED not responding on :1880" >&2
  exit 1
fi
echo "Node-RED: http://127.0.0.1:1880/ (LAN: http://192.168.0.105:1880/)"
echo "Tabs: Solar plant diagram (8-panel group), Solar computed meters; page /solar/computed"
