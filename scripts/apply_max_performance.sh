#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Installing performance/tuning units and rules..."

# Install systemd services
sudo install -m 0644 -D "$ROOT_DIR/systemd/wlan-power-save-off.service" /etc/systemd/system/wlan-power-save-off.service
sudo install -m 0644 -D "$ROOT_DIR/systemd/cpu-performance.service" /etc/systemd/system/cpu-performance.service
sudo install -m 0644 -D "$ROOT_DIR/systemd/ethernet-performance.service" /etc/systemd/system/ethernet-performance.service

# Install udev rule
sudo install -m 0644 -D "$ROOT_DIR/udev/99-usb-autosuspend-off.rules" /etc/udev/rules.d/99-usb-autosuspend-off.rules

echo "Reloading systemd and udev..."
sudo systemctl daemon-reload
sudo udevadm control --reload-rules

echo "Enabling services for boot..."
sudo systemctl enable --now wlan-power-save-off.service || true
sudo systemctl enable --now cpu-performance.service || true
sudo systemctl enable --now ethernet-performance.service || true

echo "Applying settings immediately..."
# Wi‑Fi PS off (best-effort)
if command -v iw >/dev/null 2>&1; then
  sudo iw dev wlan0 set power_save off || true
fi

# CPU governor performance now
for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
  [ -w "$gov" ] && echo performance | sudo tee "$gov" >/dev/null || true
done

# Ethernet tuning now
if command -v ethtool >/dev/null 2>&1; then
  sudo ethtool --set-eee eth0 eee off || true
  sudo ethtool -K eth0 tso off gso off gro off lro off || true
fi
sudo ip link set dev eth0 txqueuelen 1000 || true

echo "Max performance settings applied."
