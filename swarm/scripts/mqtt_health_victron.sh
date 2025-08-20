#!/usr/bin/env sh
set -eu

HOST="${MQTT_HOST:-192.168.0.1}"
PORT="${MQTT_PORT:-1883}"
USER="${MQTT_USER:-victron}"
PASS="${MQTT_PASSWORD:-changeme}"
TOPIC="${TOPIC:-system/health/victron_ble}"
LOG="${LOG:-/logs/victron_ble2mqtt.log}"
INTERVAL_SEC="${INTERVAL_SEC:-120}"
STALE_SECS="${STALE_SECS:-600}"

while true; do
  if [ ! -s "$LOG" ]; then
    STATUS="WARN"; MSG="no log yet"
  else
    # mtime (GNU/BSD compatible)
    if MTIME=$(stat -c %Y "$LOG" 2>/dev/null); then :; else MTIME=$(stat -f %m "$LOG"); fi
    NOW=$(date +%s); AGE=$((NOW - MTIME))
    if [ "$AGE" -gt "$STALE_SECS" ]; then
      STATUS="WARN"; MSG="stale ${AGE}s"
    else
      STATUS="OK"; MSG="fresh ${AGE}s"
    fi
  fi

  mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -t "$TOPIC" -m "${STATUS}: ${MSG}"
  sleep "$INTERVAL_SEC"
done
