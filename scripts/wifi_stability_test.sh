#!/usr/bin/env bash
set -euo pipefail

# Wi‑Fi stability test: pings public and gateway from a wlan interface and prints summaries.
# Usage: wifi_stability_test.sh [duration_seconds=120] [iface]

DURATION="${1:-120}"
IFACE_INPUT="${2:-}"

if ! command -v ip >/dev/null 2>&1; then
  echo "ip command not found" >&2; exit 1
fi

pick_iface() {
  local want="$1"
  if [ -n "$want" ]; then
    echo "$want"; return 0
  fi
  ip -o addr show up scope global \
    | awk -F'[ :/]+' '$2 ~ /^wlan[0-9]+$/ {print $2; exit}'
}

IFACE=$(pick_iface "$IFACE_INPUT")
if [ -z "${IFACE:-}" ]; then
  echo "No active wlan interface with an IP found" >&2; exit 1
fi

START_ISO=$(date -Is)
echo "Wi‑Fi interface: $IFACE"
ip -brief addr show dev "$IFACE"

if command -v iw >/dev/null 2>&1; then
  echo "--- iw link (before) ---"
  iw dev "$IFACE" link || true
fi

GATEWAY=$(ip route show dev "$IFACE" | awk '$1=="default" {print $3; exit}')
if [ -n "${GATEWAY:-}" ]; then
  echo "Gateway: $GATEWAY"
else
  echo "Gateway: (not found for $IFACE)"
fi

TMPDIR=$(mktemp -d)
PUB_OUT="$TMPDIR/ping_public.txt"
GW_OUT="$TMPDIR/ping_gw.txt"

echo "Starting ${DURATION}s ping tests at $START_ISO ..."

# -n numeric, -I iface, -i 1s interval, -c count, -w deadline
ping -n -I "$IFACE" -i 1 -c "$DURATION" -w "$DURATION" 1.1.1.1 >"$PUB_OUT" 2>&1 & PID1=$!
if [ -n "${GATEWAY:-}" ]; then
  ping -n -I "$IFACE" -i 1 -c "$DURATION" -w "$DURATION" "$GATEWAY" >"$GW_OUT" 2>&1 & PID2=$!
else
  PID2=""; GW_OUT="";
fi

wait "$PID1" || true
[ -n "$PID2" ] && wait "$PID2" || true

END_ISO=$(date -Is)
echo "Completed at $END_ISO"

echo "==== Public (1.1.1.1) ping summary ===="
tail -n 5 "$PUB_OUT" || true

if [ -n "$GW_OUT" ] && [ -s "$GW_OUT" ]; then
  echo "==== Gateway ($GATEWAY) ping summary ===="
  tail -n 5 "$GW_OUT" || true
fi

echo "==== Recent kernel Wi‑Fi messages (since $START_ISO) ===="
if dmesg --since "$START_ISO" >/dev/null 2>&1; then
  dmesg --since "$START_ISO" | sed -n '/wlan\|brcm\|brcmfmac\|wifi/Ip' || true
else
  dmesg | tail -n 200 | sed -n '/wlan\|brcm\|brcmfmac\|wifi/Ip' | tail -n 80 || true
fi

if command -v iw >/dev/null 2>&1; then
  echo "--- iw link (after) ---"
  iw dev "$IFACE" link || true
fi

echo "(Raw outputs in $TMPDIR)"
