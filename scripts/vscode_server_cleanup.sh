#!/usr/bin/env bash
set -euo pipefail

# Clean up stale VS Code Server processes to reclaim RAM.
# Kills .vscode-server processes older than a threshold when no active SSH session
# for this user is present. Also prunes stale lock/ipc files.
#
# Usage: vscode_server_cleanup.sh [AGE_SECS]
#   AGE_SECS default: ${CLEANUP_AGE_SECS:-900} (15 minutes)

AGE_SECS=${1:-${CLEANUP_AGE_SECS:-900}}
USER_NAME=${SUDO_USER:-${USER:-$(id -un)}}
HOME_DIR=$(getent passwd "$USER_NAME" | awk -F: '{print $6}')
[ -n "$HOME_DIR" ] || HOME_DIR="$HOME"

log() { echo "[vscode-cleanup] $*"; }

# Detect any active SSH sessions for this user (safety guard)
has_active_ssh=false
if pgrep -u "$USER_NAME" -fa sshd >/dev/null 2>&1; then
  has_active_ssh=true
fi

if $has_active_ssh; then
  log "Active SSH session(s) detected for user $USER_NAME; skipping cleanup."
  exit 0
fi

# Find candidate VS Code Server processes owned by the user
# We consider anything under ~/.vscode-server/bin/* and common server processes
candidates=$(ps -u "$USER_NAME" -o pid=,etimes=,%cpu=,cmd= \
  | awk -v age="$AGE_SECS" '(
      $0 ~ /\.vscode-server\/bin\/.*\/node/ ||
      $0 ~ /server-main\.js/ ||
      $0 ~ /extensionHost/ ||
      $0 ~ /watcherService/
    ) {
      pid=$1; et=$2; cpu=$3;
      if (et+0 > age && cpu+0 < 1.0) { print pid }
    }')

if [ -z "${candidates:-}" ]; then
  log "No stale VS Code Server processes found (age>${AGE_SECS}s, cpu<1%)."
else
  log "Killing stale VS Code Server PIDs: $candidates"
  # Try graceful first
  while read -r pid; do
    kill -TERM "$pid" 2>/dev/null || true
  done <<<"$candidates"
  sleep 2
  # Force kill any survivors
  while read -r pid; do
    if kill -0 "$pid" 2>/dev/null; then
      log "PID $pid still alive; sending SIGKILL"
      kill -KILL "$pid" 2>/dev/null || true
    fi
  done <<<"$candidates"
fi

# Prune stale lock/ipc files older than the threshold
find "$HOME_DIR/.vscode-server" -xdev \
  \( -name 'vscode-remote-lock.*' -o -name '.pid' -o -name 'ipc*' -o -name '*.sock' \) \
  -type s -o -type p -o -type f 2>/dev/null | while read -r f; do
  # Delete if older than threshold
  if [ "$(date +%s)" -gt $(( $(stat -c %Y "$f" 2>/dev/null || echo 0) + AGE_SECS )) ]; then
    rm -f "$f" 2>/dev/null || true
  fi
done

log "Cleanup complete."
