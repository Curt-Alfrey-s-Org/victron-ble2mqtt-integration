#!/usr/bin/env bash
# Enable the animated solar-flow diagram on Tailscale (.105 operator host).
#
# What this does:
#   1. Ensures solar-flow listens on localhost :8765 (systemd unit preferred).
#   2. Configures `tailscale serve` so the diagram is reachable on this host's
#      MagicDNS HTTPS URL (tailnet only — not Funnel / public internet).
#   3. Prints the exact URL(s) to open on phone or laptop with Tailscale on.
#
# Prerequisites on the solar-flow host (this site: web-sites; HA is on .105):
#   - Tailscale installed and `tailscale status` online
#   - HA long-lived token on .105 (host105-ai.env / /opt/homeassistant/secrets / alfa-ai)
#     — linker auto-copies locally, or pulls via ssh ansible@192.168.0.105
#   - This repo checked out (REPO_ROOT)
#   - When not on .105: HA_BASE_URL=http://192.168.0.105:8123
#
# Official:
#   https://tailscale.com/docs/features/tailscale-serve
#   https://tailscale.com/docs/reference/tailscale-cli/serve
#
# Usage (on .105 / web-sites):
#   sudo bash scripts/solar_flow_enable_tailscale.sh
#   # then open the printed https://....ts.net/ URL on the phone

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${SOLAR_FLOW_PORT:-8765}"
UNIT_SRC="$ROOT_DIR/systemd/solar-flow.service"
UNIT_DST="/etc/systemd/system/solar-flow.service"
TOKEN_FILE="${HA_TOKEN_FILE:-${HA_LONG_LIVED_TOKEN_FILE:-/opt/homeassistant/secrets/ha_long_lived.token}}"
# HA Container is on .105; use LAN IP so web-sites (and .105) both reach it.
HA_BASE_URL="${HA_BASE_URL:-http://192.168.0.105:8123}"
LINK_TOKEN_SCRIPT="$ROOT_DIR/scripts/solar_flow_link_ha_token.sh"

die() { echo "FAIL: $*" >&2; exit 1; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

need_cmd tailscale
need_cmd python3
need_cmd systemctl

if ! tailscale status >/dev/null 2>&1; then
  die "tailscale is not up — run: sudo tailscale up"
fi

# Auto-discover an existing site token and copy into the solar-flow path (no HA UI hunt).
if [[ -x "$LINK_TOKEN_SCRIPT" || -f "$LINK_TOKEN_SCRIPT" ]]; then
  echo "[solar-flow] Linking HA long-lived token (auto-discover) ..."
  # Prefer the canonical dest; allow link script to find sources even when TOKEN_FILE unset.
  if SOLAR_FLOW_HA_TOKEN_DEST="$TOKEN_FILE" bash "$LINK_TOKEN_SCRIPT"; then
    :
  else
    echo "WARN: could not auto-link token → $TOKEN_FILE (diagram may start in DEMO)." >&2
  fi
fi

if [[ ! -f "$TOKEN_FILE" ]] || [[ ! -s "$TOKEN_FILE" ]]; then
  echo "WARN: token file missing ($TOKEN_FILE). Server will start in DEMO mode until a source is found." >&2
  echo "WARN: DEMO Battery 1 voltage (~29.0 V) is a placeholder — not live HA." >&2
  echo "WARN: re-run: sudo bash $LINK_TOKEN_SCRIPT" >&2
fi

if [[ ! -f "$UNIT_SRC" ]]; then
  die "missing unit template: $UNIT_SRC"
fi

echo "[solar-flow] Installing systemd unit ..."
# Render REPO_ROOT and token path into the unit (no secrets in the unit beyond the path).
tmp_unit="$(mktemp)"
sed \
  -e "s|@REPO_ROOT@|${ROOT_DIR}|g" \
  -e "s|@HA_TOKEN_FILE@|${TOKEN_FILE}|g" \
  -e "s|@HA_BASE_URL@|${HA_BASE_URL}|g" \
  -e "s|@SOLAR_FLOW_PORT@|${PORT}|g" \
  "$UNIT_SRC" >"$tmp_unit"
sudo install -m 0644 "$tmp_unit" "$UNIT_DST"
rm -f "$tmp_unit"
sudo systemctl daemon-reload
sudo systemctl enable --now solar-flow.service
# Pick up a token created after a previous install without re-running sed paths.
sudo systemctl restart solar-flow.service

# Wait briefly for listen
for _ in $(seq 1 20); do
  if curl -fsS "http://127.0.0.1:${PORT}/" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done
curl -fsS "http://127.0.0.1:${PORT}/" >/dev/null || die "solar-flow not responding on 127.0.0.1:${PORT}"

# Confirm LIVE vs DEMO so a missing token is obvious before Tailscale Serve is advertised.
snap_mode="$(curl -fsS "http://127.0.0.1:${PORT}/api/snapshot" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin).get("mode",""))' 2>/dev/null || true)"
if [[ "$snap_mode" == "live" ]]; then
  echo "[solar-flow] Snapshot mode: LIVE (Home Assistant REST OK)"
elif [[ "$snap_mode" == "demo" ]]; then
  echo >&2
  echo "=== DEMO MODE — Battery 1 ~29.0 V is a placeholder, not live HA ===" >&2
  echo "Auto-link failed (or no source on this host / unreachable .105). Prefer:" >&2
  echo "  sudo bash ${LINK_TOKEN_SCRIPT} -v" >&2
  echo "That searches local paths, then ssh ansible@192.168.0.105 (HA_TOKEN_HOST)." >&2
  echo "Token is on .105 disk secrets — not in the victron git clone." >&2
  echo "Only if nothing exists yet — HA Profile → Long-lived access tokens, then:" >&2
  echo "  sudo mkdir -p $(dirname "$TOKEN_FILE")" >&2
  echo "  sudo tee $TOKEN_FILE >/dev/null   # paste one line, Ctrl-D" >&2
  echo "  sudo chmod 600 $TOKEN_FILE" >&2
  echo "  sudo systemctl restart solar-flow.service" >&2
  echo "  curl -fsS http://127.0.0.1:${PORT}/api/snapshot | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d[\"mode\"], d[\"entities\"].get(\"sensor.battery_1_voltage\",{}).get(\"state\"))'" >&2
  echo "Expect: live <real-voltage>  (badge LIVE, no amber DEMO banner)" >&2
  echo >&2
else
  echo "WARN: could not read /api/snapshot mode (got: ${snap_mode:-empty})" >&2
fi

echo "[solar-flow] Configuring Tailscale Serve (HTTPS → localhost:${PORT}) ..."
# Persist in background. Serve is tailnet-only (not Funnel).
# https://tailscale.com/docs/reference/tailscale-cli/serve
sudo tailscale serve --bg "${PORT}"

echo
echo "=== Solar flow Tailscale address ==="
# Prefer Serve HTTPS URL from status text; fall back to MagicDNS + port.
serve_url=""
if serve_status="$(tailscale serve status 2>/dev/null || true)"; then
  serve_url="$(printf '%s\n' "$serve_status" | grep -Eo 'https://[a-zA-Z0-9._-]+\.ts\.net' | head -n1 || true)"
fi

ts_ip="$(tailscale ip -4 2>/dev/null | awk 'NR==1{print; exit}')"
magicdns=""
if status_json="$(tailscale status --json 2>/dev/null || true)"; then
  magicdns="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("Self") or {}).get("DNSName","").rstrip("."))' <<<"$status_json" 2>/dev/null || true)"
fi

if [[ -n "$serve_url" ]]; then
  echo "  Primary (Tailscale Serve HTTPS): ${serve_url}/"
else
  echo "  WARN: could not parse Serve HTTPS URL — check: tailscale serve status" >&2
fi
if [[ -n "$magicdns" ]]; then
  echo "  Direct HTTP (Tailscale MagicDNS): http://${magicdns}:${PORT}/"
fi
if [[ -n "$ts_ip" ]]; then
  echo "  Direct HTTP (Tailscale IP):      http://${ts_ip}:${PORT}/"
fi
echo "  Local:                             http://127.0.0.1:${PORT}/"
echo
echo "Phone: turn Tailscale ON, then open the Primary URL above."
echo "Home Assistant Sungold tiles: same host :8123 — open Solar → Sungold view."
echo "To attach the diagram link on the Solar dashboard (HA stopped):"
if [[ -n "$serve_url" ]]; then
  echo "  sudo SOLAR_FLOW_PUBLIC_URL='${serve_url}/' python3 ${ROOT_DIR}/scripts/ha_label_sungold_solar.py"
else
  echo "  sudo SOLAR_FLOW_PUBLIC_URL='http://${magicdns:-YOUR-105.ts.net}:${PORT}/' python3 ${ROOT_DIR}/scripts/ha_label_sungold_solar.py"
fi
