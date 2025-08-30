#!/usr/bin/env bash
set -euo pipefail

echo "== zram swap setup (lz4, size = RAM/2), disable disk swap, swappiness=15 =="

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "This script must run as root. Try: sudo bash $0"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update -y -qq
apt-get install -y -qq systemd-zram-generator || true

CONF="/etc/systemd/zram-generator.conf"
echo "Writing ${CONF}"
cat >"${CONF}" <<'CONF'
[zram0]
compression-algorithm = lz4
zram-size = ram / 2
swap-priority = 100
CONF
chmod 0644 "${CONF}"

echo "Disabling on-disk swap (if any)"
if systemctl list-unit-files | grep -q '^dphys-swapfile\.service'; then
  systemctl disable --now dphys-swapfile.service || true
fi
swapoff -a || true
rm -f /var/swap /var/swapfile || true

if [ -f /etc/fstab ]; then
  echo "Backing up and commenting /var/swap entries in /etc/fstab"
  cp /etc/fstab "/etc/fstab.bak.$(date +%s)"
  sed -i 's|^/var/swapfile|# /var/swapfile|' /etc/fstab || true
  sed -i 's|^/var/swap|# /var/swap|' /etc/fstab || true
fi

echo "Reloading systemd and starting zram swap"
systemctl daemon-reload || true
# Prefer the generator-produced unit; fall back to setup service if needed
systemctl start dev-zram0.swap 2>/dev/null || systemctl start systemd-zram-setup@zram0.service 2>/dev/null || true

echo "Setting vm.swappiness=15"
echo 'vm.swappiness=15' > /etc/sysctl.d/99-swappiness.conf
sysctl -p /etc/sysctl.d/99-swappiness.conf || true

echo
echo "== Verification =="
echo "-- /etc/systemd/zram-generator.conf --"
sed -n '1,120p' /etc/systemd/zram-generator.conf || true
echo
echo "-- swapon --show --"
swapon --show || true
echo
if command -v zramctl >/dev/null 2>&1; then
  echo "-- zramctl --"
  zramctl || true
fi
echo
echo "-- vm.swappiness --"
sysctl -n vm.swappiness || true
echo
echo "If zram swap is not listed above yet, reboot once to finalize activation."
