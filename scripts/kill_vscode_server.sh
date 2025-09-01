#!/usr/bin/env bash
set -euo pipefail

USER_NAME=${SUDO_USER:-${USER:-$(id -un)}}
log() { echo "[kill-vscode] $*"; }

pids=$(pgrep -u "$USER_NAME" -fa '.vscode-server' | awk '{print $1}' | sort -u)
if [ -z "${pids:-}" ]; then
  log "No VS Code Server processes found."
  exit 0
fi

log "Killing VS Code Server PIDs: $pids"
kill -TERM $pids 2>/dev/null || true
sleep 2
for pid in $pids; do
  if kill -0 "$pid" 2>/dev/null; then
    log "PID $pid still running, sending SIGKILL"
    kill -KILL "$pid" 2>/dev/null || true
  fi
done

log "Done."
