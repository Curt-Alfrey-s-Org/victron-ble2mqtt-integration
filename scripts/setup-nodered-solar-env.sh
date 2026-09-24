#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
HA_TOKEN_FILE="${HA_TOKEN_FILE:-/home/ansible/alfa-ai/deploy/secrets/home-assistant/long-lived.token}"
NR_USER="${NR_ADMIN_USER:-n4s1}"
NR_PASS="${NR_ADMIN_PASSWORD:-}"
if [[ -z "$NR_PASS" ]]; then
  echo "Set NR_ADMIN_PASSWORD in the environment (not stored in git)." >&2
  exit 1
fi
if [[ ! -f "$HA_TOKEN_FILE" ]]; then
  echo "Missing HA token file: $HA_TOKEN_FILE" >&2
  exit 1
fi
token=$(tr -d '\n\r' < "$HA_TOKEN_FILE")
hash=$(NR_ADMIN_PASSWORD="$NR_PASS" python3 - <<'PY'
import bcrypt, os
pw = os.environ["NR_ADMIN_PASSWORD"].encode("utf-8")
print(bcrypt.hashpw(pw, bcrypt.gensalt(rounds=8)).decode("ascii"))
PY
)
umask 077
HA_TOKEN="$token" NR_HASH="$hash" NR_USER="$NR_USER" python3 - <<'PY'
import os
from pathlib import Path
lines = [
    "HA_BASE_URL=http://127.0.0.1:8123",
    "HA_LONG_LIVED_TOKEN=" + os.environ["HA_TOKEN"],
    "NR_ADMIN_USER=" + os.environ["NR_USER"],
    "NR_ADMIN_PASSWORD_HASH=" + os.environ["NR_HASH"],
    "TZ=America/Chicago",
]
Path("nodered.env").write_text("\n".join(lines) + "\n", encoding="utf-8")
os.chmod("nodered.env", 0o600)
PY
echo "Wrote nodered.env (mode 600). NR user: ${NR_USER}"
