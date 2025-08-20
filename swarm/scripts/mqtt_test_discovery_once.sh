#!/usr/bin/env sh
set -eu
HOST="${MQTT_HOST:-192.168.0.1}"
PORT="${MQTT_PORT:-1883}"
USER="${MQTT_USER:-victron}"
PASS="${MQTT_PASSWORD:-changeme}"

H="$(hostname)"
CFG="/tmp/ha_test_sensor.json"

cat > "$CFG" <<JSON
{
  "name": "Victron Test Ping",
  "unique_id": "victron_test_ping_${H}",
  "state_topic": "victron/test/ping",
  "icon": "mdi:lan-connect",
  "entity_category": "diagnostic",
  "device": {
    "identifiers": ["victron_test_${H}"],
    "name": "Victron Test (${H})",
    "manufacturer": "ALFaQD",
    "model": "MQTT Test"
  }
}
JSON

exec mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -r \
  -t "homeassistant/sensor/victron_test_ping_${H}/config" -f "$CFG"
