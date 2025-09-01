#!/usr/bin/env bash
set -euo pipefail

# Purge stale retained MQTT discovery for our prefixes and restart publishers

BROKER_HOST=${MQTT_HOST:-127.0.0.1}
BROKER_PORT=${MQTT_PORT:-1883}
USER=${MQTT_USER:-}
PASS=${MQTT_PASSWORD:-}

AUTH_ARGS=()
[[ -n "$USER" ]] && AUTH_ARGS+=( -u "$USER" )
[[ -n "$PASS" ]] && AUTH_ARGS+=( -P "$PASS" )

prefixes=(
  # Main device and host sensors
  'homeassistant/sensor/1000/#'
  # Per-device (SmartShunt, SolarCharger) topics use the 1000-* prefix
  'homeassistant/sensor/1000-*/#'
)

echo "Collecting retained discovery topics to purge..."
mapfile -t topics < <(
  {
    for t in "${prefixes[@]}"; do
  # Intentionally DO receive retained messages (no -R) so we can purge them
  mosquitto_sub -h "$BROKER_HOST" -p "$BROKER_PORT" "${AUTH_ARGS[@]}" -t "$t" -v -W 2 || true
    done
  } | awk '{print $1}' | sort -u | grep '/config$' || true
)

if (( ${#topics[@]} > 0 )); then
  echo "Purging ${#topics[@]} retained config topics..."
  for tp in "${topics[@]}"; do
    mosquitto_pub -h "$BROKER_HOST" -p "$BROKER_PORT" "${AUTH_ARGS[@]}" -t "$tp" -r -n || true
  done
else
  echo "No matching retained config topics found to purge."
fi

echo "Restarting publishers (victron and HA) to republish fresh discovery..."
docker restart victron_ble2mqtt >/dev/null 2>&1 || true
docker restart homeassistant >/dev/null 2>&1 || true

echo "Done. Verify in HA (MQTT: Connected) and watch topics for states."
