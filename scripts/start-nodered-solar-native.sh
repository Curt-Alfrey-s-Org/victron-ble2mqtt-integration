#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="$ROOT/nodered-runtime"
DATA="$ROOT/nodered-data"
if [[ ! -f "$ROOT/nodered.env" ]]; then
  echo "Missing nodered.env" >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source "$ROOT/nodered.env"
set +a
export PORT=1880
export NODE_RED_HOME="$DATA"
exec "$RUNTIME/bin/node" "$RUNTIME/app/node_modules/node-red/red.js" \
  --userDir "$DATA" \
  --settings "$DATA/settings.js"
