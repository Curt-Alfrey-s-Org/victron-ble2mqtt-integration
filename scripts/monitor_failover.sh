#!/usr/bin/env bash
set -euo pipefail

# Simple loop: if eth0 loses carrier/default route, ensure wlan0 is up and has default route

ETH=eth0
WLAN=wlan0

# Load .env if running from repo (best-effort)
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
if [[ -f "$REPO_DIR/.env" ]]; then
  # shellcheck disable=SC1090
  set -a; . "$REPO_DIR/.env"; set +a
fi

SSID=${WIFI_SSID:-}
PSK=${WIFI_PASSWORD:-}

log() { echo "[failover] $(date +'%Y-%m-%d %H:%M:%S') $*"; }

ensure_wlan_up() {
  if command -v nmcli >/dev/null 2>&1; then
    sudo systemctl enable --now NetworkManager >/dev/null 2>&1 || true
    sudo nmcli radio wifi on >/dev/null 2>&1 || true
    sudo nmcli dev set "$WLAN" managed yes >/dev/null 2>&1 || true
    if [[ -n "$SSID" ]]; then
      if ! nmcli -t -f NAME connection show | grep -Fxq "$SSID"; then
        sudo nmcli con add type wifi ifname "$WLAN" con-name "$SSID" ssid "$SSID" || true
      fi
      [[ -n "$PSK" ]] && sudo nmcli con modify "$SSID" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK" || true
      sudo nmcli con modify "$SSID" connection.autoconnect yes || true
      sudo nmcli dev disconnect "$WLAN" >/dev/null 2>&1 || true
      sudo nmcli con up "$SSID" ifname "$WLAN" >/dev/null 2>&1 || true
    else
      # Try existing wifi connection
      conn=$(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="802-11-wireless"{print $1; exit}')
      if [[ -n "$conn" ]]; then
        sudo nmcli con modify "$conn" connection.autoconnect yes || true
        sudo nmcli dev disconnect "$WLAN" >/dev/null 2>&1 || true
        sudo nmcli con up "$conn" ifname "$WLAN" >/dev/null 2>&1 || true
      fi
    fi
  else
    # Fallback to wpa_supplicant + dhclient
    sudo systemctl enable --now wpa_supplicant@"$WLAN".service >/dev/null 2>&1 || true
    sudo dhclient -nw "$WLAN" >/dev/null 2>&1 || true
  fi
}

ensure_metrics() {
  # Prefer eth0 when up; otherwise allow wlan0 to own default route
  if command -v nmcli >/dev/null 2>&1; then
    ethc=$(nmcli -t -f NAME,DEVICE connection show | awk -F: -v d="$ETH" '$2==d{print $1; exit}')
    [[ -n "$ethc" ]] && sudo nmcli con modify "$ethc" ipv4.route-metric 100 >/dev/null 2>&1 || true
    conw=$(nmcli -t -f NAME,DEVICE connection show | awk -F: -v d="$WLAN" '$2==d{print $1; exit}')
    [[ -n "$conw" ]] && sudo nmcli con modify "$conw" ipv4.route-metric 600 >/dev/null 2>&1 || true
  elif systemctl list-unit-files | grep -q '^dhcpcd\.service'; then
    DC=/etc/dhcpcd.conf
    sudo grep -q "^interface $ETH$" "$DC" 2>/dev/null || echo -e "\ninterface $ETH\n  metric 100" | sudo tee -a "$DC" >/dev/null
    sudo grep -q "^interface $WLAN$" "$DC" 2>/dev/null || echo -e "\ninterface $WLAN\n  metric 600" | sudo tee -a "$DC" >/dev/null
    sudo systemctl restart dhcpcd >/dev/null 2>&1 || true
  fi
}

while true; do
  eth_carrier=$(cat /sys/class/net/$ETH/carrier 2>/dev/null || echo 0)
  has_default=$(ip route | awk '/^default/{print 1; exit}')
  if [[ "$eth_carrier" -eq 0 || -z "$has_default" ]]; then
    log "eth0 down or no default route; asserting Wi‑Fi"
    ensure_wlan_up
    ensure_metrics
    ip route show || true
  fi
  sleep 5
done
