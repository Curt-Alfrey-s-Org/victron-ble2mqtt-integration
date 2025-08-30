#!/usr/bin/env bash
set -euo pipefail
# Sync nginx basic auth credentials for tools (Dozzle/Portainer) from .env
# Uses MQTT_USER/MQTT_PASSWORD by default.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
  echo ".env not found in $ROOT_DIR" >&2
  exit 1
fi

# shellcheck disable=SC2046
export $(grep -E '^(MQTT_USER|MQTT_PASSWORD)=' .env | xargs -d '\n')

USER_NAME=${MQTT_USER:-admin}
USER_PASS=${MQTT_PASSWORD:-admin}

if [ -z "${USER_NAME}" ] || [ -z "${USER_PASS}" ]; then
  echo "MQTT_USER or MQTT_PASSWORD not set in .env" >&2
  exit 1
fi

mkdir -p nginx
HASH=$(openssl passwd -apr1 "$USER_PASS")
printf "%s:%s\n" "$USER_NAME" "$HASH" > nginx/.htpasswd
chmod 640 nginx/.htpasswd || true

echo "Wrote nginx/.htpasswd for user '$USER_NAME' from .env"

# restart nginx container if running
if docker ps --format '{{.Names}}' | grep -q '^tools_nginx$'; then
  docker restart tools_nginx >/dev/null && echo "Restarted tools_nginx"
fi
