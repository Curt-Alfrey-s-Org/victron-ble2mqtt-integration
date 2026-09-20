#!/usr/bin/env bash
# Retire solar-flow.service on .105 (custom SVG :8765).
# Canonical view: Home Assistant /energy (docs/SOLAR_HA_DASHBOARD.md).
# Official: https://www.freedesktop.org/software/systemd/man/systemctl.html
#           https://tailscale.com/kb/1242/tailscale-serve/#disable-tailscale-serve
#           https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html
set -euo pipefail

if systemctl list-unit-files --type=service 2>/dev/null | grep -q '^solar-flow.service'; then
  echo "[solar-flow] systemctl disable --now solar-flow.service"
  sudo systemctl disable --now solar-flow.service
elif systemctl is-active --quiet solar-flow.service 2>/dev/null; then
  echo "[solar-flow] stopping leftover unit"
  sudo systemctl disable --now solar-flow.service
else
  echo "[solar-flow] unit not installed (ok)"
fi

if [[ -f /etc/systemd/system/solar-flow.service ]]; then
  sudo rm -f /etc/systemd/system/solar-flow.service
  echo "[solar-flow] removed /etc/systemd/system/solar-flow.service"
fi
sudo systemctl daemon-reload
sudo systemctl reset-failed solar-flow.service 2>/dev/null || true

if command -v tailscale >/dev/null 2>&1; then
  if tailscale serve status 2>/dev/null | grep -q '127.0.0.1:8765'; then
    echo "[solar-flow] turning off Tailscale Serve proxy to :8765"
    sudo tailscale serve --https=443 --set-path=/ off
  else
    echo "[solar-flow] Tailscale Serve is not proxying :8765 (ok)"
  fi
fi

if command -v ufw >/dev/null 2>&1; then
  echo "[solar-flow] deleting ufw 8765 rules if present"
  n=0
  while [ "$n" -lt 8 ]; do
    line="$(sudo ufw status numbered | grep '8765' | head -n 1 || true)"
    if [ -z "$line" ]; then
      break
    fi
    num="$(printf '%s\n' "$line" | sed -n 's/^\[\s*\([0-9][0-9]*\).*/\1/p')"
    if [ -z "$num" ]; then
      break
    fi
    echo y | sudo ufw delete "$num"
    n=$((n + 1))
  done
fi

echo "[solar-flow] retired. Open http://192.168.0.105:8123/energy"
