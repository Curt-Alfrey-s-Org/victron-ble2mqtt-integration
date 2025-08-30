#!/usr/bin/env bash
# Bounded diagnostics for BLE, Docker, and MQTT with visible timeouts
# Usage: bash scripts/diag_ble_mqtt.sh

set -u

# Resolve repo root based on this script's location so sourcing works from any CWD
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SCRIPT_DIR%/scripts}"

DEFAULT_TIMEOUT="6s"
SCAN_TIMEOUT="8s"
MQTT_WAIT="4"  # seconds for mosquitto_sub -W

# Load MQTT auth if available (from repo-root)
AUTH_OPTS=()
MQTT_HOST="127.0.0.1"
MQTT_PORT="1883"
if [[ -f "${REPO_ROOT}/victron-secrets.env" ]]; then
  set -a; . "${REPO_ROOT}/victron-secrets.env"; set +a || true
fi
if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a; . "${REPO_ROOT}/.env"; set +a || true
fi
if [[ -n "${MQTT_USER:-}" && -n "${MQTT_PASSWORD:-}" ]]; then
  AUTH_OPTS=( -u "$MQTT_USER" -P "$MQTT_PASSWORD" )
fi
if [[ -n "${MQTT_HOST:-}" ]]; then MQTT_HOST="$MQTT_HOST"; fi
if [[ -n "${MQTT_PORT:-}" ]]; then MQTT_PORT="$MQTT_PORT"; fi

section() {
  echo
  echo "=== $1 ==="
}

run() {
  local TO="$1"; shift
  echo "> $*" | sed 's/^/> /'
  if timeout "$TO" bash -c "$*"; then
    :
  else
    local EC=$?
    if [[ $EC -eq 124 ]]; then
      echo "[TIMEOUT after $TO] $*"
    else
      echo "[EXIT $EC] $*"
    fi
  fi
}

ts() { date '+%F %T %Z'; }

echo "diag_ble_mqtt: $(ts)"

section "Bluetooth: service status"
run "$DEFAULT_TIMEOUT" "systemctl is-active bluetooth || true"
run "$DEFAULT_TIMEOUT" "systemctl status --no-pager bluetooth | sed -n '1,12p' || true"

section "rfkill"
run "$DEFAULT_TIMEOUT" "rfkill list || true"

section "hciconfig -a"
run "$DEFAULT_TIMEOUT" "hciconfig -a || true"

section "btmgmt info"
if command -v btmgmt >/dev/null 2>&1; then
  run "$DEFAULT_TIMEOUT" "sudo btmgmt -i hci0 info || true"
else
  echo "btmgmt not installed"
fi

section "bluetoothctl show"
run "$DEFAULT_TIMEOUT" "bluetoothctl show || true"

section "Ensure controller powered + LE on"
if command -v btmgmt >/dev/null 2>&1; then
  run "$DEFAULT_TIMEOUT" "sudo btmgmt -i hci0 power on || true"
  run "$DEFAULT_TIMEOUT" "sudo btmgmt -i hci0 le on || true"
else
  echo "btmgmt not installed"
fi

section "Short BLE scan (btmgmt find -l)"
if command -v btmgmt >/dev/null 2>&1; then
  OUT=$(timeout "$SCAN_TIMEOUT" sudo btmgmt -i hci0 find -l 2>&1 || true)
  RC=$?
  echo "$OUT"
  if echo "$OUT" | grep -q "status 0x0a (Busy)"; then
    echo "[NOTE] Controller is already scanning (Busy). This is OK if the app is scanning."
  elif [[ $RC -eq 124 ]]; then
    echo "[TIMEOUT after $SCAN_TIMEOUT] btmgmt find -l"
  fi
else
  echo "btmgmt not installed"
fi

section "Docker containers"
run "$DEFAULT_TIMEOUT" "docker ps --format '{{.Names}}\t{{.Status}}' || true"

section "victron_ble2mqtt logs (last 100)"
run "$DEFAULT_TIMEOUT" "docker logs --tail 100 victron_ble2mqtt 2>&1 | tail -n 100 || true"

section "MQTT: discovery samples"
if command -v mosquitto_sub >/dev/null 2>&1; then
  run "$DEFAULT_TIMEOUT" "mosquitto_sub -h $MQTT_HOST -p $MQTT_PORT ${AUTH_OPTS[*]} -t 'homeassistant/+/+/config' -C 2 -W $MQTT_WAIT -v || true"
else
  echo "mosquitto_sub not installed"
fi

section "MQTT: HA status + one device config + one state"
if command -v mosquitto_sub >/dev/null 2>&1; then
  run "$DEFAULT_TIMEOUT" "mosquitto_sub -h $MQTT_HOST -p $MQTT_PORT ${AUTH_OPTS[*]} -t 'homeassistant/status' -C 1 -W $MQTT_WAIT -v || true"
  run "$DEFAULT_TIMEOUT" "mosquitto_sub -h $MQTT_HOST -p $MQTT_PORT ${AUTH_OPTS[*]} -t 'homeassistant/sensor/raspberrypi/raspberrypi-wifi_device_name/config' -C 1 -W $MQTT_WAIT -v || true"
  # Try to sample any Victron device state if present (wildcards)
  run "$DEFAULT_TIMEOUT" "mosquitto_sub -h $MQTT_HOST -p $MQTT_PORT ${AUTH_OPTS[*]} -t 'homeassistant/sensor/+/+/state' -C 1 -W $MQTT_WAIT -v || true"
else
  echo "mosquitto_sub not installed"
fi

section "Broker port check (ss -lntp | 1883)"
run "$DEFAULT_TIMEOUT" "ss -lntp | grep ':$MQTT_PORT ' || true"

echo "done: $(ts)"
