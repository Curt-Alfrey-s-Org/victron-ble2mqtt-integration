#!/usr/bin/env bash
# Install solar package sensors + Energy wiring on .105 HA Container.
# Operator UI is built-in Energy / Home / Solar. Do not register YAML Lovelace.
# Official: https://www.home-assistant.io/docs/energy/
#           https://www.home-assistant.io/dashboards/dashboards/#home-assistant-built-in-dashboards
#           https://www.home-assistant.io/dashboards/dashboards/#adding-yaml-dashboards
#           https://www.home-assistant.io/docs/configuration/packages/
#           https://www.home-assistant.io/docs/configuration/troubleshooting/
#           https://www.home-assistant.io/installation/linux#install-home-assistant-container
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HA_CONFIG_DIR="${HA_CONFIG_DIR:-/opt/homeassistant}"
PKG_SRC="$ROOT/config/packages/solar_plant.yaml"
PKG_DST="$HA_CONFIG_DIR/packages/solar_plant.yaml"
DASH_DST="$HA_CONFIG_DIR/dashboards/solar-plant.yaml"
CONF="$HA_CONFIG_DIR/configuration.yaml"
UNREG="$ROOT/scripts/unregister_yaml_lovelace_dashboard.py"

if [[ ! -f "$PKG_SRC" ]]; then
  echo "Missing package source: $PKG_SRC" >&2
  exit 1
fi
if [[ ! -f "$UNREG" ]]; then
  echo "Missing $UNREG" >&2
  exit 1
fi
if [[ ! -f "$CONF" ]]; then
  echo "Missing $CONF" >&2
  exit 1
fi

sudo mkdir -p "$HA_CONFIG_DIR/packages"
sudo cp "$PKG_SRC" "$PKG_DST"
sudo chown "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" "$PKG_DST" 2>/dev/null || true
echo "[solar-plant] Installed $PKG_DST"

if ! grep -qE 'include_dir_named packages' "$CONF"; then
  echo "[solar-plant] $CONF must include: homeassistant.packages: !include_dir_named packages" >&2
  exit 1
fi

# YAML Lovelace is not UI-movable. Unregister if a prior install added it.
# https://www.home-assistant.io/dashboards/dashboards/#adding-yaml-dashboards
sudo python3 "$UNREG" "$CONF" solar-plant
if [[ -f "$DASH_DST" ]]; then
  sudo rm -f "$DASH_DST"
  echo "[solar-plant] Removed leftover YAML dashboard file $DASH_DST"
fi

if ! grep -q '^recorder:' "$CONF"; then
  echo "[solar-plant] Appending recorder + history (this HA has no default_config) ..."
  sudo tee -a "$CONF" >/dev/null <<'YAML'

recorder:
history:
YAML
fi

if ! grep -q '^energy:' "$CONF"; then
  echo "[solar-plant] Appending energy (default_config would have loaded it) ..."
  sudo tee -a "$CONF" >/dev/null <<'YAML'

energy:
YAML
fi

# Companion needs mobile_app when default_config is absent.
# Official: https://www.home-assistant.io/integrations/mobile_app/
# Do not add default_config: -- it also loads bluetooth/cloud/usb
# (https://www.home-assistant.io/integrations/default_config/).
if ! grep -q '^mobile_app:' "$CONF"; then
  echo "[solar-plant] Appending mobile_app (Companion; no default_config) ..."
  sudo tee -a "$CONF" >/dev/null <<'YAML'

mobile_app:
YAML
fi

KU_EST_SRC="$ROOT/config/packages/solar_ku_estimates.yaml"
KU_EST_DST="$HA_CONFIG_DIR/packages/solar_ku_estimates.yaml"
if [[ -f "$KU_EST_SRC" ]]; then
  sudo cp "$KU_EST_SRC" "$KU_EST_DST"
  sudo chown "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" "$KU_EST_DST" 2>/dev/null || true
  echo "[solar-plant] Installed $KU_EST_DST"
fi

DUMP_SRC="$ROOT/config/packages/sim_dump_control.yaml"
DUMP_DST="$HA_CONFIG_DIR/packages/sim_dump_control.yaml"
if [[ -f "$DUMP_DST" && -f "$DUMP_SRC" ]]; then
  sudo cp "$DUMP_SRC" "$DUMP_DST"
  sudo chown "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" "$DUMP_DST" 2>/dev/null || true
  echo "[solar-plant] Refreshed already-installed dump control $DUMP_DST"
fi

if docker ps --format '{{.Names}}' | grep -qw homeassistant; then
  echo "[solar-plant] check_config ..."
  docker exec homeassistant python -m homeassistant --script check_config -c /config
  echo "[solar-plant] Restarting homeassistant container ..."
  docker restart homeassistant
  echo "[solar-plant] Waiting for container health ..."
  i=0
  while [ "$i" -lt 36 ]; do
    st="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' homeassistant 2>/dev/null || true)"
    if [ "$st" = "healthy" ] || [ "$st" = "running" ]; then
      echo "[solar-plant] homeassistant is $st"
      break
    fi
    i=$((i + 1))
    sleep 5
  done
  echo "[solar-plant] Open http://192.168.0.105:8123/energy"
  echo "[solar-plant] Built-in Energy / Home / Solar are the operator UI (no YAML Lovelace)."
else
  echo "[solar-plant] homeassistant container not running -- start HA, then rerun this script."
  exit 1
fi
