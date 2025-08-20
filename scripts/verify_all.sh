#!/usr/bin/env bash
set -euo pipefail

SWARM="$PWD/victron-ble2mqtt-integration/swarm"

show() {
  local p="$1"
  echo
  echo "==================== ${p} ===================="
  if [[ -f "$p" ]]; then
    nl -ba "$p"
  else
    echo "<missing>"
  fi
}

echo "Repo: $PWD"
echo "Swarm dir: $SWARM"

# show latest snapshot path (for reference)
SNAP="$(ls -1t "$SWARM"/input-snapshot_*.txt 2>/dev/null | head -n1 || true)"
echo
echo "Latest snapshot: ${SNAP:-<none found>}"

# list swarm contents
echo
echo "----- ls -l swarm/ -----"
ls -l "$SWARM" || true

# show all expected files
show "$SWARM/.env"
show "$SWARM/devices.list"

# snapshot previews (robust via Python)
if [[ -f "$SNAP" ]]; then
  echo
  echo "----- snapshot: user_settings.py block (first 80 lines) -----"
  python3 - "$SNAP" <<'PY'
import sys, re
snap = sys.argv[1]
txt = open(snap, 'r', errors='ignore').read()
m = re.search(r"^===== .*user_settings\.py =====\n(.*?)(?=^===== |\Z)", txt, flags=re.S|re.M)
block = (m.group(1) if m else "").splitlines()
for i, line in enumerate(block[:80], 1):
    print(f"{i:4d}  {line}")
PY

  echo
  echo "----- snapshot: mosquitto listeners (up to 5) -----"
  python3 - "$SNAP" <<'PY'
import sys, re
snap = sys.argv[1]
txt = open(snap, 'r', errors='ignore').read()
# Find each mosquitto *.conf block and list 'listener <port>' lines
for blk in re.findall(r"^===== .*mosquitto.*\.conf =====\n(.*?)(?=^===== |\Z)", txt, flags=re.S|re.M):
    for line in blk.splitlines():
        if re.match(r"\s*listener\s+\d+", line):
            print(line.strip())
PY
fi
