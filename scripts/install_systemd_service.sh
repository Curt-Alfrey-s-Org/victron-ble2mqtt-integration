#!/usr/bin/env bash
set -euo pipefail

UNIT_SRC="$(cd "$(dirname "$0")/.." && pwd)/systemd/victron-ble2mqtt.service"
UNIT_DST="/etc/systemd/system/victron-ble2mqtt.service"

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "This installer must run as root. Try: sudo bash $0"
  exit 1
fi

echo "Installing systemd unit to ${UNIT_DST}"
install -m 0644 -D "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload
systemctl enable victron-ble2mqtt.service
systemctl restart victron-ble2mqtt.service

echo "Status:"
systemctl --no-pager status victron-ble2mqtt.service | sed -n '1,20p'
