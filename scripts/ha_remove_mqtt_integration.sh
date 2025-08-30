#!/usr/bin/env bash
# Remove existing MQTT integration entry from Home Assistant to allow clean re-add via UI.
# - Backs up /config/.storage/core.config_entries inside the container
# - Removes the first mqtt entry from entries array
# - Restarts HA (optional; default yes)
set -euo pipefail

HA_CONT=${HA_CONT:-homeassistant}
RESTART=${RESTART:-1}

if ! docker ps --format '{{.Names}}' | grep -qw "${HA_CONT}"; then
  echo "Home Assistant container (${HA_CONT}) is not running." >&2
  exit 1
fi

TS=$(date +%Y%m%d-%H%M%S)
FILE=/config/.storage/core.config_entries
BAK=/config/.storage/core.config_entries.bak-${TS}

echo "Backing up ${FILE} to ${BAK} ..."
docker exec "${HA_CONT}" bash -lc "cp -n '${FILE}' '${BAK}' && ls -l '${BAK}'"

echo "Removing MQTT integration entry ..."
docker exec -i "${HA_CONT}" python3 - <<'PY'
import json
from pathlib import Path
file=Path('/config/.storage/core.config_entries')
data=json.loads(file.read_text())
entries=data.get('data',{}).get('entries',[])
idx=None
for i,e in enumerate(entries):
    if e.get('domain')=='mqtt':
        idx=i; break
if idx is None:
    print('no mqtt entry found')
else:
    removed=entries.pop(idx)
    file.write_text(json.dumps(data, indent=2, sort_keys=True))
    print('removed mqtt entry titled:', removed.get('title'))
PY

if [[ "${RESTART}" == "1" ]]; then
  echo "Restarting ${HA_CONT} ..."
  docker restart "${HA_CONT}" >/dev/null
  echo "Restarted."
fi

echo "Done. You can now add the MQTT integration via the HA UI."
