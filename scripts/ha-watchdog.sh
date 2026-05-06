#!/usr/bin/env bash
# Simple watchdog: try to GET HA HTTP endpoint; if fails, restart the container.
# Exits 0 when Docker or the homeassistant container is absent so systemd does not
# log FAILED on hosts that never run Home Assistant (disable the timer there anyway).
set -euo pipefail

HA_URL="http://127.0.0.1:8123/"
CONTAINER="homeassistant"

if ! command -v docker >/dev/null 2>&1; then
  logger -t ha-watchdog "docker not in PATH; skipping"
  exit 0
fi

if ! docker inspect "$CONTAINER" >/dev/null 2>&1; then
  logger -t ha-watchdog "no container named ${CONTAINER}; skipping (run: systemctl disable --now ha-watchdog.timer)"
  exit 0
fi

if curl -fsS --max-time 5 "$HA_URL" >/dev/null 2>&1; then
  echo "OK"
  exit 0
fi

echo "Home Assistant unresponsive, restarting container $CONTAINER"
/usr/bin/docker restart "$CONTAINER"
