#!/usr/bin/env bash
# Recreate victron_ble2mqtt container with env from .env and victron-secrets.env
# - Forces MQTT_HOST=localhost and uses MQTT_USER/PASSWORD from .env
# - Host networking, NET_ADMIN, same mounts as compose
set -euo pipefail

cd "$(dirname "$0")/.."

# Load env (provides MQTT_USER/MQTT_PASSWORD/MAIN_UID/PUBLISH_CONFIG_THROTTLE_SEC)
if [[ -f ./.env ]]; then set -a; . ./.env; set +a; fi

# Load secrets as env too (ADVKEY_*) so we can sanitize before passing to Docker
if [[ -f ./victron-secrets.env ]]; then set -a; . ./victron-secrets.env; set +a; fi

# Sanitize ADVKEY_* to 32 hex chars (strip non-hex, trim to 32)
sanitize_advkey() {
  local v="$1"; v="${v//[^0-9A-Fa-f]/}"; echo "${v:0:32}";
}
ADVKEY_BATTERY_1_SAN="$(sanitize_advkey "${ADVKEY_BATTERY_1:-}")"
ADVKEY_BATTERY_2_SAN="$(sanitize_advkey "${ADVKEY_BATTERY_2:-}")"
ADVKEY_SOLAR_CONTROLLER_SAN="$(sanitize_advkey "${ADVKEY_SOLAR_CONTROLLER:-}")"

# Ensure image
IMG="victron_ble2mqtt:local"
if ! docker image inspect "$IMG" >/dev/null 2>&1; then
  DOCKER_BUILDKIT=1 docker build -t "$IMG" .
fi

# Stop old container
docker rm -f victron_ble2mqtt >/dev/null 2>&1 || true

# Run fresh container
docker run -d --name victron_ble2mqtt --restart unless-stopped \
  --log-driver json-file --log-opt max-size=10m --log-opt max-file=5 \
  --network host --cap-add NET_ADMIN --privileged \
  --env-file ./victron-secrets.env \
  -e MQTT_HOST=localhost -e MQTT_PORT=1883 \
  -e MQTT_USER="${MQTT_USER:-}" -e MQTT_PASSWORD="${MQTT_PASSWORD:-}" \
  -e MAIN_UID="${MAIN_UID:-}" -e PUBLISH_CONFIG_THROTTLE_SEC="${PUBLISH_CONFIG_THROTTLE_SEC:-60}" \
  -e SYSTEM_POLL_THROTTLE_SEC="${SYSTEM_POLL_THROTTLE_SEC:-3}" \
  -e LOG_LEVEL="${LOG_LEVEL:-INFO}" \
  -e ADVKEY_BATTERY_1="${ADVKEY_BATTERY_1_SAN}" \
  -e ADVKEY_BATTERY_2="${ADVKEY_BATTERY_2_SAN}" \
  -e ADVKEY_SOLAR_CONTROLLER="${ADVKEY_SOLAR_CONTROLLER_SAN}" \
  -e PYTHONPATH=/work/override:/work \
  -v "$(pwd)/override":/work/override:ro \
  -v "$(pwd)/override/victron_ble2mqtt":/app/override/victron_ble2mqtt:ro \
  -v "$(pwd)/victron_ble2mqtt":/app/victron_ble2mqtt:ro \
  -v "$(pwd)/swarm":/work/swarm:ro \
  -v /var/log/victron_ble2mqtt.log:/logs/victron_ble2mqtt.log:rw \
  -v /run/dbus/system_bus_socket:/run/dbus/system_bus_socket:ro \
  -v /var/run/dbus:/var/run/dbus:ro \
  -v /var/lib/bluetooth:/var/lib/bluetooth:ro \
  "$IMG"

sleep 3
echo "Container env (MQTT_*)"
docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' victron_ble2mqtt | grep -E 'MQTT_HOST|MQTT_PORT|MQTT_USER|MQTT_PASSWORD' || true
