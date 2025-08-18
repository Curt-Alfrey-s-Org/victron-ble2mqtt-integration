#!/usr/bin/env bash
set -euo pipefail

# Load device MACs from your secrets file
cd /home/n4s1/victron-ble2mqtt-integration
set -a; . swarm/victron-secrets.env; set +a
MAC_RE='\b('"$(echo "${VICTRON_DEVICE_KEYS:-}" \
  | tr ';' '\n' | cut -d= -f1 | paste -sd'|' -)"')\b'

# 1) Bluetooth powered?
if ! bluetoothctl show hci0 2>/dev/null | grep -q 'Powered: yes'; then
  systemctl restart bluetooth.service || true
  sleep 3
fi

# 2) Scanner running?
if ! bluetoothctl show hci0 2>/dev/null | grep -q 'Discovering: yes'; then
  systemctl restart victron-ble2mqtt.service || true
  sleep 2
fi

# 3) Are our devices heard recently? (gracefully skip if no keys set)
if [[ -n "${VICTRON_DEVICE_KEYS:-}" ]]; then
  if ! timeout 12s btmgmt -i hci0 find -l 2>/dev/null | egrep -iq "${MAC_RE}"; then
    # Kick BT stack and app if we stopped seeing adverts
    systemctl restart bluetooth.service || true
    sleep 3
    systemctl restart victron-ble2mqtt.service || true
  fi
fi
