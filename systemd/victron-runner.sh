#!/usr/bin/env bash
# victron-runner.sh
# Long-running runner used by systemd to (re)create the container via our redeploy script
# and monitor its health. Avoids docker compose dependency.
set -euo pipefail

# Repo root (this file lives in systemd/ — never hardcode /home/user1; deploy only templates the .service).
_SCRIPT="${BASH_SOURCE[0]:-$0}"
WORKDIR="$(cd "$(dirname "$_SCRIPT")/.." && pwd)"
MAIN_SERVICE=victron_ble2mqtt

cd "$WORKDIR"

redeploy() {
  echo "[victron-runner] Redeploying ${MAIN_SERVICE} via scripts/redeploy_victron.sh" >&2
  bash "$WORKDIR/scripts/redeploy_victron.sh"
}

is_running() {
  docker ps --filter "name=${MAIN_SERVICE}" --format '{{.Names}}' | grep -q "^${MAIN_SERVICE}$"
}

health_status() {
  docker inspect --format='{{.State.Health.Status}}' "${MAIN_SERVICE}" 2>/dev/null || echo unknown
}

# Ensure container exists and is running
if ! is_running; then
  # Wait for Bluetooth adapter readiness to avoid early scanner failures
  echo "[victron-runner] Waiting for Bluetooth adapter (hci0) to be powered..." >&2
  for i in $(seq 1 20); do
    if bluetoothctl show | grep -q "Powered: yes"; then
      break
    fi
    sleep 1
  done
  redeploy
fi

# Monitor loop
while true; do
  sleep 10
  if ! is_running; then
    echo "[victron-runner] ${MAIN_SERVICE} not running; redeploying" >&2
    redeploy
    continue
  fi
  hs=$(health_status)
  case "$hs" in
    healthy)
      # all good
      ;;
    starting)
      # allow to settle
      ;;
    unhealthy|unknown)
      echo "[victron-runner] ${MAIN_SERVICE} health=$hs; redeploying" >&2
      docker rm -f "${MAIN_SERVICE}" >/dev/null 2>&1 || true
      redeploy
      ;;
  esac
done
