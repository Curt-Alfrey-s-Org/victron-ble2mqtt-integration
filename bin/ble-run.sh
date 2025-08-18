#!/usr/bin/env bash
set -euo pipefail
cd /home/n4s1/victron-ble2mqtt-integration
set -a
. swarm/ha-discovery.env
. swarm/victron-secrets.env
set +a
export PYTHONPATH="$PWD/override:$PWD/fixes:$PWD"
exec python3 - <<'PY'
from victron_ble2mqtt.cli_app.mqtt import publish_loop
publish_loop(verbosity=2)  # INFO
PY
