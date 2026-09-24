#!/usr/bin/env bash
# Native Node-RED on .105 when Docker Hub DNS is unavailable (LAN-only install).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="$ROOT/nodered-runtime"
DATA="$ROOT/nodered-data"
TARBALL_NODE="/tmp/node-v22.22.1-linux-x64.tar.xz"
TARBALL_MODULES="/tmp/nodered-linux-modules.tgz"
if [[ ! -f "$ROOT/nodered.env" ]]; then
  echo "Missing nodered.env. Run scripts/setup-nodered-solar-env.sh first." >&2
  exit 1
fi
if [[ ! -f "$TARBALL_NODE" ]] || [[ ! -f "$TARBALL_MODULES" ]]; then
  echo "Missing offline tarballs on .105: $TARBALL_NODE and $TARBALL_MODULES" >&2
  exit 1
fi
mkdir -p "$RUNTIME" "$DATA"
rm -rf "$RUNTIME/bin" "$RUNTIME/lib" "$RUNTIME/include" "$RUNTIME/share" "$RUNTIME/app"
tar xf "$TARBALL_NODE" -C "$RUNTIME" --strip-components=1
mkdir -p "$RUNTIME/app"
tar xzf "$TARBALL_MODULES" -C "$RUNTIME/app"
cp "$ROOT/flows/solar_plant_diagram.json" "$DATA/flows.json"
cp "$ROOT/nodered/settings.js" "$DATA/settings.js"
echo "Node-RED runtime installed under $RUNTIME"
echo "Start: bash scripts/start-nodered-solar-native.sh"
