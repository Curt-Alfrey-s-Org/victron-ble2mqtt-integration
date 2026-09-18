#!/usr/bin/env bash
# Stop HA Container, set numeric display precision to tenths, start HA.
# Official: https://www.home-assistant.io/common-tasks/container/
#           https://www.home-assistant.io/integrations/sensor.mqtt/#suggested_display_precision
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/opt/homeassistant}"
STORAGE="${HA_CONFIG_DIR}/.storage"
SCRIPT="$ROOT/scripts/ha_set_display_precision.py"

if [[ ! -f "$SCRIPT" ]]; then
  echo "Missing $SCRIPT" >&2
  exit 1
fi
if [[ ! -f "$STORAGE/core.entity_registry" ]]; then
  echo "Missing $STORAGE/core.entity_registry" >&2
  exit 1
fi
if ! docker ps -a --format '{{.Names}}' | grep -qw homeassistant; then
  echo "homeassistant container not found" >&2
  exit 1
fi

echo "[display-precision] Stopping homeassistant ..."
docker stop homeassistant
echo "[display-precision] Writing entity registry tenths ..."
sudo python3 "$SCRIPT" --storage "$STORAGE"
echo "[display-precision] Starting homeassistant ..."
docker start homeassistant
echo "[display-precision] Waiting for container health ..."
i=0
while [ "$i" -lt 36 ]; do
  st="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' homeassistant 2>/dev/null || true)"
  if [ "$st" = "healthy" ] || [ "$st" = "running" ]; then
    echo "[display-precision] homeassistant is $st"
    break
  fi
  i=$((i + 1))
  sleep 5
done
echo "[display-precision] Refresh Lovelace if tiles still show extra decimals."
