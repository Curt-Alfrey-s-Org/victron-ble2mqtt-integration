#!/usr/bin/env bash
# Install the dump-load CONTROL package on .105 (HA owns on/off of the H5082 dump sockets).
# Removes the retired sim_dump_control.yaml / sim_dump_plugs.yaml copies (they share
# helper ids with dump_control.yaml and would collide).
# Needs the per-socket "use" selects first: python3 scripts/create_h5082_socket_labels.py
# That script also appends the Use option "Sungold charge" without changing the current value.
# Run it after this install, once HA is up, with HA_TOKEN_FILE pointing at ~/.ha_token.
# Official packages: https://www.home-assistant.io/docs/configuration/packages/
# Container restart:
#   https://www.home-assistant.io/installation/linux#install-home-assistant-container
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/opt/homeassistant}"
PKG_SRC="$ROOT/config/packages/dump_control.yaml"
PKG_DST="$HA_CONFIG_DIR/packages/dump_control.yaml"
CONF="$HA_CONFIG_DIR/configuration.yaml"

if [[ ! -f "$PKG_SRC" ]]; then
  echo "Missing package source: $PKG_SRC" >&2
  exit 1
fi
if [[ ! -f "$CONF" ]]; then
  echo "Missing $CONF" >&2
  exit 1
fi
if ! grep -qE 'include_dir_named packages' "$CONF"; then
  echo "[dump-control] $CONF must include: homeassistant.packages: !include_dir_named packages" >&2
  exit 1
fi

sudo mkdir -p "$HA_CONFIG_DIR/packages"
for old in sim_dump_control.yaml sim_dump_plugs.yaml; do
  if [[ -f "$HA_CONFIG_DIR/packages/$old" ]]; then
    sudo rm -f "$HA_CONFIG_DIR/packages/$old"
    echo "[dump-control] Removed retired $HA_CONFIG_DIR/packages/$old"
  fi
done
sudo cp "$PKG_SRC" "$PKG_DST"
sudo chown "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" "$PKG_DST" 2>/dev/null || true
echo "[dump-control] Installed $PKG_DST"

if docker ps --format '{{.Names}}' | grep -qw homeassistant; then
  echo "[dump-control] check_config ..."
  docker exec homeassistant python -m homeassistant --script check_config -c /config
  echo "[dump-control] Restarting homeassistant container (reload package) ..."
  docker restart homeassistant
  echo "[dump-control] Set Use = dump on the sockets HA may switch (Site solar > Plugs), pick each one's inverter, then turn on Dump load HA control."
else
  echo "[dump-control] homeassistant container not running -- start HA, then restart."
fi
