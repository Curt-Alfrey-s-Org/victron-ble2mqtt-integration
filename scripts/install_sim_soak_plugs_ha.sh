#!/usr/bin/env bash
# Install simulated soak plug HA package on .105 (Home Assistant Container /opt/homeassistant).
# Does not start until operator runs this script.
# Official packages: https://www.home-assistant.io/docs/configuration/packages/
# Container restart after config change:
#   https://www.home-assistant.io/installation/linux#install-home-assistant-container
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/opt/homeassistant}"
PKG_SRC="$ROOT/config/packages/sim_soak_plugs.yaml"
PKG_DST="$HA_CONFIG_DIR/packages/sim_soak_plugs.yaml"
CONF="$HA_CONFIG_DIR/configuration.yaml"

if [[ ! -f "$PKG_SRC" ]]; then
  echo "Missing package source: $PKG_SRC" >&2
  exit 1
fi

sudo mkdir -p "$HA_CONFIG_DIR/packages"
sudo cp "$PKG_SRC" "$PKG_DST"
sudo chown "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" "$PKG_DST" 2>/dev/null || true
echo "[sim-soak] Installed $PKG_DST"

if [[ ! -f "$CONF" ]]; then
  echo "[sim-soak] Creating minimal $CONF with packages include ..."
  sudo tee "$CONF" >/dev/null <<YAML
default_config:

homeassistant:
  packages: !include_dir_named packages
YAML
else
  if ! grep -qE 'include_dir_named packages' "$CONF"; then
    if grep -q '^homeassistant:' "$CONF"; then
      echo "[sim-soak] Adding packages include to homeassistant: block ..."
      sudo sed -i '/^homeassistant:/a\  packages: !include_dir_named packages' "$CONF"
    else
      echo "[sim-soak] Appending homeassistant packages block ..."
      sudo tee -a "$CONF" >/dev/null <<YAML

homeassistant:
  packages: !include_dir_named packages
YAML
    fi
  fi
fi

if docker ps --format '{{.Names}}' | grep -qw homeassistant; then
  # HA Container: restart to load new package YAML (official install doc above).
  echo "[sim-soak] Restarting homeassistant container (reload package) ..."
  docker restart homeassistant
  echo "[sim-soak] Wait ~2 min, then verify: curl -fsS -H 'Authorization: Bearer <token>' http://127.0.0.1:8123/api/states/switch.sim_ac_plug_1"
else
  echo "[sim-soak] homeassistant container not running -- start HA, then restart or call homeassistant.restart."
fi
