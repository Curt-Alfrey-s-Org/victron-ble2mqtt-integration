#!/usr/bin/env bash
# DEPRECATED — use scripts/deploy.sh (Dockge + Compose stacks).
set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'TXT'
quick_start.sh — DEPRECATED

Use the unified installer instead:
  sudo bash scripts/deploy.sh

See DEPLOY.md for ENABLE_DOCKGE, ENABLE_TOOLS (Watchtower), and watchdog timers.
TXT
  exit 0
fi

echo >&2 ""
echo >&2 "DEPRECATED: scripts/quick_start.sh is unsupported."
echo >&2 "Run: sudo bash scripts/deploy.sh"
echo >&2 ""
exit 2
