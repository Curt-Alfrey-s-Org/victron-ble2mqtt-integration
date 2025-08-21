#!/usr/bin/env bash
set -euo pipefail
# deploy_local.sh
# Builds the image and starts the stack using docker compose (recommended)
# Usage: ./scripts/deploy_local.sh [--compose-file docker-compose.victron.yml]

COMPOSE_FILE=${1:-docker-compose.victron.yml}
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "Using compose file: $COMPOSE_FILE"

# Ensure .env exists (do not commit secrets)
if [[ ! -f .env ]]; then
  echo ".env file not found in repo root. Create one with MQTT_* and ADVKEY_* values before running."
  exit 1
fi

# Prefer docker compose; support both `docker compose` and legacy `docker-compose` if installed
if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    echo "Building and bringing up with docker compose..."
    docker compose -f "$COMPOSE_FILE" up --build -d
  elif command -v docker-compose >/dev/null 2>&1; then
    echo "Building and bringing up with docker-compose..."
    docker-compose -f "$COMPOSE_FILE" up --build -d
  else
    echo "Docker installed but compose plugin not found. Attempting docker build + docker run fallback."
    docker build -t victron_ble2mqtt:local .
    echo "Run with: docker run --rm --network host -e MQTT_HOST=... victron_ble2mqtt:local"
  fi
else
  echo "docker command not found. Install Docker and retry on your host."
  exit 2
fi

echo "Deployment requested. To follow logs: docker logs -f victron_ble2mqtt" 
