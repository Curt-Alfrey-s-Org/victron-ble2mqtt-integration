#!/usr/bin/env bash
set -euo pipefail

# Switch current Wi‑Fi SSID to 2.4 GHz (bg band), pin to strongest 2.4G BSSID, reconnect,
# verify frequency, and run a 10-minute stability test.

TEST_SECS=${1:-600}
LOGDIR=/var/log/wifi-hardening

require() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1" >&2; exit 1; }; }
require nmcli
require iw
require ip

sudo true >/dev/null 2>&1 || { echo "This script requires sudo privileges." >&2; exit 1; }

WIFI_NAME=$(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="802-11-wireless"{print $1; exit}')
if [ -z "${WIFI_NAME:-}" ]; then echo "No Wi‑Fi connection profile found in NetworkManager." >&2; exit 1; fi

# Try to read SSID from current link; fall back to profile name
SSID=$(iw dev wlan0 link 2>/dev/null | awk -F': ' '/SSID:/ {print $2; exit}')
[ -z "${SSID:-}" ] && SSID="$WIFI_NAME"

echo "Profile: $WIFI_NAME | SSID: $SSID"

nmcli dev wifi rescan ifname wlan0 || true

# Find strongest 2.4 GHz BSSID for SSID
BEST_LINE=$(nmcli -t -f BSSID,SSID,FREQ,SIGNAL dev wifi list ifname wlan0 | \
  awk -F: -v ssid="$SSID" 'BEGIN{bestSig=-100} {
    bssid=$1; s=$2; freq=$3+0; sig=$4+0;
    if (s==ssid && freq>0 && freq<2500) { if (sig>bestSig) {bestSig=sig; bestB=bssid; bestF=freq; bestS=sig;} }
  } END { if (bestSig>-100) printf("%s %d %d\n", bestB, bestF, bestS); }')

if [ -z "${BEST_LINE:-}" ]; then echo "No 2.4 GHz BSSID found for SSID '$SSID'" >&2; exit 2; fi
BSSID=$(echo "$BEST_LINE" | awk '{print $1}')
FREQ=$(echo "$BEST_LINE" | awk '{print $2}')
SIG=$(echo "$BEST_LINE" | awk '{print $3}')
echo "Selected 2.4 GHz BSSID: $BSSID (${FREQ}MHz, signal ${SIG})"

echo "Applying band=bg and BSSID pin"
nmcli connection modify "$WIFI_NAME" 802-11-wireless.band bg || true
nmcli connection modify "$WIFI_NAME" 802-11-wireless.bssid "$BSSID"

echo "Reconnecting $WIFI_NAME"
nmcli connection down "$WIFI_NAME" || true
nmcli connection up "$WIFI_NAME"

sleep 3
iw dev wlan0 link || true

if ! iw dev wlan0 link | awk '/freq:/ {print $2}' | awk '{exit !($1>0 && $1<2500)}'; then
  echo "[WARN] Still not on 2.4 GHz after reconnect. Check AP config or SSID band availability." >&2
fi

sudo install -d -m 755 "$LOGDIR"
OUT="$LOGDIR/wifi_stability_$(date +%Y%m%d_%H%M%S)_2g.log"
echo "Starting ${TEST_SECS}s 2.4 GHz stability test -> $OUT"
nohup bash "$(dirname "$0")/wifi_stability_test.sh" "$TEST_SECS" > "$OUT" 2>&1 & echo $! | sudo tee "$LOGDIR/pid_2g_test.txt" >/dev/null
sleep 2
head -n 20 "$OUT" || true
