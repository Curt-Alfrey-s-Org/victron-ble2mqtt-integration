#!/usr/bin/env bash
# Install / refresh the Govee H5082 MQTT bridge unit on this Pi.
#
#   sudo bash scripts/install_h5082_bridge.sh --host pi4 [--dry-run]
#   sudo bash scripts/install_h5082_bridge.sh --host pi5 [--dry-run]
#
# Both Pis install the unit as h5082-mqtt.service. Per-host settings live in
# /home/n4s1/.config/h5082-bridge.env (outside git): H5082_PLUGS=<plug ids> and
# optionally H5082_ADAPTER=hciN. Pairing keys stay in /home/n4s1/.govee-h5082-keys
# (mode 600); this script never reads, copies, or prints them. It only checks the
# file exists with mode 600. It stops (before touching systemd) if the bridge venv
# cannot import bleak, paho.mqtt and dbus_fast. On pi5 it stops h5082-rssi-pi5 (the
# full bridge also publishes pi5 RSSI) and does not start the bridge until
# H5082_PLUGS is set.
set -euo pipefail

HOST=""
DRY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="${2:-}"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
case "$HOST" in
  pi4) UNIT_SRC="systemd/h5082-mqtt.service" ;;
  pi5) UNIT_SRC="systemd/h5082-mqtt-pi5.service" ;;
  *) echo "usage: $0 --host pi4|pi5 [--dry-run]" >&2; exit 2 ;;
esac

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_HOME="${H5082_HOME:-/home/n4s1}"
HOST_ENV="$USER_HOME/.config/h5082-bridge.env"
KEYS="$USER_HOME/.govee-h5082-keys"
UNIT_DST="/etc/systemd/system/h5082-mqtt.service"
VENV_PY="${H5082_VENV_PY:-$USER_HOME/govee-ble-venv/bin/python}"  # same as ExecStart

run() {
  if [[ "$DRY" == 1 ]]; then echo "+ $*"; else "$@"; fi
}

echo "host=$HOST unit=$UNIT_SRC -> $UNIT_DST"

# The unit runs $VENV_PY -m govee_h5082: it needs bleak, paho-mqtt and dbus-fast.
# (2026-09-28: the Pi 5 venv had paho-mqtt and dbus-fast but no bleak.)
if ! VERSIONS="$("$VENV_PY" -c 'import bleak, paho.mqtt, dbus_fast
from importlib.metadata import version as v
print("bleak", v("bleak"), "paho-mqtt", v("paho-mqtt"), "dbus-fast", v("dbus-fast"))' 2>&1)"; then
  echo "ERROR: $VENV_PY cannot import bleak / paho.mqtt / dbus_fast:" >&2
  echo "$VERSIONS" | tail -n 1 >&2
  echo "Fix (as n4s1, not root): $(dirname "$VENV_PY")/pip install bleak paho-mqtt" >&2
  if [[ "$DRY" != 1 ]]; then exit 1; fi
else
  echo "venv ok: $VERSIONS"
fi

if [[ ! -f "$KEYS" ]]; then
  echo "WARN: $KEYS is missing. Copy the key line(s) for this Pi's plugs first (see docs/H5082_MULTI_BRIDGE.md)." >&2
elif [[ "$(stat -c %a "$KEYS")" != "600" ]]; then
  echo "WARN: $KEYS is mode $(stat -c %a "$KEYS"); run: chmod 600 $KEYS" >&2
fi

if [[ ! -f "$HOST_ENV" ]]; then
  echo "creating $HOST_ENV (template; H5082_PLUGS left commented out)"
  if [[ "$DRY" != 1 ]]; then
    if [[ ! -d "$(dirname "$HOST_ENV")" ]]; then
      install -d -m 700 -o n4s1 -g n4s1 "$(dirname "$HOST_ENV")"
    fi
    cat > "$HOST_ENV" <<'TEMPLATE'
# Govee H5082 bridge settings for this Pi (not in git).
# H5082_PLUGS: the plug ids this Pi owns (last 4 hex of the MAC), comma separated.
# Each plug must be owned by exactly one Pi. Unset on the Pi 4 = owns every plug.
#H5082_PLUGS=82FB
# Adapter override (Pi 4 must stay hci1; Pi 5 default is hci0).
#H5082_ADAPTER=hci0
TEMPLATE
    chown n4s1:n4s1 "$HOST_ENV"
    chmod 600 "$HOST_ENV"
  fi
fi

run install -m 644 "$REPO/$UNIT_SRC" "$UNIT_DST"
run systemctl daemon-reload

if [[ "$HOST" == pi5 ]]; then
  if systemctl list-unit-files h5082-rssi-pi5.service >/dev/null 2>&1; then
    run systemctl disable --now h5082-rssi-pi5.service || true
  fi
  if ! grep -Eq '^[[:space:]]*H5082_PLUGS=[^[:space:]]' "$HOST_ENV" 2>/dev/null; then
    echo "Set H5082_PLUGS in $HOST_ENV (e.g. H5082_PLUGS=82FB), then:"
    echo "  sudo systemctl enable --now h5082-mqtt"
    run systemctl enable h5082-mqtt.service
    exit 0
  fi
fi

run systemctl enable h5082-mqtt.service
run systemctl restart h5082-mqtt.service
echo "check: journalctl -u h5082-mqtt -n 30   (expect OWNS ... and DISCOVERY)"
