#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-$HOME/victron-ble2mqtt-integration}"
SWARM="$REPO/swarm"
mkdir -p "$SWARM"

# If SNAPSHOT_FILE env var is provided, use it; otherwise pick the latest
SNAP="${SNAPSHOT_FILE:-}"
if [[ -z "${SNAP}" ]]; then
  SNAP="$(ls -1t "$SWARM"/input-snapshot_*.txt 2>/dev/null | head -n1 || true)"
fi

detect_host() {
  # Primary LAN IPv4 (not loopback)
  local ip
  ip=$(ip -4 route get 1.1.1.1 2>/dev/null | awk '/src/ {for(i=1;i<=NF;i++) if ($i=="src") print $(i+1)}' | head -n1)
  [[ -n "$ip" ]] || ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  [[ -n "$ip" ]] || ip="127.0.0.1"
  printf '%s' "$ip"
}

extract_port_from_snapshot() {
  [[ -n "${SNAP:-}" && -f "$SNAP" ]] || { echo ""; return; }
  # First 'listener <port>' occurrence in mosquitto configs inside the snapshot
  awk '
    tolower($0) ~ /===== .*mosquitto.*\.conf =====/ { inmosq=1; next }
    /^===== / { inmosq=0 }
    inmosq && /^[[:space:]]*listener[[:space:]]+[0-9]+/ { print $2; exit }
  ' "$SNAP" 2>/dev/null | head -n1
}

set_kv() {
  local file="$1" key="$2" val="$3"
  touch "$file"
  if grep -qE "^${key}=" "$file"; then
    cp -f "$file" "${file}.bak.$(date +%s)"
    sed -i -E "s|^(${key}=).*|\1${val}|" "$file"
  else
    printf '%s=%s\n' "$key" "$val" >> "$file"
  fi
}

get_current_or_default() {
  local file="$1" key="$2" def="$3"
  if [[ -f "$file" ]] && grep -qE "^${key}=" "$file"; then
    awk -F= -v k="$key" '$1==k{print $2}' "$file" | tail -n1
  else
    printf '%s' "$def"
  fi
}

HEALTH_ENV="$SWARM/health.env"
HADISC_ENV="$SWARM/ha-discovery.env"

# Derive values (prefer existing; fill gaps from snapshot/fallbacks)
MQTT_HOST="$(get_current_or_default "$HEALTH_ENV" MQTT_HOST "")"
[[ -z "$MQTT_HOST" || "$MQTT_HOST" == "127.0.0.1" || "$MQTT_HOST" == "192.168.0.123" ]] && MQTT_HOST="$(detect_host)"

MQTT_PORT="$(get_current_or_default "$HEALTH_ENV" MQTT_PORT "")"
if [[ -z "$MQTT_PORT" || "$MQTT_PORT" == "1883" ]]; then
  PORT_SNAP="$(extract_port_from_snapshot)"
  [[ -n "$PORT_SNAP" ]] && MQTT_PORT="$PORT_SNAP" || MQTT_PORT="1883"
fi

MQTT_USER="$(get_current_or_default "$HEALTH_ENV" MQTT_USER "victron")"
MQTT_PASSWORD="$(get_current_or_default "$HEALTH_ENV" MQTT_PASSWORD "replace_me_now")"

# Write consistent values to both env files (preserve custom user/pass if already set)
for ENVF in "$HEALTH_ENV" "$HADISC_ENV"; do
  set_kv "$ENVF" MQTT_HOST "$MQTT_HOST"
  set_kv "$ENVF" MQTT_PORT "$MQTT_PORT"

  CURU="$(get_current_or_default "$ENVF" MQTT_USER "")"
  if [[ -z "$CURU" || "$CURU" == "victron" ]]; then
    set_kv "$ENVF" MQTT_USER "$MQTT_USER"
  fi

  CURP="$(get_current_or_default "$ENVF" MQTT_PASSWORD "")"
  if [[ -z "$CURP" || "$CURP" == "changeme" || "$CURP" == "replace_me_now" ]]; then
    set_kv "$ENVF" MQTT_PASSWORD "$MQTT_PASSWORD"
  fi
done

echo "Snapshot used: ${SNAP:-<none found>}"
echo
echo "--- $HEALTH_ENV ---"
cat "$HEALTH_ENV"
echo
echo "--- $HADISC_ENV ---"
cat "$HADISC_ENV"
