#!/usr/bin/env sh
set -eu

HOST="${MQTT_HOST:-192.168.0.1}"
PORT="${MQTT_PORT:-1883}"
USER="${MQTT_USER:-victron}"
PASS="${MQTT_PASSWORD:-changeme}"

# Create HA discovery JSONs
mkdir -p /tmp/ha_disc

cat >/tmp/ha_disc/victron_health_sensor.json <<'JSON'
{
  "name": "Victron BLE Bridge Health",
  "unique_id": "victron_ble_health_sensor",
  "state_topic": "system/health/victron_ble",
  "icon": "mdi:heart-pulse",
  "entity_category": "diagnostic",
  "value_template": "{{ value.split(\":\" )[0] }}",
  "device": {"identifiers": ["victron_ble_bridge"], "name": "Victron BLE Bridge", "manufacturer": "ALFaQD", "model": "Victron BLE→MQTT"}
}
JSON

cat >/tmp/ha_disc/victron_health_problem.json <<'JSON'
{
  "name": "Victron BLE Problem",
  "unique_id": "victron_ble_problem",
  "state_topic": "system/health/victron_ble",
  "device_class": "problem",
  "entity_category": "diagnostic",
  "value_template": "{% set s = value.split(\":\" )[0] %}{% if s == \"WARN\" %}ON{% else %}OFF{% endif %}",
  "payload_on": "ON", "payload_off": "OFF",
  "device": {"identifiers": ["victron_ble_bridge"], "name": "Victron BLE Bridge", "manufacturer": "ALFaQD", "model": "Victron BLE→MQTT"}
}
JSON

cat >/tmp/ha_disc/wifi_health_sensor.json <<'JSON'
{
  "name": "WiFi AP Watchdog",
  "unique_id": "wifi_ap_watchdog_sensor",
  "state_topic": "system/watchdog/wifi_ap",
  "icon": "mdi:wifi",
  "entity_category": "diagnostic",
  "value_template": "{{ value.split(\":\" )[0] }}",
  "device": {"identifiers": ["victron_ble_bridge"], "name": "Victron BLE Bridge"}
}
JSON

cat >/tmp/ha_disc/wifi_health_problem.json <<'JSON'
{
  "name": "WiFi AP Problem",
  "unique_id": "wifi_ap_problem",
  "state_topic": "system/watchdog/wifi_ap",
  "device_class": "problem",
  "entity_category": "diagnostic",
  "value_template": "{% set s = value.split(\":\" )[0] %}{% if s == \"WARN\" %}ON{% else %}OFF{% endif %}",
  "payload_on": "ON", "payload_off": "OFF",
  "device": {"identifiers": ["victron_ble_bridge"], "name": "Victron BLE Bridge"}
}
JSON

# Publish discovery configs
mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -r \
  -t "homeassistant/sensor/victron_ble/health/config" -f /tmp/ha_disc/victron_health_sensor.json

mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -r \
  -t "homeassistant/binary_sensor/victron_ble/problem/config" -f /tmp/ha_disc/victron_health_problem.json

mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -r \
  -t "homeassistant/sensor/wifi_ap/health/config" -f /tmp/ha_disc/wifi_health_sensor.json

mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -r \
  -t "homeassistant/binary_sensor/wifi_ap/problem/config" -f /tmp/ha_disc/wifi_health_problem.json

# Keep container alive (original did `tail -f /dev/null`)
tail -f /dev/null
