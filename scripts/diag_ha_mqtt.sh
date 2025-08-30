#!/usr/bin/env bash
# Bounded diagnostics for Home Assistant MQTT integration
# - Checks HA container health
# - Reads MQTT integration config from /config/.storage/core.config_entries
# - Samples MQTT birth topic (homeassistant/status)
# Usage: bash scripts/diag_ha_mqtt.sh

set -u

DEFAULT_TIMEOUT="8s"
MQTT_WAIT="5"  # seconds for mosquitto_sub -W

section() { echo; echo "=== $1 ==="; }

run() {
  local TO="$1"; shift
  echo "> $*" | sed 's/^/> /'
  if timeout "$TO" bash -lc "$*"; then
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
echo "diag_ha_mqtt: $(ts)"

section "Home Assistant container status"
run "$DEFAULT_TIMEOUT" "docker ps --format '{{.Names}}\t{{.Status}}' | grep -E '^homeassistant\b' || true"
run "$DEFAULT_TIMEOUT" "docker inspect -f '{{.State.Health.Status}}' homeassistant 2>/dev/null || echo 'no healthcheck'"

section "HA HTTP check (localhost:8123 in container)"
run "$DEFAULT_TIMEOUT" "docker exec homeassistant bash -lc 'curl -fsS http://localhost:8123/manifest.json | jq -r .version 2>/dev/null || curl -fsS http://localhost:8123/ >/dev/null && echo ok' || true"

section "MQTT integration entry in core.config_entries"
PYTMP=$(mktemp)
cat > "$PYTMP" <<'PY'
import json, sys
p = "/config/.storage/core.config_entries"
try:
  with open(p, "r") as f:
    data = json.load(f)
except Exception as e:
  print("read_failed:", e)
  sys.exit(0)
entries = [e for e in data.get("data", {}).get("entries", []) if e.get("domain") == "mqtt"]
if not entries:
  print("no_mqtt_integration")
  sys.exit(0)
for e in entries:
  d = e.get("data", {})
  print("status", e.get("state"))
  print("broker", d.get("broker"))
  print("port", d.get("port"))
  print("username", d.get("username"))
  print("birth_message", (d.get("birth_message", {}) or {}).get("topic"))
PY
run "$DEFAULT_TIMEOUT" "docker cp '$PYTMP' homeassistant:/tmp/ha_mqtt_diag.py && docker exec homeassistant python3 /tmp/ha_mqtt_diag.py || true"
run "$DEFAULT_TIMEOUT" "docker exec homeassistant rm -f /tmp/ha_mqtt_diag.py || true"
rm -f "$PYTMP"

section "MQTT birth topic sample (homeassistant/status)"
# Try to read HA birth on local broker; use creds if present in env files
AUTH_OPTS=()
MQTT_HOST="127.0.0.1"; MQTT_PORT="1883";
if [[ -f "./victron-secrets.env" ]]; then set -a; . ./victron-secrets.env; set +a || true; fi
if [[ -f "./.env" ]]; then set -a; . ./.env; set +a || true; fi
if [[ -n "${MQTT_USER:-}" && -n "${MQTT_PASSWORD:-}" ]]; then AUTH_OPTS=( -u "$MQTT_USER" -P "$MQTT_PASSWORD" ); fi
if command -v mosquitto_sub >/dev/null 2>&1; then
  run "$DEFAULT_TIMEOUT" "mosquitto_sub -h ${MQTT_HOST} -p ${MQTT_PORT} ${AUTH_OPTS[*]} -t 'homeassistant/status' -C 1 -W ${MQTT_WAIT} -v || true"
else
  echo "mosquitto_sub not installed"
fi

echo "done: $(ts)"
