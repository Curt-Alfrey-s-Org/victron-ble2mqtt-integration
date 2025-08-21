#!/usr/bin/env bash
# quick_start.sh — quick, idempotent bootstrap for Raspberry Pi
# Usage:
#   cd /home/n4s1/victron-ble2mqtt-integration
#   ./scripts/quick_start.sh [--no-tools] [--use-ghcr]
# Options:
#   --no-tools   : don't start the tools stack (Portainer/Dozzle/nginx)
#   --use-ghcr   : pull prebuilt image from ghcr.io/curtalfrey/victron-ble2mqtt-integration:latest

set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

NO_TOOLS=0
USE_GHCR=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --no-tools) NO_TOOLS=1; shift ;;
    --use-ghcr) USE_GHCR=1; shift ;;
    -h|--help) sed -n '1,120p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
done

# Ensure docker available
if ! command -v docker >/dev/null; then
  echo "docker is required. Install Docker and re-run."
  exit 1
fi

if [ $USE_GHCR -eq 1 ]; then
  echo "Pulling prebuilt image from GHCR..."
  docker pull ghcr.io/curtalfrey/victron-ble2mqtt-integration:latest || true
  docker tag ghcr.io/curtalfrey/victron-ble2mqtt-integration:latest victron_ble2mqtt:local || true
else
  echo "Building local arm64 image (this may take a while)..."
  docker buildx create --use --name mybuilder || true
  docker buildx inspect --bootstrap || true
  docker buildx build --platform linux/arm64 -t victron_ble2mqtt:local --load .
fi

echo "Starting victron stack..."
docker compose -f docker-compose.victron.yml up -d --build

if [ $NO_TOOLS -eq 0 ]; then
  echo "Starting tools stack (Portainer, Dozzle, nginx, Watchtower)..."
  docker compose -f docker-compose.tools.yml up -d
fi

# Install runner + service (idempotent)
if [ -f systemd/victron-runner.sh ]; then
  echo "Installing runner to /usr/local/bin/victron-runner.sh (requires sudo)"
  sudo cp systemd/victron-runner.sh /usr/local/bin/victron-runner.sh
  sudo chmod +x /usr/local/bin/victron-runner.sh
fi

if [ -f systemd/victron.service ]; then
  echo "Installing systemd unit /etc/systemd/system/victron.service (requires sudo)"
  sudo cp systemd/victron.service /etc/systemd/system/victron.service
  sudo systemctl daemon-reload
  sudo systemctl enable --now victron.service
fi

# Optional: install tools unit if present
if [ -f systemd/victron-tools.service ] && [ $NO_TOOLS -eq 0 ]; then
  echo "Installing tools systemd unit /etc/systemd/system/victron-tools.service (requires sudo)"
  sudo cp systemd/victron-tools.service /etc/systemd/system/victron-tools.service || true
  sudo systemctl daemon-reload || true
  sudo systemctl enable --now victron-tools.service || true
fi

echo "Quick start complete. Check container status with:"
echo "  docker compose -f docker-compose.victron.yml ps"
if [ $NO_TOOLS -eq 0 ]; then
  echo "  docker compose -f docker-compose.tools.yml ps"
fi

echo "Check victron service logs: sudo journalctl -u victron.service -f"
