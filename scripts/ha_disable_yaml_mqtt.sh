#!/usr/bin/env bash
# Disable YAML-based MQTT configuration in /opt/homeassistant so the UI integration can be added/configured.
set -euo pipefail

HA_CONFIG_DIR=${HA_CONFIG_DIR:-/opt/homeassistant}

conf="${HA_CONFIG_DIR}/configuration.yaml"
if [[ -f "${conf}" ]]; then
  if grep -qE '^mqtt:|mqtt: *!include' "${conf}"; then
    echo "Commenting out mqtt stanza in ${conf} ..."
    cp -a "${conf}" "${conf}.bak.$(date +%s)"
    # Comment out lines starting with 'mqtt:' or 'mqtt: !include'
    sed -i -e 's/^mqtt:/# mqtt:/' -e 's/^mqtt: *!include/# mqtt: !include/' "${conf}"
  else
    echo "No mqtt stanza found in ${conf}."
  fi
else
  echo "${conf} not found; skipping."
fi

mqtt_yaml="${HA_CONFIG_DIR}/mqtt.yaml"
if [[ -f "${mqtt_yaml}" ]]; then
  echo "Renaming ${mqtt_yaml} to disable YAML MQTT ..."
  mv -f "${mqtt_yaml}" "${mqtt_yaml}.disabled.$(date +%s)"
fi

echo "YAML MQTT disabled. Restart Home Assistant to apply."
