#!/usr/bin/env bash
# Smoke-test BMS supervisor read-only VE.Direct -> MQTT sidecar (run on Pi after USB connected).
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f ./.env ]]; then set -a; . ./.env; set +a; fi

: "${MQTT_HOST:=127.0.0.1}"
: "${MQTT_PORT:=1883}"
: "${BMS_MQTT_TOPIC:=bms_supervisor}"
: "${BMS_ADAPTER:=generic_shunt}"
: "${BMS_SERIAL_DEVICE:=/dev/vedirect}"

fail=0
ok() { echo "[smoke] OK: $*"; }
warn() { echo "[smoke] WARN: $*" >&2; }
die() { echo "[smoke] FAIL: $*" >&2; fail=1; }

echo "[smoke] BMS supervisor sidecar smoke test"

if [[ -e "$BMS_SERIAL_DEVICE" || -e /dev/vedirect ]]; then
  ok "serial device present (${BMS_SERIAL_DEVICE} or /dev/vedirect)"
else
  die "no serial device -- plug VE.Direct USB and set BMS_SERIAL_DEVICE in .env"
fi

if docker ps --format '{{.Names}}' | grep -qw bms_supervisor; then
  ok "container bms_supervisor running"
  status="$(docker inspect -f '{{.State.Health.Status}}' bms_supervisor 2>/dev/null || echo unknown)"
  echo "[smoke] health: ${status}"
  if [[ "$status" == "unhealthy" ]]; then
    warn "container unhealthy -- check docker logs bms_supervisor (shunt may not be sending Text yet)"
  fi
else
  die "container bms_supervisor not running -- ENABLE_BMS_SUPERVISOR=1 && sudo bash scripts/deploy.sh"
fi

if [[ -n "${MQTT_USER:-}" && -n "${MQTT_PASSWORD:-}" ]]; then
  if mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASSWORD" \
    -t "${BMS_MQTT_TOPIC}/${BMS_ADAPTER}/voltage/state" -C 1 -W 15 -v 2>/dev/null; then
    ok "MQTT state topic received (${BMS_MQTT_TOPIC}/${BMS_ADAPTER}/voltage/state)"
  else
    warn "no MQTT state within 15s -- shunt off or VE.Direct not streaming Text yet"
  fi

  disc_topic="homeassistant/sensor/${BMS_MQTT_TOPIC}-${BMS_ADAPTER}-voltage/config"
  if mosquitto_sub -h "$MQTT_HOST" -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASSWORD" \
    -t "$disc_topic" -C 1 -W 5 2>/dev/null | grep -q unique_id; then
    ok "HA discovery config present for voltage"
  else
    warn "HA discovery not seen yet (container may still be starting)"
  fi
else
  warn "MQTT_USER/MQTT_PASSWORD unset -- skip broker subscribe checks"
fi

if [[ "$fail" -ne 0 ]]; then
  echo "[smoke] FAILED -- see docs/PI4_BMS_SOFTWARE.md"
  exit 1
fi

echo "[smoke] PASSED (or WARN-only if shunt not yet online)"
exit 0
