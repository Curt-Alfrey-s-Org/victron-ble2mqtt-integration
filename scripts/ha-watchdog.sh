#!/usr/bin/env bash
# Simple watchdog: try to GET HA HTTP endpoint; if fails, restart the container
set -euo pipefail

HA_URL="http://127.0.0.1:8123/"
CONTAINER="homeassistant"

if curl -fsS --max-time 5 "$HA_URL" >/dev/null 2>&1; then
  echo "OK"
  exit 0
fi

echo "Home Assistant unresponsive, restarting container $CONTAINER"
/usr/bin/docker restart "$CONTAINER"
