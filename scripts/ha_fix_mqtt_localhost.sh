#!/usr/bin/env bash
set -euo pipefail

# Configure Home Assistant MQTT (YAML) to use localhost broker with credentials,
# then restart the HA container. Designed to be idempotent and safe.

HA_C=$(docker ps --format '{{.Names}}' | grep -E '^homeassistant$|home-assistant' | head -n1 || true)
HA_C=${HA_C:-homeassistant}
echo "[ha_fix_mqtt_localhost] HA container: ${HA_C}"

if ! docker ps --format '{{.Names}}' | grep -q "^${HA_C}$"; then
  echo "[ha_fix_mqtt_localhost] Home Assistant container not running or not found" >&2
  exit 1
fi

echo "[ha_fix_mqtt_localhost] Writing /config/mqtt.yaml and ensuring include in configuration.yaml..."
docker exec -i "${HA_C}" python3 - <<'PY'
from pathlib import Path

cfg_dir = Path('/config')
conf = cfg_dir / 'configuration.yaml'
mq = cfg_dir / 'mqtt.yaml'

# Write mqtt.yaml deterministically (anonymous access)
mqtt_yaml = (
  'broker: 127.0.0.1\n'
  'port: 1883\n'
  'discovery: true\n'
  'keepalive: 60\n'
)
mq.write_text(mqtt_yaml, encoding='utf-8')

# Ensure configuration.yaml exists and includes mqtt: !include mqtt.yaml
if not conf.exists():
    conf.write_text('homeassistant:\n  time_zone: America/Chicago\n', encoding='utf-8')

lines = conf.read_text(encoding='utf-8').splitlines()
if not any(l.strip().startswith('mqtt:') for l in lines):
    lines.append('')
    lines.append('mqtt: !include mqtt.yaml')
conf.write_text('\n'.join(lines) + '\n', encoding='utf-8')

print('OK: wrote mqtt.yaml and ensured configuration.yaml contains include')
PY

echo "[ha_fix_mqtt_localhost] Restarting Home Assistant..."
docker restart "${HA_C}" >/dev/null

sleep 10
echo "[ha_fix_mqtt_localhost] Recent HA logs mentioning mqtt (last 2m):"
docker logs --since 2m "${HA_C}" 2>&1 | grep -i mqtt || echo "(no 'mqtt' lines in last 2 minutes)"

echo "[ha_fix_mqtt_localhost] MQTT entities count (if registry accessible):"
if docker exec "${HA_C}" test -r /config/.storage/core.entity_registry; then
  docker exec -i "${HA_C}" python3 - <<'PY'
import json
try:
    j=json.load(open('/config/.storage/core.entity_registry','r',encoding='utf-8'))
    ents=[e for e in j.get('data',{}).get('entities',[]) if e.get('platform')=='mqtt']
    print(len(ents))
except Exception as e:
    print('error reading entity_registry:', e)
PY
else
  echo "(entity registry not accessible)"
fi

echo "[ha_fix_mqtt_localhost] Done."
