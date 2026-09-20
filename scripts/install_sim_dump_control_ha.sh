#!/usr/bin/env bash
# Install dump-load CONTROL package on .105 (HA owns switch on/off).
# Requires sim dump plugs already installed.
# Official packages: https://www.home-assistant.io/docs/configuration/packages/
# Container restart:
#   https://www.home-assistant.io/installation/linux#install-home-assistant-container
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/opt/homeassistant}"
PKG_SRC="$ROOT/config/packages/sim_dump_control.yaml"
PKG_DST="$HA_CONFIG_DIR/packages/sim_dump_control.yaml"
DASH_SRC="$ROOT/config/dashboards/solar-plant.yaml"
DASH_DST="$HA_CONFIG_DIR/dashboards/solar-plant.yaml"
PLUGS_DST="$HA_CONFIG_DIR/packages/sim_dump_plugs.yaml"
CONF="$HA_CONFIG_DIR/configuration.yaml"

if [[ ! -f "$PKG_SRC" ]]; then
  echo "Missing package source: $PKG_SRC" >&2
  exit 1
fi
if [[ ! -f "$PLUGS_DST" ]]; then
  echo "Install sim dump plugs first: bash scripts/install_sim_dump_plugs_ha.sh" >&2
  exit 1
fi

sudo mkdir -p "$HA_CONFIG_DIR/packages"
sudo cp "$PKG_SRC" "$PKG_DST"
sudo chown "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" "$PKG_DST" 2>/dev/null || true
echo "[sim-dump-control] Installed $PKG_DST"
if [[ -f "$DASH_SRC" && -f "$DASH_DST" ]]; then
  sudo cp "$DASH_SRC" "$DASH_DST"
  sudo chown "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" "$DASH_DST" 2>/dev/null || true
  echo "[sim-dump-control] Updated Solar plant dashboard $DASH_DST"
elif [[ -f "$DASH_SRC" ]]; then
  echo "[sim-dump-control] Solar plant dashboard not installed; run bash scripts/install_solar_plant_ha.sh"
fi

if [[ ! -f "$CONF" ]]; then
  echo "Missing $CONF" >&2
  exit 1
fi
if ! grep -qE 'include_dir_named packages' "$CONF"; then
  echo "[sim-dump-control] $CONF must include: homeassistant.packages: !include_dir_named packages" >&2
  exit 1
fi

if docker ps --format '{{.Names}}' | grep -qw homeassistant; then
  echo "[sim-dump-control] Restarting homeassistant container (reload package) ..."
  docker restart homeassistant
  echo "[sim-dump-control] Open http://192.168.0.105:8123/energy -- dump is Energy device Sim dump; knobs in Settings > Helpers"
else
  echo "[sim-dump-control] homeassistant container not running -- start HA, then restart."
fi
