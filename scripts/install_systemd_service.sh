#!/usr/bin/env bash
set -euo pipefail

echo "DEPRECATED: victron stacks are started by Docker Compose (via scripts/deploy.sh + Dockge)." >&2
echo "Do not install victron-ble2mqtt.service — run instead:" >&2
echo "  sudo bash scripts/deploy.sh" >&2
exit 2
