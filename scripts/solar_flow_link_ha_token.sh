#!/usr/bin/env bash
# Locate an existing Home Assistant long-lived token on the operator host and
# copy it to the path solar-flow expects.
#
# Destination (canonical for solar-flow / systemd unit):
#   /opt/homeassistant/secrets/ha_long_lived.token
#
# Search order (first non-empty wins; never prints token contents):
#   1. Dest already present and non-empty → no-op
#   2. HA_TOKEN_FILE / HA_LONG_LIVED_TOKEN_FILE env (if they point at a readable file)
#   3. HA_TOKEN env (write value to dest)
#   4. Known token files under /opt/homeassistant and /home/ansible
#   5. Env files that may hold HA_TOKEN= or HA_TOKEN_FILE= (host105-ai.env, alfa-ai .env, …)
#   6. Shallow find of *.token under /opt/homeassistant and /home/ansible
#
# Usage (on web-sites / .105):
#   sudo bash scripts/solar_flow_link_ha_token.sh
#   # or: sudo bash scripts/solar_flow_enable_tailscale.sh  (calls this first)
#
# Security: never echo the token; at most "copied N chars from PATH → DEST".

set -euo pipefail

DEST="${SOLAR_FLOW_HA_TOKEN_DEST:-/opt/homeassistant/secrets/ha_long_lived.token}"
# Optional override for tests: colon-separated extra roots for find (default below).
SEARCH_ROOTS="${SOLAR_FLOW_HA_TOKEN_SEARCH_ROOTS:-/opt/homeassistant:/home/ansible}"

die() { echo "FAIL: $*" >&2; exit 1; }

# Strip quotes / CR; never print the value.
_normalize_token() {
  local raw="$1"
  raw="${raw#"${raw%%[![:space:]]*}"}"
  raw="${raw%"${raw##*[![:space:]]}"}"
  raw="${raw%$'\r'}"
  if [[ "$raw" == \"*\" && "$raw" == *\" ]]; then
    raw="${raw:1:${#raw}-2}"
  elif [[ "$raw" == \'*\' && "$raw" == *\' ]]; then
    raw="${raw:1:${#raw}-2}"
  fi
  printf '%s' "$raw"
}

_token_len() {
  printf '%s' "$1" | wc -c | tr -d '[:space:]'
}

_dest_ok() {
  [[ -f "$DEST" ]] || return 1
  local body
  body="$(_normalize_token "$(cat "$DEST" 2>/dev/null || true)")"
  [[ -n "$body" ]]
}

_install_token_text() {
  local token="$1" source_label="$2"
  local n
  n="$(_token_len "$token")"
  [[ "$n" -gt 0 ]] || return 1
  mkdir -p "$(dirname "$DEST")"
  # Atomic write via temp in same dir; mode 600; never log contents.
  local tmp
  tmp="$(mktemp "$(dirname "$DEST")/.ha_token.XXXXXX")"
  printf '%s\n' "$token" >"$tmp"
  chmod 600 "$tmp"
  mv -f "$tmp" "$DEST"
  chmod 600 "$DEST"
  echo "[solar-flow] copied ${n} chars from ${source_label} → ${DEST}"
}

_try_token_file() {
  local path="$1"
  [[ -n "$path" && -f "$path" ]] || return 1
  # Skip if already the dest (caller handles dest-ok).
  if [[ "$(readlink -f "$path" 2>/dev/null || echo "$path")" == "$(readlink -f "$DEST" 2>/dev/null || echo "$DEST")" ]]; then
    return 1
  fi
  local body
  body="$(_normalize_token "$(cat "$path" 2>/dev/null || true)")"
  [[ -n "$body" ]] || return 1
  _install_token_text "$body" "$path"
}

# Read KEY=value from an env file without sourcing (avoids executing the file).
_env_file_get() {
  local file="$1" key="$2"
  [[ -f "$file" ]] || return 1
  local line val
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[[:space:]]*${key}= ]] || continue
    val="${line#*=}"
    _normalize_token "$val"
    return 0
  done <"$file"
  return 1
}

_try_env_file() {
  local file="$1"
  [[ -f "$file" ]] || return 1
  local path_ref token
  path_ref="$(_env_file_get "$file" "HA_TOKEN_FILE" || true)"
  if [[ -z "${path_ref:-}" ]]; then
    path_ref="$(_env_file_get "$file" "HA_LONG_LIVED_TOKEN_FILE" || true)"
  fi
  if [[ -n "${path_ref:-}" ]] && _try_token_file "$path_ref"; then
    return 0
  fi
  token="$(_env_file_get "$file" "HA_TOKEN" || true)"
  if [[ -n "${token:-}" ]]; then
    _install_token_text "$token" "${file}:HA_TOKEN"
    return 0
  fi
  return 1
}

if _dest_ok; then
  n="$(_token_len "$(_normalize_token "$(cat "$DEST")")")"
  echo "[solar-flow] token already present at ${DEST} (${n} chars) — nothing to do"
  exit 0
fi

# --- 2. Env path overrides ---
for env_name in HA_TOKEN_FILE HA_LONG_LIVED_TOKEN_FILE; do
  path_raw="${!env_name:-}"
  if [[ -n "$path_raw" ]] && _try_token_file "$path_raw"; then
    exit 0
  fi
done

# --- 3. HA_TOKEN in current environment ---
if [[ -n "${HA_TOKEN:-}" ]]; then
  tok="$(_normalize_token "$HA_TOKEN")"
  if [[ -n "$tok" ]]; then
    _install_token_text "$tok" "env:HA_TOKEN"
    exit 0
  fi
fi

# --- 4. Known absolute token file paths ---
KNOWN_TOKEN_FILES=(
  /opt/homeassistant/secrets/ha_long_lived.token
  /opt/homeassistant/secrets/long_lived.token
  /opt/homeassistant/secrets/long-lived.token
  /home/ansible/secrets/ha_long_lived.token
  /home/ansible/.secrets/ha_long_lived.token
  /home/ansible/alfa-ai/secrets/ha_long_lived.token
  /home/ansible/alfa-ai/.secrets/ha_long_lived.token
  /home/ansible/victron-ble2mqtt-integration/secrets/ha_long_lived.token
)

for path in "${KNOWN_TOKEN_FILES[@]}"; do
  if _try_token_file "$path"; then
    exit 0
  fi
done

# --- 5. Env files (HA_TOKEN= or HA_*TOKEN*_FILE=) ---
KNOWN_ENV_FILES=(
  /home/ansible/.config/host105-ai.env
  /home/ansible/alfa-ai/.env
  /home/ansible/alfa-ai/secrets/.env
  /home/ansible/.config/homeassistant.env
  /home/ansible/.config/ha.env
  /opt/homeassistant/secrets/.env
)

# Also: EnvironmentFile= lines from solar-flow / related units if present.
for unit in /etc/systemd/system/solar-flow.service \
            /etc/systemd/system/solar-flow.service.d/*.conf; do
  [[ -f "$unit" ]] || continue
  while IFS= read -r ef || [[ -n "$ef" ]]; do
    [[ -n "$ef" ]] || continue
    KNOWN_ENV_FILES+=("$ef")
  done < <(grep -E '^[[:space:]]*EnvironmentFile=-?' "$unit" 2>/dev/null \
    | sed -E 's/^[[:space:]]*EnvironmentFile=-?//' || true)
done

seen_env=""
for file in "${KNOWN_ENV_FILES[@]}"; do
  case " $seen_env " in
    *" $file "*) continue ;;
  esac
  seen_env+=" $file"
  if _try_env_file "$file"; then
    exit 0
  fi
done

# --- 6. Shallow find *.token under operator roots ---
IFS=':' read -r -a roots <<<"$SEARCH_ROOTS"
for root in "${roots[@]}"; do
  [[ -d "$root" ]] || continue
  while IFS= read -r -d '' path; do
    if _try_token_file "$path"; then
      exit 0
    fi
  done < <(find "$root" -maxdepth 4 \( -name '*.token' -o -name '*ha*long*lived*' \) \
    -type f -print0 2>/dev/null || true)
done

echo "WARN: no existing HA long-lived token found for ${DEST}" >&2
echo "WARN: searched env HA_TOKEN / HA_TOKEN_FILE, known paths under /opt/homeassistant and /home/ansible, host105-ai.env, alfa-ai .env" >&2
echo "WARN: create one in HA (Profile → Long-lived access tokens) or place a source file, then re-run." >&2
exit 1
