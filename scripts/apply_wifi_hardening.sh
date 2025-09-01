#!/usr/bin/env bash
set -euo pipefail

# Persist NetworkManager Wi‑Fi hardening, ensure regulatory domain, set route metrics
# and run a stability test using scripts/wifi_stability_test.sh.
#
# Usage:
#   sudo ./apply_wifi_hardening.sh [COUNTRY_CODE] [TEST_SECS]
#
# Defaults:
#   COUNTRY_CODE = US
#   TEST_SECS    = 600 (10 minutes)

COUNTRY_CODE=${1:-US}
TEST_SECS=${2:-600}

require_root() {
  if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "This script must run as root. Re-run with: sudo $0" >&2
    exit 1
  fi
}

write_nm_configs() {
  install -d -m 755 /etc/NetworkManager/conf.d
  cat > /etc/NetworkManager/conf.d/99-wifi-tuning.conf <<'EOF'
[connection]
wifi.cloned-mac-address=permanent
ethernet.cloned-mac-address=permanent

[wifi]
mac-address-randomization=0
scan-rand-mac-address=no

[device]
wifi.scan-rand-mac-address=no
EOF

  # Relax PMF requirements to avoid strict AP interactions triggering roam loops
  cat > /etc/NetworkManager/conf.d/10-wifi-pmf.conf <<'EOF'
[wifi]
pmf=1
pmf-required=0
EOF
}

ensure_wpa_country() {
  local wpa=/etc/wpa_supplicant/wpa_supplicant.conf
  if [ -f "$wpa" ]; then
    if ! grep -q '^country=' "$wpa"; then
      echo "country=${COUNTRY_CODE}" >> "$wpa"
    fi
  else
    printf 'country=%s\nap_scan=1\n' "${COUNTRY_CODE}" > "$wpa"
  fi
}

tune_connections() {
  # Prefer Ethernet via lower metrics; keep Wi‑Fi powersave off and relax PMF
  local wifi_name eth_name
  wifi_name=$(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="802-11-wireless"{print $1; exit}')
  eth_name=$(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="802-3-ethernet"{print $1; exit}')

  if [ -n "${wifi_name:-}" ]; then
    nmcli connection modify "$wifi_name" 802-11-wireless.powersave 2 || true
    nmcli connection modify "$wifi_name" 802-11-wireless.cloned-mac-address permanent || true
  # Try to set per-connection country (not all NM versions support this key)
  nmcli connection modify "$wifi_name" 802-11-wireless.country "${COUNTRY_CODE}" || true
  # Ensure basic WPA-PSK and relax PMF
  nmcli connection modify "$wifi_name" wifi-sec.key-mgmt wpa-psk || true
  nmcli connection modify "$wifi_name" wifi-sec.pmf 0 || true
    nmcli connection modify "$wifi_name" ipv4.route-metric 600 || true
    nmcli connection modify "$wifi_name" ipv6.route-metric 600 || true
  fi

  if [ -n "${eth_name:-}" ]; then
    nmcli connection modify "$eth_name" ipv4.route-metric 100 || true
    nmcli connection modify "$eth_name" ipv6.route-metric 100 || true
  fi
}

verify_and_restart_nm() {
  command -v iw >/dev/null 2>&1 && iw reg set "${COUNTRY_CODE}" || true
  systemctl restart NetworkManager || true
  sleep 3
  echo "--- nmcli device status ---"
  nmcli -t -f DEVICE,TYPE,STATE,CONNECTION dev status || true
  echo "--- iw reg get ---"
  iw reg get || true
  echo "--- iw link ---"
  iw dev wlan0 link || true
}

reconnect_wifi() {
  # Bring Wi‑Fi back up and wait for IP
  local wifi_name
  wifi_name=$(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="802-11-wireless"{print $1; exit}')
  if [ -z "${wifi_name:-}" ]; then
    echo "[WARN] No saved Wi‑Fi connection found to bring up."
    return 0
  fi
  echo "[INFO] Reconnecting Wi‑Fi: $wifi_name"
  nmcli connection up "$wifi_name" || true
  # Wait up to 60s for wlan0 to be connected with an IP
  for i in $(seq 1 60); do
    state=$(nmcli -t -f DEVICE,TYPE,STATE dev status | awk -F: '$1=="wlan0"{print $3}')
    if [ "$state" = "connected" ]; then
      ip -o -4 addr show dev wlan0 | grep -q 'inet ' && break || true
    fi
    sleep 1
  done
  echo "--- nmcli device status (post-reconnect) ---"
  nmcli -t -f DEVICE,TYPE,STATE,CONNECTION dev status || true
  # Disable device powersave explicitly at runtime
  if iw dev wlan0 info >/dev/null 2>&1; then
    iw dev wlan0 set power_save off || true
  fi
  # Reprint reg domain (PHY may adopt AP Country IE after association)
  echo "--- iw reg get (post-assoc) ---"
  iw reg get || true
  echo "--- iw link (post-assoc) ---"
  iw dev wlan0 link || true
}

run_stability_test() {
  local logdir="/var/log/wifi-hardening"
  install -d -m 755 "$logdir"
  local ts; ts=$(date +%Y%m%d_%H%M%S)
  local out="$logdir/wifi_stability_${ts}.log"
  echo "Running ${TEST_SECS}s Wi‑Fi stability test... logs: $out"
  if [ -x "$(dirname "$0")/wifi_stability_test.sh" ]; then
    "$(dirname "$0")/wifi_stability_test.sh" "${TEST_SECS}" | tee "$out"
  else
    echo "wifi_stability_test.sh not found or not executable" | tee -a "$out"
    return 1
  fi
}

main() {
  require_root
  write_nm_configs
  ensure_wpa_country
  tune_connections
  verify_and_restart_nm
  reconnect_wifi
  run_stability_test
}

main "$@"
