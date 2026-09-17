#!/usr/bin/env bash
# Install simulated dump-load plug HA package on .105 (Home Assistant Container /opt/homeassistant).
# Does not start until operator runs this script.
# Official packages: https://www.home-assistant.io/docs/configuration/packages/
# Container restart after config change:
#   https://www.home-assistant.io/installation/linux#install-home-assistant-container
# Template unique_id + default_entity_id:
#   https://www.home-assistant.io/integrations/template/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/opt/homeassistant}"
PKG_SRC="$ROOT/config/packages/sim_dump_plugs.yaml"
PKG_DST="$HA_CONFIG_DIR/packages/sim_dump_plugs.yaml"
LEGACY_DST="$HA_CONFIG_DIR/packages/sim_soak_plugs.yaml"
CONF="$HA_CONFIG_DIR/configuration.yaml"

if [[ ! -f "$PKG_SRC" ]]; then
  echo "Missing package source: $PKG_SRC" >&2
  exit 1
fi

sudo mkdir -p "$HA_CONFIG_DIR/packages"
sudo cp "$PKG_SRC" "$PKG_DST"
sudo chown "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" "$PKG_DST" 2>/dev/null || true
if [[ -f "$LEGACY_DST" ]]; then
  sudo rm -f "$LEGACY_DST"
  echo "[sim-dump] Removed leftover $LEGACY_DST"
fi
echo "[sim-dump] Installed $PKG_DST"

if [[ ! -f "$CONF" ]]; then
  echo "[sim-dump] Creating minimal $CONF with packages include ..."
  sudo tee "$CONF" >/dev/null <<YAML
default_config:

homeassistant:
  packages: !include_dir_named packages
YAML
else
  if ! grep -qE 'include_dir_named packages' "$CONF"; then
    if grep -q '^homeassistant:' "$CONF"; then
      echo "[sim-dump] Adding packages include to homeassistant: block ..."
      sudo sed -i '/^homeassistant:/a\  packages: !include_dir_named packages' "$CONF"
    else
      echo "[sim-dump] Appending homeassistant packages block ..."
      sudo tee -a "$CONF" >/dev/null <<YAML

homeassistant:
  packages: !include_dir_named packages
YAML
    fi
  fi
fi

if docker ps --format '{{.Names}}' | grep -qw homeassistant; then
  # HA Container: restart to load new package YAML (official install doc above).
  echo "[sim-dump] Restarting homeassistant container (reload package) ..."
  docker restart homeassistant
  echo "[sim-dump] Wait ~2 min, then verify: curl -fsS -H 'Authorization: Bearer <token>' http://127.0.0.1:8123/api/states/switch.sim_ac_plug_1"
  echo "[sim-dump] Aggregate sensor is sensor.sim_dump_load_power. Remove leftover sensor.sim_soak_load_power in Settings > Entities if it remains (changing unique_id registers a new entity; HA has no in-place unique_id rename API)."
else
  echo "[sim-dump] homeassistant container not running -- start HA, then restart or call homeassistant.restart."
fi
