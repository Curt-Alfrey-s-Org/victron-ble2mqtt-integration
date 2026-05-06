#!/usr/bin/env bash
# Mosquitto liveness: subscribe to $SYS/broker/uptime; restart broker if wedged.
# Credentials come from /etc/mosquitto/watchdog.env (installed by deploy.sh).
set -euo pipefail
HOST=127.0.0.1
PORT=1883
if [[ -f /etc/mosquitto/watchdog.env ]]; then
  set -a
  # shellcheck disable=SC1091
  source /etc/mosquitto/watchdog.env
  set +a
  PORT="${MQTT_PORT:-1883}"
fi
args=(-h "$HOST" -p "$PORT")
if [[ -n "${MQTT_USER:-}" && -n "${MQTT_PASSWORD:-}" ]]; then
  args+=(-u "$MQTT_USER" -P "$MQTT_PASSWORD")
fi
args+=(-t '$SYS/broker/uptime' -C 1 -W 8)
if mosquitto_sub "${args[@]}" >/dev/null 2>&1; then
  exit 0
fi
logger -t mqtt-watchdog 'Mosquitto unresponsive; restarting'
systemctl restart mosquitto || true
