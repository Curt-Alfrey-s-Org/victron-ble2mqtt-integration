#!/usr/bin/env sh
set -eu
HOST="${MQTT_HOST:-192.168.0.1}"
PORT="${MQTT_PORT:-1883}"
USER="${MQTT_USER:-victron}"
PASS="${MQTT_PASSWORD:-changeme}"
MSG="ping from $(hostname) at $(date -Iseconds)"
exec mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -r \
  -t "victron/test/ping" -m "$MSG"
