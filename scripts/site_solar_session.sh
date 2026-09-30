#!/usr/bin/env bash
# One .105 session for Site solar: pull, token, wait for HA, backup, then one action.
#
#   bash scripts/site_solar_session.sh [options] ACTION [ARGS...]
#
# Actions:
#   backup              only the common steps (ends with the helper/dashboard backup)
#   solar-compare       export the live Solar tab and print the Solar tab vs Site solar table
#   dashboard-dry-run   show what re-seeding /site-solar would do (writes nothing to HA)
#   dashboard-apply     re-seed /site-solar from the repo (save script --force; backs up first)
#   restore ARGS...     passthrough: python3 scripts/site_solar_settings.py restore ARGS...
#                       e.g. restore --from LATEST --dashboard --dry-run
#
# Options:
#   --no-pull       skip "git pull --ff-only origin main" (default: pull first)
#   --keep-token    keep ~/.ha_token even if this run created it
#   --keep-export   keep config/dashboards/exports/solar-tab.json if this run created it
#   --wait SECONDS  how long to wait for HA to answer (default 300)
#   -h, --help      show this help
#
# Common steps, in order: cd to the repo root, git pull (unless --no-pull), token file,
# export HA_TOKEN_FILE / HA_URL (default http://127.0.0.1:8123), wait for HA, and back up
# with "python3 scripts/site_solar_settings.py export". Token file: $HA_TOKEN_FILE if set,
# else ~/.ha_token. If neither exists, it is created with mode 600 and opened in
# ${EDITOR:-nano}; paste a long-lived HA token there and save. The token is never
# printed and never read from the terminal. On exit, a trap removes ~/.ha_token if this
# run created it (unless --keep-token) and removes a Solar tab export this run created
# (unless --keep-export). Run it with bash, not "source", so nothing stays in your shell.
set -euo pipefail

PULL=1
KEEP_TOKEN=0
KEEP_EXPORT=0
WAIT_S=300
HA_URL="${HA_URL:-http://127.0.0.1:8123}"

usage() { sed -n '2,29p' "$0" | sed 's/^# \{0,1\}//'; }
step() { printf '\n==> %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-pull) PULL=0; shift ;;
    --keep-token) KEEP_TOKEN=1; shift ;;
    --keep-export) KEEP_EXPORT=1; shift ;;
    --wait) WAIT_S="${2:?--wait needs seconds}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    --) shift; break ;;
    -*) die "unknown option: $1 (see --help)" ;;
    *) break ;;
  esac
done
ACTION="${1:-}"
[[ -n "$ACTION" ]] || { usage >&2; exit 2; }
shift
case "$ACTION" in
  backup|solar-compare|dashboard-dry-run|dashboard-apply|restore) ;;
  *) die "unknown action: $ACTION (backup, solar-compare, dashboard-dry-run, dashboard-apply, restore)" ;;
esac
[[ "$WAIT_S" =~ ^[0-9]+$ ]] || die "--wait needs a number of seconds"

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPORT_REL="config/dashboards/exports/solar-tab.json"
DEFAULT_TOKEN="$HOME/.ha_token"
CREATED_TOKEN=""
EXPORT_EXISTED=0

cleanup() {
  local rc=$?
  if [[ -n "$CREATED_TOKEN" && "$KEEP_TOKEN" == 0 ]]; then
    rm -f "$CREATED_TOKEN" && echo "==> cleanup: removed $CREATED_TOKEN (created by this run)"
  fi
  if [[ "$EXPORT_EXISTED" == 0 && "$KEEP_EXPORT" == 0 && -f "$REPO/$EXPORT_REL" ]]; then
    rm -f "$REPO/$EXPORT_REL" && echo "==> cleanup: removed $EXPORT_REL (created by this run; --keep-export keeps it)"
  fi
  unset HA_TOKEN_FILE
  exit "$rc"
}
if [[ -f "$REPO/$EXPORT_REL" ]]; then EXPORT_EXISTED=1; fi
trap cleanup EXIT

cd "$REPO"

if [[ "$PULL" == 1 ]]; then
  step "git pull --ff-only origin main"
  git pull --ff-only origin main
else
  step "git pull skipped (--no-pull)"
fi

step "token file"
if [[ -n "${HA_TOKEN_FILE:-}" ]]; then
  [[ -s "$HA_TOKEN_FILE" ]] || die "HA_TOKEN_FILE=$HA_TOKEN_FILE is missing or empty"
  echo "using \$HA_TOKEN_FILE ($HA_TOKEN_FILE)"
elif [[ -s "$DEFAULT_TOKEN" ]]; then
  export HA_TOKEN_FILE="$DEFAULT_TOKEN"
  echo "using existing $DEFAULT_TOKEN (kept at the end)"
else
  if [[ ! -e "$DEFAULT_TOKEN" ]]; then
    install -m 600 /dev/null "$DEFAULT_TOKEN"
    CREATED_TOKEN="$DEFAULT_TOKEN"
  fi
  echo "paste a long-lived HA token into $DEFAULT_TOKEN, save and exit the editor"
  "${EDITOR:-nano}" "$DEFAULT_TOKEN"
  chmod 600 "$DEFAULT_TOKEN"
  [[ -s "$DEFAULT_TOKEN" ]] || die "$DEFAULT_TOKEN is empty; nothing to authenticate with"
  export HA_TOKEN_FILE="$DEFAULT_TOKEN"
fi
export HA_URL
echo "HA_URL=$HA_URL"

step "wait for Home Assistant at $HA_URL (up to ${WAIT_S}s)"
waited=0
until curl -s -o /dev/null "$HA_URL"; do
  if (( waited >= WAIT_S )); then
    die "Home Assistant did not answer at $HA_URL after ${WAIT_S}s (is the container up? docker ps)"
  fi
  sleep 5
  waited=$((waited + 5))
done
echo "HA is up"

step "backup: python3 scripts/site_solar_settings.py export"
python3 scripts/site_solar_settings.py export

case "$ACTION" in
  backup)
    step "done (backup only)"
    ;;
  solar-compare)
    step "export the Solar tab (read-only): site_solar_settings.py export-dashboard"
    python3 scripts/site_solar_settings.py export-dashboard
    step "compare with Site solar: compare_solar_tab.py"
    python3 scripts/compare_solar_tab.py "$EXPORT_REL"
    ;;
  dashboard-dry-run)
    step "dry run: save_solar_plant_storage_dashboard.py --dry-run (writes nothing)"
    set +e
    python3 scripts/save_solar_plant_storage_dashboard.py --dry-run
    rc=$?
    set -e
    if [[ "$rc" == 3 ]]; then
      step "live /site-solar has UI edits; what dashboard-apply (--force) would do (writes nothing)"
      python3 scripts/save_solar_plant_storage_dashboard.py --dry-run --force
    elif [[ "$rc" != 0 ]]; then
      exit "$rc"
    fi
    ;;
  dashboard-apply)
    step "re-seed: save_solar_plant_storage_dashboard.py --force (backs up the live dashboard first)"
    python3 scripts/save_solar_plant_storage_dashboard.py --force
    echo "undo: python3 scripts/site_solar_settings.py restore --from <backup folder> --dashboard"
    ;;
  restore)
    step "restore: site_solar_settings.py restore $*"
    python3 scripts/site_solar_settings.py restore "$@"
    ;;
esac
