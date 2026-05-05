#!/usr/bin/env bash
# Copy victron pip wheels from TrueNAS hub into repo ./wheels for offline Docker builds.
#
# Default source: /mnt/cluster/wheels/victron (NFS mount of .111 .../wheels/victron).
# Usage:
#   bash scripts/sync-victron-wheels-from-hub.sh
#
# Env:
#   CLUSTER_WHEELS_VICTRON  — hub directory (default /mnt/cluster/wheels/victron)
#   CLUSTER_VICTRON_HUB_REQUIRED — if 1, exit non-zero when hub dir missing (default 0)
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${CLUSTER_WHEELS_VICTRON:-/mnt/cluster/wheels/victron}"
DST="${VICTRON_WHEELS_DST:-$ROOT_DIR/wheels}"

if [[ ! -d "$SRC" ]]; then
  echo "[sync-victron-wheels] Hub directory not found: $SRC" >&2
  if [[ "${CLUSTER_VICTRON_HUB_REQUIRED:-0}" == "1" ]]; then
    exit 1
  fi
  exit 0
fi

mkdir -p "$DST"
echo "[sync-victron-wheels] rsync $SRC/ -> $DST/"
rsync -a "${SRC}/" "${DST}/"

cnt="$(find "$DST" -maxdepth 1 -type f -name '*.whl' 2>/dev/null | wc -l)"
echo "[sync-victron-wheels] Local .whl count: $cnt"
