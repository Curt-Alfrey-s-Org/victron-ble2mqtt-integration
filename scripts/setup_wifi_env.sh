#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

find_from_nm() {
  local conn ssid psk file
  if ! command -v nmcli >/dev/null 2>&1; then
    return 1
  fi
  # Prefer active wlan0 connection; else any Wi‑Fi connection
  conn=$(nmcli -t -f DEVICE,STATE,CONNECTION device | awk -F: '$1=="wlan0"{print $3; exit}')
  if [[ -z "${conn:-}" ]]; then
    conn=$(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="802-11-wireless"{print $1; exit}')
  fi
  # Try nmcli fields first
  if [[ -n "${conn:-}" ]]; then
    ssid=$(nmcli -s -g 802-11-wireless.ssid connection show "$conn" 2>/dev/null || true)
    psk=$(nmcli -s -g 802-11-wireless-security.psk connection show "$conn" 2>/dev/null || true)
    # If secret not available via nmcli, read from system-connections file
  if [[ -z "${psk:-}" ]]; then
      file=$(LC_ALL=C sudo grep -rl "^id=${conn}$" /etc/NetworkManager/system-connections 2>/dev/null | head -n1 || true)
      if [[ -n "${file:-}" ]]; then
        ssid=${ssid:-$(LC_ALL=C sudo awk -F= '/^ssid=/{print $2; exit}' "$file" || true)}
        psk=${psk:-$(LC_ALL=C sudo awk -F= '/^psk=/{print $2; exit}' "$file" || true)}
      fi
  fi
  fi
  if [[ -n "${ssid:-}" ]]; then
    echo "$ssid"; echo "${psk:-}"
    return 0
  fi
  return 1
}

find_from_wpa() {
  local conf ssid psk
  for conf in /etc/wpa_supplicant/wpa_supplicant-wlan0.conf /etc/wpa_supplicant/wpa_supplicant.conf; do
    [[ -r "$conf" ]] || continue
    ssid=$(awk -F= '/^[[:space:]]*ssid=/{gsub(/"/,"",$2); print $2; exit}' "$conf" || true)
    psk=$(awk -F= '/^[[:space:]]*psk=/{gsub(/"/,"",$2); print $2; exit}' "$conf" || true)
    if [[ -n "${ssid:-}" ]]; then
      echo "$ssid"; echo "${psk:-}"
      return 0
    fi
  done
  return 1
}

# Try sources in order
SSID=""; PSK=""
vals=()
if mapfile -t vals < <(find_from_nm); then
  if (( ${#vals[@]} >= 1 )); then SSID=${vals[0]}; fi
  if (( ${#vals[@]} >= 2 )); then PSK=${vals[1]}; fi
elif mapfile -t vals < <(find_from_wpa); then
  if (( ${#vals[@]} >= 1 )); then SSID=${vals[0]}; fi
  if (( ${#vals[@]} >= 2 )); then PSK=${vals[1]}; fi
else
  echo "Could not locate Wi‑Fi settings from NetworkManager or wpa_supplicant." >&2
  exit 1
fi

if [[ -z "${SSID}" ]]; then
  echo "SSID not found." >&2
  exit 2
fi

# Write into .env (backup first)
[[ -f .env ]] && cp .env .env.bak-$(date +%Y%m%d-%H%M%S)
sanitize() { printf "%s" "$1" | sed "s/'/'\\''/g"; }
SSID_Q=$(sanitize "$SSID"); PSK_Q=$(sanitize "${PSK}")
grep -vE '^(WIFI_SSID|WIFI_PASSWORD)=' .env 2>/dev/null > .env.tmp || true
{
  echo "WIFI_SSID='${SSID_Q}'"
  echo "WIFI_PASSWORD='${PSK_Q}'"
} >> .env.tmp
mv .env.tmp .env

# If NM present, ensure profile autoconnect is enabled
if command -v nmcli >/dev/null 2>&1; then
  if ! nmcli -t -f NAME connection show | grep -Fxq "$SSID"; then
    sudo nmcli con add type wifi ifname wlan0 con-name "$SSID" ssid "$SSID" || true
  fi
  if [[ -n "${PSK}" ]]; then
    sudo nmcli con modify "$SSID" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK" || true
  fi
  sudo nmcli con modify "$SSID" connection.autoconnect yes || true
fi

echo "Updated .env with WIFI_SSID='${SSID}' and WIFI_PASSWORD='********'"
