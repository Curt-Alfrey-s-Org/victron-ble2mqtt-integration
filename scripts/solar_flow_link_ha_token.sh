#!/usr/bin/env bash
# Locate an existing Home Assistant long-lived token and copy it to the path
# solar-flow expects. Token is operator-provisioned on disk — never in git.
#
# Where the token actually lives on this site (HA host = .105):
#   /opt/homeassistant/secrets/ha_long_lived.token   (canonical solar-flow dest)
#   /home/ansible/.config/host105-ai.env             (HA_TOKEN= / HA_TOKEN_FILE=)
#   /home/ansible/alfa-ai/secrets/*.token            (alfa-ai brain secrets)
# It is NOT expected inside the victron git clone (any secrets/ there is local-only).
#
# Destination (canonical for solar-flow / systemd unit on the diagram host):
#   /opt/homeassistant/secrets/ha_long_lived.token
#
# Search order (first non-empty wins; never prints token contents):
#   1. Dest already present and non-empty → no-op
#   2. HA_TOKEN_FILE / HA_LONG_LIVED_TOKEN_FILE env (if they point at a readable file)
#   3. HA_TOKEN env (write value to dest)
#   4. Known token files under /opt/homeassistant, /home/ansible, alfa-ai, stacks, run/secrets
#   5. Env files that may hold HA_TOKEN= or HA_TOKEN_FILE= (host105-ai.env, alfa-ai .env, …)
#   6. systemd EnvironmentFile= from solar-flow / HA / soak / brain / alfa units
#   7. Shallow find of *.token / HA_TOKEN basenames under search roots (never *ha*token*)
#   8. Remote .105 over ssh (when local search is empty) — see HA_TOKEN_HOST
#
# Usage:
#   # On .105 (HA host) — local search only:
#   sudo bash scripts/solar_flow_link_ha_token.sh
#   # On web-sites (solar-flow) when the token only exists on .105:
#   sudo bash scripts/solar_flow_link_ha_token.sh -v
#   # Override host / user / disable remote:
#   sudo HA_TOKEN_HOST=192.168.0.105 HA_TOKEN_SSH_USER=ansible bash scripts/solar_flow_link_ha_token.sh
#   sudo HA_TOKEN_REMOTE=0 bash scripts/solar_flow_link_ha_token.sh   # local only
#   # or: sudo bash scripts/solar_flow_enable_tailscale.sh  (calls this first)
#
# Security: never echo the token; at most "copied N chars from PATH → DEST".
# Verbose mode lists candidate paths only (miss / empty / used) — never values.

set -euo pipefail

DEST="${SOLAR_FLOW_HA_TOKEN_DEST:-/opt/homeassistant/secrets/ha_long_lived.token}"
# Optional override for tests: colon-separated extra roots for find (default below).
SEARCH_ROOTS="${SOLAR_FLOW_HA_TOKEN_SEARCH_ROOTS:-/opt/homeassistant:/home/ansible:/opt/stacks:/opt/dockge:/run/secrets:/root:/home}"
VERBOSE="${SOLAR_FLOW_TOKEN_VERBOSE:-0}"
# Remote HA-token hosts. Primary = HA LAN (.105). Extra = operator/dev boxes that may
# hold a saved copy (e.g. .93 Windows/dev host via OpenSSH). Colon-separated.
HA_TOKEN_HOST="${HA_TOKEN_HOST:-192.168.0.105}"
HA_TOKEN_EXTRA_HOSTS="${HA_TOKEN_EXTRA_HOSTS:-192.168.0.93}"
HA_TOKEN_SSH_USER="${HA_TOKEN_SSH_USER:-ansible}"
# Optional per-host user override for .93 (often a different account on the PC).
HA_TOKEN_SSH_USER_93="${HA_TOKEN_SSH_USER_93:-${HA_TOKEN_SSH_USER}}"
HA_TOKEN_REMOTE="${HA_TOKEN_REMOTE:-1}"
HA_TOKEN_SSH_OPTS="${HA_TOKEN_SSH_OPTS:--o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new}"

for arg in "$@"; do
  case "$arg" in
    -v|--verbose) VERBOSE=1 ;;
    -h|--help)
      sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
  esac
done

die() { echo "FAIL: $*" >&2; exit 1; }

_v() {
  [[ "$VERBOSE" == "1" ]] || return 0
  echo "[solar-flow][verbose] $*" >&2
}

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

# Home Assistant long-lived tokens are single-line JWTs / opaque secrets — never shell scripts.
# Reject the false positive that matched solar_flow_link_ha_token.sh via *ha*token* find.
_looks_like_ha_token() {
  local t="$1"
  local n
  n="$(_token_len "$t")"
  if [[ "$n" -lt 32 || "$n" -gt 4096 ]]; then
    return 1
  fi
  case "$t" in
    \#!*) return 1 ;;
  esac
  if [[ "$t" == *$'\n'* ]]; then
    return 1
  fi
  # JWT / URL-safe opaque token charset only
  [[ "$t" =~ ^[A-Za-z0-9._=-]+$ ]] || return 1
  return 0
}

_path_looks_like_token_file() {
  local path="$1" base
  base="$(basename "$path")"
  case "$path" in
    */scripts/*|*/.git/*|*/tests/*|*/node_modules/*) return 1 ;;
  esac
  case "$base" in
    *.sh|*.py|*.md|*.js|*.css|*.html|*.yml|*.yaml|*.service|*.timer|*.json|*.lock)
      return 1
      ;;
    *.token|HA_TOKEN|ha_token|long_lived.token|long-lived.token|ha.token)
      return 0
      ;;
    *)
      # Exact secret-style basenames only — never *token* glob hits on this script.
      return 1
      ;;
  esac
}

_dest_ok() {
  [[ -f "$DEST" ]] || return 1
  local body
  body="$(_normalize_token "$(cat "$DEST" 2>/dev/null || true)")"
  _looks_like_ha_token "$body"
}

_install_token_text() {
  local token="$1" source_label="$2"
  local n
  token="$(_normalize_token "$token")"
  if ! _looks_like_ha_token "$token"; then
    _v "reject non-token payload from ${source_label} (len=$(_token_len "$token"))"
    return 1
  fi
  n="$(_token_len "$token")"
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
  if [[ -z "$path" ]]; then
    _v "skip token-file: (empty path)"
    return 1
  fi
  if [[ ! -f "$path" ]]; then
    _v "miss token-file: ${path}"
    return 1
  fi
  if ! _path_looks_like_token_file "$path"; then
    _v "skip non-secret path: ${path}"
    return 1
  fi
  # Skip if already the dest (caller handles dest-ok).
  if [[ "$(readlink -f "$path" 2>/dev/null || echo "$path")" == "$(readlink -f "$DEST" 2>/dev/null || echo "$DEST")" ]]; then
    _v "skip token-file: ${path} (is dest)"
    return 1
  fi
  local body
  body="$(_normalize_token "$(cat "$path" 2>/dev/null || true)")"
  if [[ -z "$body" ]]; then
    _v "empty token-file: ${path}"
    return 1
  fi
  if ! _looks_like_ha_token "$body"; then
    _v "reject non-token file: ${path} (len=$(_token_len "$body"))"
    return 1
  fi
  _v "hit token-file: ${path}"
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

_TOKEN_ENV_KEYS=(
  HA_TOKEN
  HA_LONG_LIVED_TOKEN
  HOMEASSISTANT_TOKEN
  HASS_TOKEN
  LONG_LIVED_ACCESS_TOKEN
  HA_LONG_LIVED_ACCESS_TOKEN
)
_TOKEN_FILE_ENV_KEYS=(
  HA_TOKEN_FILE
  HA_LONG_LIVED_TOKEN_FILE
  HOMEASSISTANT_TOKEN_FILE
  HASS_TOKEN_FILE
)

_list_env_key_names() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  local keys
  keys="$(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$file" 2>/dev/null | cut -d= -f1 | sort -u | tr '\n' ' ')"
  keys="${keys%"${keys##*[![:space:]]}"}"
  if [[ -n "$keys" ]]; then
    _v "env-file ${file} key names (values redacted): ${keys}"
  else
    _v "env-file ${file}: no KEY= lines"
  fi
}

_try_env_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    _v "miss env-file: ${file}"
    return 1
  fi
  _v "check env-file: ${file}"
  _list_env_key_names "$file"
  local path_ref token key
  for key in "${_TOKEN_FILE_ENV_KEYS[@]}"; do
    path_ref="$(_env_file_get "$file" "$key" || true)"
    if [[ -n "${path_ref:-}" ]]; then
      _v "env-file ${file}: ${key} → ${path_ref}"
      if _try_token_file "$path_ref"; then
        return 0
      fi
    fi
  done
  for key in "${_TOKEN_ENV_KEYS[@]}"; do
    token="$(_env_file_get "$file" "$key" || true)"
    if [[ -n "${token:-}" ]]; then
      _v "hit env-file key ${key}: ${file}"
      if _install_token_text "$token" "${file}:${key}"; then
        return 0
      fi
    fi
  done
  _v "no usable HA token keys in: ${file}"
  return 1
}

_collect_systemd_env_files() {
  local unit ef
  # shellcheck disable=SC2044
  for unit in \
    /etc/systemd/system/solar-flow.service \
    /etc/systemd/system/solar-flow.service.d/*.conf \
    /etc/systemd/system/*ha*.service \
    /etc/systemd/system/*ha*.service.d/*.conf \
    /etc/systemd/system/*soak*.service \
    /etc/systemd/system/*soak*.service.d/*.conf \
    /etc/systemd/system/*brain*.service \
    /etc/systemd/system/*brain*.service.d/*.conf \
    /etc/systemd/system/*alfa*.service \
    /etc/systemd/system/*alfa*.service.d/*.conf \
    /etc/systemd/system/*homeassistant*.service \
    /etc/systemd/system/*homeassistant*.service.d/*.conf \
    /lib/systemd/system/*ha*.service \
    /lib/systemd/system/*soak*.service \
    /lib/systemd/system/*brain*.service \
    /lib/systemd/system/*alfa*.service
  do
    [[ -f "$unit" ]] || continue
    _v "scan unit: ${unit}"
    while IFS= read -r ef || [[ -n "$ef" ]]; do
      [[ -n "$ef" ]] || continue
      # Drop optional leading '-' (systemd ignore-missing).
      ef="${ef#-}"
      printf '%s\n' "$ef"
    done < <(grep -E '^[[:space:]]*EnvironmentFile=-?' "$unit" 2>/dev/null \
      | sed -E 's/^[[:space:]]*EnvironmentFile=-?//' || true)
  done
}

# True if HA_TOKEN_HOST is this machine (skip useless ssh-to-self).
_host_is_local() {
  local host="$1"
  [[ -z "$host" ]] && return 0
  case "$host" in
    127.*|localhost|::1) return 0 ;;
  esac
  local ip
  while IFS= read -r ip; do
    [[ -n "$ip" && "$ip" == "$host" ]] && return 0
  done < <(hostname -I 2>/dev/null | tr ' ' '\n'; ip -4 -o addr show 2>/dev/null | awk '{print $4}' | cut -d/ -f1)
  return 1
}

# Fetch a remote file to stdout (scp preferred); never log contents.
_remote_cat() {
  local target="$1" rpath="$2" tmp
  tmp="$(mktemp)"
  # shellcheck disable=SC2086
  if command -v scp >/dev/null 2>&1 \
    && scp ${HA_TOKEN_SSH_OPTS} "${target}:${rpath}" "$tmp" >/dev/null 2>&1; then
    cat "$tmp"
    rm -f "$tmp"
    return 0
  fi
  rm -f "$tmp"
  # shellcheck disable=SC2086
  ssh ${HA_TOKEN_SSH_OPTS} "$target" "cat -- $(printf '%q' "$rpath")" 2>/dev/null
}

# Pull token from HA host over ssh when solar-flow runs elsewhere (e.g. web-sites).
# Prints only source path + char count; never the token value.
_try_remote_ha_token_host() {
  local host="$1"
  local user="$2"
  local target remote_kind remote_path remote_body path_ref tok tmp_env

  if [[ "${HA_TOKEN_REMOTE}" == "0" || "${HA_TOKEN_REMOTE}" == "false" || "${HA_TOKEN_REMOTE}" == "no" ]]; then
    _v "remote fetch disabled (HA_TOKEN_REMOTE=${HA_TOKEN_REMOTE})"
    return 1
  fi
  if [[ -z "$host" ]]; then
    _v "remote fetch skipped (HA_TOKEN_HOST empty)"
    return 1
  fi
  if _host_is_local "$host"; then
    _v "remote fetch skipped (${host} is this host)"
    return 1
  fi
  if ! command -v ssh >/dev/null 2>&1; then
    _v "remote fetch skipped (ssh not installed)"
    return 1
  fi

  target="${user}@${host}"
  _v "probe remote token host: ${target}"

  # shellcheck disable=SC2086
  if ! ssh ${HA_TOKEN_SSH_OPTS} "$target" 'true' 2>/dev/null; then
    echo "WARN: cannot ssh to ${target} (BatchMode) — token may only exist on .105" >&2
    echo "WARN: fix: ssh-copy-id ${target}  OR  run linker on .105 then scp the dest here" >&2
    _v "ssh probe failed for ${target}"
    return 1
  fi

  # Remote probe: FILE|<path> or ENV|<path> (paths only — never token values).
  # shellcheck disable=SC2086
  remote_kind="$(ssh ${HA_TOKEN_SSH_OPTS} "$target" 'bash -s' <<'REMOTE' 2>/dev/null || true
set -euo pipefail
for p in \
  /opt/homeassistant/secrets/ha_long_lived.token \
  /opt/homeassistant/secrets/long_lived.token \
  /opt/homeassistant/secrets/long-lived.token \
  /opt/homeassistant/secrets/ha.token \
  /opt/homeassistant/ha_long_lived.token \
  /opt/homeassistant/.secrets/ha_long_lived.token \
  /home/ansible/secrets/ha_long_lived.token \
  /home/ansible/secrets/ha.token \
  /home/ansible/.secrets/ha_long_lived.token \
  /home/ansible/.config/ha_long_lived.token \
  /home/ansible/.config/homeassistant/ha_long_lived.token \
  /home/ansible/alfa-ai/secrets/ha_long_lived.token \
  /home/ansible/alfa-ai/secrets/long_lived.token \
  /home/ansible/alfa-ai/secrets/ha.token \
  /home/ansible/alfa-ai/.secrets/ha_long_lived.token \
  /home/ansible/victron-ble2mqtt-integration/secrets/ha_long_lived.token \
  /root/secrets/ha_long_lived.token \
  /root/.secrets/ha_long_lived.token \
  /run/secrets/ha_long_lived.token \
  /opt/stacks/homeassistant/secrets/ha_long_lived.token
do
  if [[ -f "$p" && -s "$p" ]]; then
    printf 'FILE|%s\n' "$p"
    exit 0
  fi
done
for e in \
  /home/ansible/.config/host105-ai.env \
  /home/ansible/.config/host105.env \
  /home/ansible/.config/homeassistant.env \
  /home/ansible/.config/ha.env \
  /home/ansible/.config/alfa-ai.env \
  /home/ansible/.config/solar-flow.env \
  /home/ansible/.env \
  /home/ansible/alfa-ai/.env \
  /home/ansible/alfa-ai/secrets/.env \
  /home/ansible/victron-ble2mqtt-integration/.env \
  /opt/homeassistant/secrets/.env \
  /opt/homeassistant/.env \
  /root/.config/host105-ai.env \
  /root/.config/ha.env
do
  [[ -f "$e" ]] || continue
  if grep -Eq '^[[:space:]]*(HA_TOKEN_FILE|HA_LONG_LIVED_TOKEN_FILE|HA_TOKEN|HA_LONG_LIVED_TOKEN|HOMEASSISTANT_TOKEN|HASS_TOKEN|LONG_LIVED_ACCESS_TOKEN|HA_LONG_LIVED_ACCESS_TOKEN)=' "$e" 2>/dev/null; then
    printf 'ENV|%s\n' "$e"
    exit 0
  fi
done
exit 1
REMOTE
)"
  remote_kind="${remote_kind//$'\r'/}"
  remote_kind="${remote_kind%%$'\n'*}"

  if [[ -z "${remote_kind}" ]]; then
    _v "remote ${target}: no token file or HA_TOKEN* env keys"
    return 1
  fi

  remote_path="${remote_kind#*|}"
  case "$remote_kind" in
    FILE\|*)
      _v "remote hit token-file: ${target}:${remote_path}"
      remote_body="$(_normalize_token "$(_remote_cat "$target" "$remote_path" || true)")"
      [[ -n "$remote_body" ]] || { _v "remote file empty after normalize: ${remote_path}"; return 1; }
      _install_token_text "$remote_body" "${target}:${remote_path}"
      return 0
      ;;
    ENV\|*)
      _v "remote hit env-file: ${target}:${remote_path}"
      tmp_env="$(mktemp)"
      if ! _remote_cat "$target" "$remote_path" >"$tmp_env" 2>/dev/null; then
        rm -f "$tmp_env"
        _v "failed to fetch remote env: ${remote_path}"
        return 1
      fi
      if _try_env_file "$tmp_env"; then
        # _try_env_file writes DEST with label like file:KEY — rewrite message is fine
        rm -f "$tmp_env"
        return 0
      fi
      rm -f "$tmp_env"
      _v "remote env had no usable token: ${remote_path}"
      return 1
      ;;
    *)
      _v "remote unexpected probe result (redacted)"
      return 1
      ;;
  esac
}

if _dest_ok; then
  n="$(_token_len "$(_normalize_token "$(cat "$DEST")")")"
  echo "[solar-flow] token already present at ${DEST} (${n} chars) — nothing to do"
  exit 0
fi
if [[ -f "$DEST" ]]; then
  echo "[solar-flow] removing invalid dest (not an HA long-lived token): ${DEST}" >&2
  rm -f "$DEST"
fi
_v "dest missing/empty: ${DEST}"

# --- 2. Env path overrides ---
for env_name in HA_TOKEN_FILE HA_LONG_LIVED_TOKEN_FILE; do
  path_raw="${!env_name:-}"
  if [[ -n "$path_raw" ]]; then
    _v "check env ${env_name} → ${path_raw}"
    if _try_token_file "$path_raw"; then
      exit 0
    fi
  else
    _v "env ${env_name}: unset"
  fi
done

# --- 3. HA_TOKEN in current environment ---
if [[ -n "${HA_TOKEN:-}" ]]; then
  tok="$(_normalize_token "$HA_TOKEN")"
  if [[ -n "$tok" ]]; then
    _v "hit env:HA_TOKEN"
    _install_token_text "$tok" "env:HA_TOKEN"
    exit 0
  fi
  _v "env HA_TOKEN set but empty after normalize"
else
  _v "env HA_TOKEN: unset"
fi

# --- 4. Known absolute token file paths ---
KNOWN_TOKEN_FILES=(
  /opt/homeassistant/secrets/ha_long_lived.token
  /opt/homeassistant/secrets/long_lived.token
  /opt/homeassistant/secrets/long-lived.token
  /opt/homeassistant/secrets/ha.token
  /opt/homeassistant/secrets/HA_TOKEN
  /opt/homeassistant/ha_long_lived.token
  /opt/homeassistant/.secrets/ha_long_lived.token
  /home/ansible/secrets/ha_long_lived.token
  /home/ansible/secrets/long_lived.token
  /home/ansible/secrets/ha.token
  /home/ansible/.secrets/ha_long_lived.token
  /home/ansible/.secrets/ha.token
  /home/ansible/.config/ha_long_lived.token
  /home/ansible/.config/ha.token
  /home/ansible/.config/homeassistant/ha_long_lived.token
  /home/ansible/alfa-ai/secrets/ha_long_lived.token
  /home/ansible/alfa-ai/secrets/long_lived.token
  /home/ansible/alfa-ai/secrets/ha.token
  /home/ansible/alfa-ai/secrets/HA_TOKEN
  /home/ansible/alfa-ai/.secrets/ha_long_lived.token
  /home/ansible/alfa-ai/.secrets/ha.token
  /home/ansible/victron-ble2mqtt-integration/secrets/ha_long_lived.token
  /home/ansible/victron-ble2mqtt-integration/secrets/ha.token
  /root/secrets/ha_long_lived.token
  /root/.secrets/ha_long_lived.token
  /root/.config/ha_long_lived.token
  /run/secrets/ha_long_lived.token
  /run/secrets/ha_token
  /run/secrets/HA_TOKEN
  /opt/stacks/homeassistant/ha_long_lived.token
  /opt/stacks/homeassistant/secrets/ha_long_lived.token
)

for path in "${KNOWN_TOKEN_FILES[@]}"; do
  if _try_token_file "$path"; then
    exit 0
  fi
done

# --- 5. Env files (HA_TOKEN= or HA_*TOKEN*_FILE=) ---
KNOWN_ENV_FILES=(
  /home/ansible/.config/host105-ai.env
  /home/ansible/.config/host105.env
  /home/ansible/.config/homeassistant.env
  /home/ansible/.config/ha.env
  /home/ansible/.config/alfa-ai.env
  /home/ansible/.config/solar-flow.env
  /home/ansible/.env
  /home/ansible/alfa-ai/.env
  /home/ansible/alfa-ai/secrets/.env
  /home/ansible/alfa-ai/.secrets/.env
  /home/ansible/victron-ble2mqtt-integration/.env
  /opt/homeassistant/secrets/.env
  /opt/homeassistant/.env
  /opt/stacks/homeassistant/.env
  /opt/stacks/victron/.env
  /opt/dockge/.env
  /etc/default/solar-flow
  /etc/default/homeassistant
  /root/.config/host105-ai.env
  /root/.config/ha.env
)

# Shallow glob of extra *.env under likely dirs (paths only; no contents logged).
for dir in /home/ansible/.config /home/ansible/alfa-ai /home/ansible/alfa-ai/secrets \
           /opt/stacks /opt/homeassistant/secrets /run/secrets; do
  [[ -d "$dir" ]] || continue
  while IFS= read -r -d '' ef; do
    KNOWN_ENV_FILES+=("$ef")
  done < <(find "$dir" -maxdepth 3 -type f \( -name '*.env' -o -name '*.token' \) \
    ! -path '*/.git/*' ! -path '*/scripts/*' -print0 2>/dev/null || true)
done

# --- 6. systemd EnvironmentFile= from related units ---
while IFS= read -r ef || [[ -n "$ef" ]]; do
  [[ -n "$ef" ]] || continue
  KNOWN_ENV_FILES+=("$ef")
done < <(_collect_systemd_env_files || true)

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

# --- 7. Shallow find *.token (and exact HA_TOKEN basenames) under operator roots ---
# Never use *ha*token* — that matched scripts/solar_flow_link_ha_token.sh and poisoned DEST.
IFS=':' read -r -a roots <<<"$SEARCH_ROOTS"
for root in "${roots[@]}"; do
  [[ -d "$root" ]] || { _v "skip find root (missing): ${root}"; continue; }
  _v "find under: ${root} (maxdepth 5)"
  while IFS= read -r -d '' path; do
    if _try_token_file "$path"; then
      exit 0
    fi
  done < <(find "$root" -maxdepth 5 \( \
      -name '*.token' -o \
      -name 'HA_TOKEN' -o \
      -name 'ha_token' \
    \) -type f ! -path '*/.git/*' ! -path '*/scripts/*' ! -path '*/tests/*' -print0 2>/dev/null || true)
done

# --- 8. Remote .105 (or HA_TOKEN_HOST) when diagram host ≠ HA host ---
_v "local search empty — trying remote HA_TOKEN_HOST=${HA_TOKEN_HOST} user=${HA_TOKEN_SSH_USER}"
if _try_remote_ha_token_host "$HA_TOKEN_HOST" "$HA_TOKEN_SSH_USER"; then
  exit 0
fi

echo "WARN: no existing HA long-lived token found for ${DEST}" >&2
if _host_is_local "$HA_TOKEN_HOST"; then
  echo "WARN: this machine IS ${HA_TOKEN_HOST} (web-sites / .105) — there is no remote host to copy from." >&2
  echo "WARN: host105-ai.env / alfa-ai .env exist but have no HA_TOKEN* keys; no *.token secret file on disk." >&2
  echo "WARN: create ONE long-lived token in HA (Profile → Security → Long-lived access tokens), then:" >&2
else
  echo "WARN: searched local paths, then ssh ${HA_TOKEN_SSH_USER}@${HA_TOKEN_HOST}" >&2
  echo "WARN: ensure BatchMode ssh: ssh ${HA_TOKEN_SSH_USER}@${HA_TOKEN_HOST} true" >&2
  echo "WARN: or create a token in HA and write it here:" >&2
fi
echo "  sudo mkdir -p $(dirname "$DEST")" >&2
echo "  sudo tee $DEST >/dev/null   # paste one line, Ctrl-D" >&2
echo "  sudo chmod 600 $DEST" >&2
echo "  sudo systemctl restart solar-flow.service" >&2
echo "WARN: confirm live: curl -fsS http://127.0.0.1:8765/api/snapshot | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"mode\"])'" >&2
exit 1
