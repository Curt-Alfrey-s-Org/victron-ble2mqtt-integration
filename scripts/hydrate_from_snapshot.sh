#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-$HOME/victron-ble2mqtt-integration}"
SWARM="$REPO/swarm"
SNAP="${SNAPSHOT_FILE:-}"
[[ -z "${SNAP}" ]] && SNAP="$(ls -1t "$SWARM"/input-snapshot_*.txt 2>/dev/null | head -n1 || true)"
[[ -n "${SNAP}" && -f "${SNAP}" ]] || { echo "No snapshot found. Aborting."; exit 1; }

HEALTH_ENV="$SWARM/health.env"
HADISC_ENV="$SWARM/ha-discovery.env"
DOZZLE_ENV="$SWARM/.env"
FILLED_DISC="$SWARM/ha-discovery-stack.filled.yml"

banner() { printf '\n=== %s ===\n' "$*"; }

# -------- helpers to extract from snapshot --------
first_match() { grep -E -m1 "$1" "$SNAP" | sed -E "s/$1/\1/"; } # (pattern must have a capture group)
val_or() { [[ -n "$1" ]] && printf '%s' "$1" || printf '%s' "$2"; }

extract_mosq_port() {
  awk '
    tolower($0) ~ /===== .*mosquitto.*\.conf =====/ { inmosq=1; next }
    /^===== / { inmosq=0 }
    inmosq && /^[[:space:]]*listener[[:space:]]+[0-9]+/ { print $2; exit }
  ' "$SNAP" 2>/dev/null | head -n1
}

extract_topic_vic() {
  # prefer a topic used by victron health publisher
  awk '
    tolower($0) ~ /===== .*victron-ble-health\.sh =====/ { in=1; next }
    /^===== / { in=0 }
    in && /mosquitto_pub/ && match($0, /-t '\''([^'\'']+)'\''/, m) { print m[1]; exit }
  ' "$SNAP" 2>/dev/null | head -n1
}

extract_topic_wifi() {
  awk '
    tolower($0) ~ /===== .*wifi-ap-watchdog\.sh =====/ { in=1; next }
    /^===== / { in=0 }
    in && /mosquitto_pub/ && match($0, /-t '\''([^'\'']+)'\''/, m) { print m[1]; exit }
  ' "$SNAP" 2>/dev/null | head -n1
}

extract_stale_secs_vic() {
  awk '
    tolower($0) ~ /===== .*victron-ble-health\.sh =====/ { in=1; next }
    /^===== / { in=0 }
    in && match($0, /^STALE_SECS=([0-9]+)/, m) { print m[1]; exit }
  ' "$SNAP" 2>/dev/null | head -n1
}

extract_hostname() {
  # from snapshot header line "Host: <name>"
  awk '
    /^### Victron/ { next }
    /^20[0-9-]{10}T/ { next }
    /^Host:/ { print $2; exit }
  ' "$SNAP" 2>/dev/null | head -n1
}

detect_host_ip() {
  ip -4 route get 1.1.1.1 2>/dev/null | awk '/src/ {for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}' | head -n1
}

extract_topic_root_from_usersettings() {
  # look for common names in user_settings.py dumped in snapshot
  awk '
    tolower($0) ~ /===== .*user_settings\.py =====/ { in=1; next }
    /^===== / { in=0 }
    in {
      if (match($0, /mqtt_topic_root\s*=\s*["'\'']([^"'\''#]+)["'\'']/, m)) { print m[1]; exit }
      if (match($0, /topic_root\s*=\s*["'\'']([^"'\''#]+)["'\'']/, m)) { print m[1]; exit }
      if (match($0, /base_topic\s*=\s*["'\'']([^"'\''#]+)["'\'']/, m)) { print m[1]; exit }
    }
  ' "$SNAP" 2>/dev/null | head -n1
}

# -------- derive values --------
LAN_IP="$(detect_host_ip)"
MOSQ_PORT="$(extract_mosq_port)"
TOPIC_VIC="$(extract_topic_vic)"
TOPIC_WIFI="$(extract_topic_wifi)"
STALE_VIC="$(extract_stale_secs_vic)"
HOSTNAME="$(extract_hostname)"
TOPIC_ROOT="$(extract_topic_root_from_usersettings)"

# sensible defaults/fallbacks
[[ -z "$LAN_IP" ]] && LAN_IP="192.168.0.123"
[[ -z "$MOSQ_PORT" ]] && MOSQ_PORT="1883"
[[ -z "$TOPIC_VIC" ]] && TOPIC_VIC="system/health/victron_ble"
[[ -z "$TOPIC_WIFI" ]] && TOPIC_WIFI="system/watchdog/wifi_ap"
[[ -z "$STALE_VIC" ]] && STALE_VIC="600"
[[ -z "$HOSTNAME" ]] && HOSTNAME="$(hostname)"
# if a topic_root exists, expose it (not overriding health/watchdog unless they match that scheme)
[[ -n "$TOPIC_ROOT" ]] && echo "Detected topic_root in user_settings.py: $TOPIC_ROOT"

banner "Detected (from snapshot)"
echo "LAN IP          : $LAN_IP"
echo "Mosquitto port  : $MOSQ_PORT"
echo "Victron topic   : $TOPIC_VIC"
echo "WiFi topic      : $TOPIC_WIFI"
echo "Stale secs      : $STALE_VIC"
echo "Hostname        : $HOSTNAME"

# -------- apply to env files (non-secret only) --------
apply_env_kv() {
  local file="$1" key="$2" val="$3"
  mkdir -p "$(dirname "$file")"
  touch "$file"
  if grep -qE "^${key}=" "$file"; then
    sed -i -E "s|^(${key}=).*|\1${val}|" "$file"
  else
    printf '%s=%s\n' "$key" "$val" >> "$file"
  fi
}

banner "Updating env files"
apply_env_kv "$HEALTH_ENV" MQTT_HOST "$LAN_IP"
apply_env_kv "$HEALTH_ENV" MQTT_PORT "$MOSQ_PORT"
apply_env_kv "$HEALTH_ENV" STALE_SECS "$STALE_VIC"
# wifi stale = same unless already set to something else
if ! grep -q '^STALE_SECS_WIFI=' "$HEALTH_ENV" 2>/dev/null; then
  apply_env_kv "$HEALTH_ENV" STALE_SECS_WIFI "$STALE_VIC"
fi
apply_env_kv "$HEALTH_ENV" TOPIC_VIC "$TOPIC_VIC"
apply_env_kv "$HEALTH_ENV" TOPIC_WIFI "$TOPIC_WIFI"

# mirror broker into HA discovery env
apply_env_kv "$HADISC_ENV" MQTT_HOST "$LAN_IP"
apply_env_kv "$HADISC_ENV" MQTT_PORT "$MOSQ_PORT"

banner "Result: $HEALTH_ENV"
cat "$HEALTH_ENV"
banner "Result: $HADISC_ENV"
cat "$HADISC_ENV"

# -------- optionally write a filled discovery stack with nicer device naming --------
banner "Writing filled HA discovery stack (non-secret): $FILLED_DISC"
cat > "$FILLED_DISC" <<YAML
version: "3.8"

services:
  ha_discovery_filled:
    image: efrecon/mqtt-client:latest
    env_file:
      - ha-discovery.env
    command:
      - sh
      - -c
      - |
        set -euo pipefail
        mkdir -p /tmp/ha_disc

        cat <<'JSON' > /tmp/ha_disc/victron_health_sensor.json
        {
          "name": "Victron BLE Bridge Health",
          "unique_id": "victron_ble_health_sensor_${HOSTNAME}",
          "state_topic": "${TOPIC_VIC}",
          "icon": "mdi:heart-pulse",
          "entity_category": "diagnostic",
          "value_template": "{{ value.split(\":\")[0] }}",
          "device": {
            "identifiers": ["victron_ble_bridge_${HOSTNAME}"],
            "name": "Victron BLE Bridge (${HOSTNAME})",
            "manufacturer": "ALFaQD",
            "model": "Victron BLE→MQTT"
          }
        }
        JSON

        cat <<'JSON' > /tmp/ha_disc/victron_health_problem.json
        {
          "name": "Victron BLE Problem",
          "unique_id": "victron_ble_problem_${HOSTNAME}",
          "state_topic": "${TOPIC_VIC}",
          "device_class": "problem",
          "entity_category": "diagnostic",
          "value_template": "{% set s = value.split(\":\" )[0] %}{% if s == \"WARN\" %}ON{% else %}OFF{% endif %}",
          "payload_on": "ON",
          "payload_off": "OFF",
          "device": {
            "identifiers": ["victron_ble_bridge_${HOSTNAME}"],
            "name": "Victron BLE Bridge (${HOSTNAME})",
            "manufacturer": "ALFaQD",
            "model": "Victron BLE→MQTT"
          }
        }
        JSON

        cat <<'JSON' > /tmp/ha_disc/wifi_health_sensor.json
        {
          "name": "WiFi AP Watchdog",
          "unique_id": "wifi_ap_watchdog_sensor_${HOSTNAME}",
          "state_topic": "${TOPIC_WIFI}",
          "icon": "mdi:wifi",
          "entity_category": "diagnostic",
          "value_template": "{{ value.split(\":\")[0] }}",
          "device": {
            "identifiers": ["victron_ble_bridge_${HOSTNAME}"],
            "name": "Victron BLE Bridge (${HOSTNAME})"
          }
        }
        JSON

        cat <<'JSON' > /tmp/ha_disc/wifi_health_problem.json
        {
          "name": "WiFi AP Problem",
          "unique_id": "wifi_ap_problem_${HOSTNAME}",
          "state_topic": "${TOPIC_WIFI}",
          "device_class": "problem",
          "entity_category": "diagnostic",
          "value_template": "{% set s = value.split(\":\" )[0] %}{% if s == \"WARN\" %}ON{% else %}OFF{% endif %}",
          "payload_on": "ON",
          "payload_off": "OFF",
          "device": {
            "identifiers": ["victron_ble_bridge_${HOSTNAME}"],
            "name": "Victron BLE Bridge (${HOSTNAME})"
          }
        }
        JSON

        # publish retained discovery configs
        mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASSWORD" -r \
          -t "homeassistant/sensor/victron_ble/health/config" -f /tmp/ha_disc/victron_health_sensor.json
        mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASSWORD" -r \
          -t "homeassistant/binary_sensor/victron_ble/problem/config" -f /tmp/ha_disc/victron_health_problem.json
        mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASSWORD" -r \
          -t "homeassistant/sensor/wifi_ap/health/config" -f /tmp/ha_disc/wifi_health_sensor.json
        mosquitto_pub -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASSWORD" -r \
          -t "homeassistant/binary_sensor/wifi_ap/problem/config" -f /tmp/ha_disc/wifi_health_problem.json

        tail -f /dev/null
    deploy:
      mode: replicated
      replicas: 1
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 0

networks:
  default:
    driver: overlay
YAML

banner "Filled stack written"
echo "$FILLED_DISC"
