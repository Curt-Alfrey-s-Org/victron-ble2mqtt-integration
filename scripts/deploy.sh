#!/usr/bin/env bash
# Unified, idempotent deployment for victron-ble2mqtt-integration
# - Verifies and installs prerequisites (Docker, Compose, BlueZ, Mosquitto)
# - Renders and enables a systemd runner that manages the container via scripts/redeploy_victron.sh
# - Builds image and ensures Home Assistant is running
# - Optional extras via env: ENABLE_PERF_TUNING=1, ENABLE_TOOLS=1, ENABLE_FAILOVER_MONITOR=1, FORCE_HA_MQTT_YAML=1
set -Eeuo pipefail
IFS=$'\n\t'

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

# --- trap for helpful errors ---
trap 'rc=$?; echo "[deploy] Failed at line $LINENO (exit=$rc)" >&2; exit $rc' ERR

# --- ensure .env exists for MQTT_* (Mosquitto auth, HA MQTT integration, redeploy_victron.sh) ---
ensure_dotenv_for_mqtt() {
  local touched=false
  if [[ ! -f ./.env ]]; then
    if [[ -f ./dotenv.sample ]]; then
      echo "[deploy] Creating .env from dotenv.sample (set MQTT_USER / MQTT_PASSWORD, then re-run deploy if Mosquitto already configured)."
      cp ./dotenv.sample ./.env
    elif [[ -f ./.env.sample ]]; then
      echo "[deploy] Creating .env from .env.sample (set MQTT_USER / MQTT_PASSWORD, then re-run deploy if Mosquitto already configured)."
      cp ./.env.sample ./.env
    else
      echo "[deploy] Creating .env with MQTT placeholders (dotenv.sample missing from checkout)."
      cat > ./.env <<'EOS'
# MQTT broker settings for Mosquitto, Home Assistant, and the victron_ble2mqtt container.
# Use the Pi's real LAN IP (from `hostname -I`) instead of localhost/127.0.0.1 for reliable connectivity.
# The new deploy verification will fail loudly if Mosquitto cannot bind port 1883 or auth fails.
MQTT_HOST=192.168.0.XX
MQTT_PORT=1883
MQTT_USER=victron
MQTT_PASSWORD=your_secure_password_here
EOS
    fi
    touched=true
  elif ! grep -qE '^[[:space:]]*MQTT_USER=' ./.env 2>/dev/null; then
    echo "[deploy] Appending MQTT_* placeholders to .env (set MQTT_USER / MQTT_PASSWORD)."
    {
      echo ""
      echo "# MQTT — Home Assistant + victron (added by deploy.sh)"
      echo "MQTT_HOST=127.0.0.1"
      echo "MQTT_PORT=1883"
      echo "MQTT_USER="
      echo "MQTT_PASSWORD="
    } >> ./.env
    touched=true
  fi
  if [[ "$touched" == true ]]; then
    chmod 600 ./.env 2>/dev/null || true
  fi
}
ensure_dotenv_for_mqtt

# --- load env if present ---
if [[ -f ./.env ]]; then set -a; . ./.env; set +a; fi

# Force a real LAN IP for MQTT_HOST if it is still localhost/127.0.0.1.
# This is critical for the container to reach the broker when using network_mode: host.
if [[ "${MQTT_HOST:-}" == "localhost" || "${MQTT_HOST:-}" == "127.0.0.1" || -z "${MQTT_HOST:-}" ]]; then
  LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || echo '')"
  if [[ -n "$LAN_IP" && "$LAN_IP" != "127.0.0.1" ]]; then
    echo "[deploy] Setting MQTT_HOST=${LAN_IP} in .env (Pi LAN IP). Edit .env to change."
    sed -i "s/^MQTT_HOST=.*/MQTT_HOST=${LAN_IP}/" ./.env 2>/dev/null || echo "MQTT_HOST=${LAN_IP}" >> ./.env
    MQTT_HOST="$LAN_IP"
  fi
fi

: "${MQTT_HOST:=127.0.0.1}"
: "${MQTT_PORT:=1883}"
: "${FORCE_HA_MQTT_YAML:=0}"
: "${ENABLE_HA_WATCHDOG:=1}"
: "${ENABLE_TOOLS:=1}"
: "${ENABLE_VSCODE_CLEANUP:=1}"
: "${ENABLE_UNATTENDED_UPGRADES:=0}"
: "${ENABLE_DOCKER_PRUNE:=1}"
: "${ENABLE_MQTT_WATCHDOG:=1}"

need_cmd() { command -v "$1" >/dev/null 2>&1; }

apt_install() {
  local pkgs=("$@")
  if ! need_cmd apt-get; then
    echo "[deploy] apt-get not available; install ${pkgs[*]} manually." >&2
    return 1
  fi
  sudo apt-get update -y
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${pkgs[@]}"
}

ensure_group_member() {
  local user="$1" group="$2"
  if ! id -nG "$user" | grep -qw "$group"; then
    echo "[deploy] Adding $user to $group group..."
    sudo usermod -aG "$group" "$user" || true
    echo "[deploy] New group membership requires a new login shell. Re-run after 'newgrp $group' if needed."
  fi
}

ensure_service_active() {
  local svc="$1"
  sudo systemctl enable --now "$svc" 2>/dev/null || sudo systemctl restart "$svc" 2>/dev/null || true
}

# Mosquitto: do not swallow start failures (ensure_service_active alone can hide a broken config).
mosquitto_restart_and_verify() {
  echo "[deploy] Restarting and verifying Mosquitto (listener on port ${MQTT_PORT} + auth)..."
  sudo systemctl restart mosquitto
  sleep 3
  if ! systemctl is-active --quiet mosquitto; then
    echo "[deploy] ERROR: mosquitto.service failed to start." >&2
    sudo systemctl --no-pager -l status mosquitto >&2
    sudo journalctl -u mosquitto -n 80 --no-pager >&2
    exit 1
  fi
  if ! ss -lntp 2>/dev/null | grep -qE ":${MQTT_PORT}\\b.*mosquitto"; then
    echo "[deploy] ERROR: no listener on TCP port ${MQTT_PORT} (check config or firewall)." >&2
    sudo journalctl -u mosquitto -n 60 --no-pager >&2
    exit 1
  fi
  local sub_args=("-h" "127.0.0.1" "-p" "${MQTT_PORT}" "-t" '$SYS/broker/uptime' "-C" "1" "-W" "10")
  if [[ -n "${MQTT_USER:-}" && -n "${MQTT_PASSWORD:-}" ]]; then
    sub_args+=("-u" "$MQTT_USER" "-P" "$MQTT_PASSWORD")
  fi
  if ! mosquitto_sub "${sub_args[@]}" >/dev/null 2>&1; then
    echo "[deploy] ERROR: subscribe test failed (wrong credentials or broker not ready)." >&2
    sudo journalctl -u mosquitto -n 30 --no-pager >&2
    exit 1
  fi
  echo "[deploy] Mosquitto OK (listening on ${MQTT_PORT}, subscribe test passed)."
}

render_unit_with_user_path() {
  local src="$1" dst="$2"
  local user="${SUDO_USER:-$USER}"
  local home
  home="$(getent passwd "$user" | awk -F: '{print $6}')"
  if [[ -z "$home" ]]; then home="$HOME"; fi
  mkdir -p "$(dirname "$dst")"
  sed -e "s#/home/user1#$home#g" \
      -e "s#User=user1#User=$user#g" \
      -e "s#Group=user1#Group=$user#g" \
      "$src" | sudo tee "$dst" >/dev/null
}

file_has_line() { local f="$1"; shift; local pattern="$*"; grep -Fqx "$pattern" "$f" 2>/dev/null; }

# ------------------------------------------------------------
# 1) Base prerequisites: sudo, curl, Docker, Compose plugin, Mosquitto tools
# ------------------------------------------------------------
if ! need_cmd sudo; then echo "[deploy] sudo is required" >&2; exit 1; fi

if ! need_cmd curl; then apt_install curl ca-certificates gnupg || true; fi

if ! need_cmd docker; then
  echo "[deploy] Installing Docker (docker.io)..."
  apt_install docker.io || true
  ensure_service_active docker
fi

# Docker Compose v2 plugin preferred; fallback to docker-compose
if ! docker compose version >/dev/null 2>&1; then
  if ! need_cmd docker-compose; then
    echo "[deploy] Installing docker compose plugin..."
    apt_install docker-compose-plugin || apt_install docker-compose || true
  fi
fi

ensure_group_member "${SUDO_USER:-$USER}" docker

# Mosquitto broker + clients (for local broker default)
if ! need_cmd mosquitto; then
  echo "[deploy] Installing Mosquitto broker & clients..."
  apt_install mosquitto mosquitto-clients || true
fi
ensure_service_active mosquitto

# Sync Wi‑Fi lines into .env *before* Mosquitto password/listener so .env is complete
# (setup_wifi_env rewrites .env while preserving MQTT_* / ADVKEY_* lines).
if [[ -x "$ROOT_DIR/scripts/setup_wifi_env.sh" ]]; then
  bash "$ROOT_DIR/scripts/setup_wifi_env.sh" || true
fi
if [[ -f ./.env ]]; then set -a; . ./.env; set +a; fi

# Configure listener if not present; prefer auth if creds provided
# per_listener_settings true avoids Mosquitto 2.x binding a stray default :1883
# when password_file/listener options are split across include snippets.
MOSQ_DIR="/etc/mosquitto"
MOSQ_CONF_DIR="$MOSQ_DIR/conf.d"
sudo mkdir -p "$MOSQ_CONF_DIR"
AUTH_CONF="$MOSQ_CONF_DIR/10-auth.conf"
ALLOW_ALL_CONF="$MOSQ_CONF_DIR/00-allow-all.conf"
if [[ -n "${MQTT_USER:-}" && -n "${MQTT_PASSWORD:-}" ]]; then
  echo "[deploy] Configuring Mosquitto with password auth..."
  sudo rm -f "$ALLOW_ALL_CONF" 2>/dev/null || true
  sudo bash -lc "set -e; mosquitto_passwd -b -c /etc/mosquitto/passwd '$MQTT_USER' '$MQTT_PASSWORD'"
  sudo bash -lc "cat > '$AUTH_CONF' <<CONF
per_listener_settings true
listener ${MQTT_PORT} 0.0.0.0
protocol mqtt
allow_anonymous false
password_file /etc/mosquitto/passwd
log_type error
log_type warning
log_type notice
# keep logs small; systemd/journald caps will also apply
log_dest syslog
CONF"
else
  if [[ ! -f "$ALLOW_ALL_CONF" ]]; then
    echo "[deploy] Configuring Mosquitto (anonymous allowed on ${MQTT_PORT})..."
  sudo bash -lc "cat > '$ALLOW_ALL_CONF' <<CONF
per_listener_settings true
listener ${MQTT_PORT} 0.0.0.0
protocol mqtt
allow_anonymous true
log_type error
log_type warning
log_type notice
log_dest syslog
CONF"
  fi
fi

# mqtt-watchdog.timer uses mosquitto_sub; when allow_anonymous is false it must use credentials.
if [[ -n "${MQTT_USER:-}" && -n "${MQTT_PASSWORD:-}" ]]; then
  sudo tee /etc/mosquitto/watchdog.env >/dev/null <<EOF
MQTT_PORT=${MQTT_PORT}
MQTT_USER=${MQTT_USER@Q}
MQTT_PASSWORD=${MQTT_PASSWORD@Q}
EOF
  sudo chmod 600 /etc/mosquitto/watchdog.env
else
  sudo tee /etc/mosquitto/watchdog.env >/dev/null <<EOF
MQTT_PORT=${MQTT_PORT}
EOF
  sudo chmod 644 /etc/mosquitto/watchdog.env
fi

# Ensure main config includes the conf.d directory (critical on Debian/RPi for Mosquitto 2.x)
if ! grep -q 'include_dir /etc/mosquitto/conf.d' /etc/mosquitto/mosquitto.conf 2>/dev/null; then
  echo "[deploy] Adding include_dir for conf.d to main mosquitto.conf"
  echo 'include_dir /etc/mosquitto/conf.d' | sudo tee -a /etc/mosquitto/mosquitto.conf >/dev/null
fi

mosquitto_restart_and_verify

# ------------------------------------------------------------
# journald caps to prevent RAM/disk bloat
# ------------------------------------------------------------
JOUR_DIR="/etc/systemd/journald.conf.d"
sudo mkdir -p "$JOUR_DIR"
sudo bash -lc "cat > '$JOUR_DIR/99-victron.conf' <<JCONF
[Journal]
SystemMaxUse=200M
RuntimeMaxUse=100M
MaxRetentionSec=1month
RateLimitIntervalSec=30s
RateLimitBurst=1000
JCONF"
sudo systemctl restart systemd-journald || true

# ------------------------------------------------------------
# Docker daemon default log rotation (applies to all containers)
# ------------------------------------------------------------
DOCKER_DAEMON_JSON=/etc/docker/daemon.json
# Write/repair daemon.json if missing or invalid
ensure_docker_daemon_json() {
  local tmp
  tmp="$(mktemp)"
  cat >"$tmp" <<'DJSON'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
DJSON

  # If file missing, write fresh
  if [[ ! -f "$DOCKER_DAEMON_JSON" ]]; then
    echo "[deploy] Writing Docker daemon log defaults (10m x3) ..."
    sudo install -o root -g root -m 0644 "$tmp" "$DOCKER_DAEMON_JSON"
    return 0
  fi

  # If existing content clearly invalid (unquoted keys) or missing required keys, back up and replace
  if ! grep -q '"log-driver"' "$DOCKER_DAEMON_JSON" ||
     ! grep -q '"log-opts"' "$DOCKER_DAEMON_JSON" ||
     grep -qE '(^|[\{,[:space:]])log-driver\s*:' "$DOCKER_DAEMON_JSON"; then
    echo "[deploy] Repairing invalid $DOCKER_DAEMON_JSON (backing up and replacing) ..."
    sudo cp -a "$DOCKER_DAEMON_JSON" "$DOCKER_DAEMON_JSON.bak.$(date +%s)" || true
    sudo install -o root -g root -m 0644 "$tmp" "$DOCKER_DAEMON_JSON"
  fi
}

ensure_docker_daemon_json
ensure_service_active docker
# Try restart; if it fails due to config, quarantine the file and start with defaults
if ! sudo systemctl restart docker; then
  echo "[deploy] Docker failed to restart; quarantining $DOCKER_DAEMON_JSON and retrying ..." >&2
  sudo mv -f "$DOCKER_DAEMON_JSON" "$DOCKER_DAEMON_JSON.broken.$(date +%s)" || true
  sudo systemctl restart docker || true
fi

# ------------------------------------------------------------
# Logrotate for app and HA logs
# ------------------------------------------------------------
if ! need_cmd logrotate; then apt_install logrotate || true; fi
sudo bash -lc "cat > /etc/logrotate.d/victron_ble2mqtt <<LROT
/var/log/victron_ble2mqtt.log {
  size 5M
  rotate 7
  compress
  copytruncate
  missingok
}
LROT"
sudo bash -lc "cat > /etc/logrotate.d/homeassistant <<LROT
/opt/homeassistant/home-assistant.log {
  size 10M
  rotate 7
  compress
  copytruncate
  missingok
}
LROT"
# Ensure logrotate timer is active
ensure_service_active logrotate.timer || true

# ------------------------------------------------------------
# 2) Host BLE stack readiness (BlueZ, dbus, rfkill, bluetoothd)
# ------------------------------------------------------------
if ! need_cmd bluetoothctl; then
  echo "[deploy] Installing BlueZ..."
  apt_install bluez rfkill dbus || true
fi
ensure_service_active bluetooth || true
sudo rfkill unblock bluetooth || true

# ------------------------------------------------------------
# 3) Optional performance/network tuning
# ------------------------------------------------------------
if [[ "${ENABLE_PERF_TUNING:-0}" == "1" ]]; then
  echo "[deploy] Applying performance tuning (systemd + udev) ..."
  bash "$ROOT_DIR/scripts/apply_max_performance.sh" || true
fi

# ------------------------------------------------------------
# 4) Build image and prepare runtime files
# ------------------------------------------------------------
if [[ ! -f requirements.txt ]]; then echo "[deploy] requirements.txt missing" >&2; exit 1; fi
if [[ ! -f victron-secrets.env ]]; then
  echo "[deploy] Creating placeholder victron-secrets.env (edit ADVKEY_* values; or set ADVKEY_* in .env — .env overrides this file)"
  cat > victron-secrets.env <<'ENV'
# ADVKEY placeholders (32-hex). Update with your device keys.
ADVKEY_BATTERY_1=
ADVKEY_BATTERY_2=
ADVKEY_SOLAR_CONTROLLER=
ENV
fi

# Log file for container bind mount
sudo touch /var/log/victron_ble2mqtt.log
sudo chown "${SUDO_USER:-$USER}":"${SUDO_USER:-$USER}" /var/log/victron_ble2mqtt.log || true

echo "[deploy] Building Docker image (victron_ble2mqtt:local) ..."
DOCKER_BUILDKIT=1 docker build -t victron_ble2mqtt:local .

# ------------------------------------------------------------
# 5) Render and enable systemd runner for persistence
# ------------------------------------------------------------
UNIT_SRC="$ROOT_DIR/systemd/victron-ble2mqtt.service"
UNIT_DST="/etc/systemd/system/victron-ble2mqtt.service"
RUNNER_SH="$ROOT_DIR/systemd/victron-runner.sh"
sudo chmod +x "$RUNNER_SH" || true
echo "[deploy] Installing systemd unit -> $UNIT_DST"
render_unit_with_user_path "$UNIT_SRC" "$UNIT_DST"
sudo systemctl daemon-reload
sudo systemctl enable --now victron-ble2mqtt.service

# Optional tools compose (Dozzle/Portainer/Watchtower)
if [[ "${ENABLE_TOOLS}" == "1" ]]; then
  if [[ -f "$ROOT_DIR/systemd/victron-tools.service" ]]; then
    echo "[deploy] Enabling victron-tools.service ..."
    render_unit_with_user_path "$ROOT_DIR/systemd/victron-tools.service" /etc/systemd/system/victron-tools.service
    sudo systemctl daemon-reload
    sudo systemctl enable --now victron-tools.service || true
  fi
fi

# Optional: Wi‑Fi failover monitor
if [[ "${ENABLE_FAILOVER_MONITOR:-0}" == "1" ]]; then
  if [[ -f "$ROOT_DIR/systemd/wifi-failover-monitor@.service" ]]; then
    echo "[deploy] Enabling wifi-failover-monitor@${SUDO_USER:-$USER}.service ..."
    sudo install -m 0644 -D "$ROOT_DIR/systemd/wifi-failover-monitor@.service" /etc/systemd/system/wifi-failover-monitor@.service
    sudo systemctl daemon-reload
    sudo systemctl enable --now "wifi-failover-monitor@${SUDO_USER:-$USER}.service" || true
  fi
fi

# Home Assistant availability watchdog (default on)
if [[ "${ENABLE_HA_WATCHDOG}" == "1" ]]; then
  if [[ -f "$ROOT_DIR/scripts/ha-watchdog.sh" && -f "$ROOT_DIR/systemd/ha-watchdog.service" && -f "$ROOT_DIR/systemd/ha-watchdog.timer" ]]; then
    echo "[deploy] Installing HA watchdog service + timer ..."
    sudo install -m 0755 -D "$ROOT_DIR/scripts/ha-watchdog.sh" /usr/local/bin/ha-watchdog.sh
    sudo install -m 0644 -D "$ROOT_DIR/systemd/ha-watchdog.service" /etc/systemd/system/ha-watchdog.service
    sudo install -m 0644 -D "$ROOT_DIR/systemd/ha-watchdog.timer" /etc/systemd/system/ha-watchdog.timer
    sudo systemctl daemon-reload
    sudo systemctl enable --now ha-watchdog.timer || true
  fi
fi

# VS Code server cleanup timer (optional, default on)
if [[ "${ENABLE_VSCODE_CLEANUP}" == "1" ]]; then
  if [[ -f "$ROOT_DIR/systemd/vscode-server-cleanup.service" && -f "$ROOT_DIR/systemd/vscode-server-cleanup.timer" && -f "$ROOT_DIR/scripts/vscode_server_cleanup.sh" ]]; then
    echo "[deploy] Installing VS Code cleanup timer ..."
    sudo install -m 0755 -D "$ROOT_DIR/scripts/vscode_server_cleanup.sh" /usr/local/bin/vscode-server-cleanup.sh
    render_unit_with_user_path "$ROOT_DIR/systemd/vscode-server-cleanup.service" /etc/systemd/system/vscode-server-cleanup.service
    sudo install -m 0644 -D "$ROOT_DIR/systemd/vscode-server-cleanup.timer" /etc/systemd/system/vscode-server-cleanup.timer
    sudo systemctl daemon-reload
    sudo systemctl enable --now vscode-server-cleanup.timer || true
  fi
fi

# Unattended upgrades (security only, no auto-reboot) – optional
if [[ "${ENABLE_UNATTENDED_UPGRADES}" == "1" ]]; then
  echo "[deploy] Enabling unattended-upgrades (security only) ..."
  apt_install unattended-upgrades || true
  # Security origins only, do not reboot automatically
  sudo bash -lc "cat > /etc/apt/apt.conf.d/51-victron-unattended <<CFG
Unattended-Upgrade::Origins-Pattern {
    "origin=Debian,codename=",
    "origin=Debian,codename=,label=Debian-Security";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-New-Unused-Dependencies "true";
CFG"
  ensure_service_active unattended-upgrades || true
  ensure_service_active apt-daily.timer || true
  ensure_service_active apt-daily-upgrade.timer || true
fi

# Docker prune (weekly) – optional, conservative retention
if [[ "${ENABLE_DOCKER_PRUNE}" == "1" ]]; then
  echo "[deploy] Installing docker prune weekly timer ..."
  sudo bash -lc "cat > /etc/systemd/system/docker-prune.service <<UNIT
[Unit]
Description=Docker prune (images/containers/volumes) with retention window

[Service]
Type=oneshot
ExecStart=/usr/bin/bash -lc 'docker image prune -af --filter \"until=240h\"; docker container prune -f --filter \"until=240h\"; docker volume prune -f'
UNIT"
  sudo bash -lc "cat > /etc/systemd/system/docker-prune.timer <<UNIT
[Unit]
Description=Run docker-prune.service weekly

[Timer]
OnCalendar=weekly
Persistent=true

[Install]
WantedBy=timers.target
UNIT"
  sudo systemctl daemon-reload
  sudo systemctl enable --now docker-prune.timer || true
fi

# MQTT broker watchdog (minute) – optional
if [[ "${ENABLE_MQTT_WATCHDOG}" == "1" ]]; then
  echo "[deploy] Installing MQTT watchdog timer ..."
  # Do not nest this heredoc inside sudo bash -lc "..." — deploy.sh has set -u and
  # would expand "$HOST"/"$PORT" from the outer shell before the heredoc is written.
  sudo tee /usr/local/bin/mqtt-watchdog.sh >/dev/null <<'WDOG'
#!/usr/bin/env bash
set -euo pipefail
HOST=127.0.0.1
PORT=1883
if [[ -f /etc/mosquitto/watchdog.env ]]; then
  set -a
  # shellcheck disable=SC1090
  . /etc/mosquitto/watchdog.env
  set +a
  PORT="${MQTT_PORT:-1883}"
fi
args=(-h "$HOST" -p "$PORT")
if [[ -n "${MQTT_USER:-}" && -n "${MQTT_PASSWORD:-}" ]]; then
  args+=(-u "$MQTT_USER" -P "$MQTT_PASSWORD")
fi
args+=(-t '$SYS/broker/uptime' -C 1 -W 8)
if mosquitto_sub "${args[@]}" >/dev/null 2>&1; then
  exit 0
fi
logger -t mqtt-watchdog 'Mosquitto unresponsive; restarting'
systemctl restart mosquitto || true
WDOG
  sudo chmod +x /usr/local/bin/mqtt-watchdog.sh
  sudo bash -lc "cat > /etc/systemd/system/mqtt-watchdog.service <<UNIT
[Unit]
Description=MQTT broker watchdog
After=mosquitto.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/mqtt-watchdog.sh
UNIT"
  sudo bash -lc "cat > /etc/systemd/system/mqtt-watchdog.timer <<UNIT
[Unit]
Description=Run MQTT watchdog every minute

[Timer]
OnBootSec=1min
OnUnitActiveSec=1min
Persistent=true

[Install]
WantedBy=timers.target
UNIT"
  sudo systemctl daemon-reload
  sudo systemctl enable --now mqtt-watchdog.timer || true
fi
# ------------------------------------------------------------
# 6) Home Assistant container (host network)
# ------------------------------------------------------------
HA_TZ="${TZ:-America/Chicago}"
HA_CONFIG_DIR="/opt/homeassistant"
sudo mkdir -p "$HA_CONFIG_DIR"
sudo chown -R "${SUDO_USER:-$USER}":"${SUDO_USER:-$USER}" "$HA_CONFIG_DIR" || true
if [[ ! -f "$HA_CONFIG_DIR/configuration.yaml" ]]; then
  cat > "$HA_CONFIG_DIR/configuration.yaml" <<YAML
homeassistant:
  time_zone: ${HA_TZ}
YAML
fi

if [[ "${FORCE_HA_MQTT_YAML}" == "1" ]]; then
  if ! grep -q '^mqtt:' "$HA_CONFIG_DIR/configuration.yaml" 2>/dev/null; then
    printf '%s\n' 'mqtt: !include mqtt.yaml' >> "$HA_CONFIG_DIR/configuration.yaml"
  fi
  cat > "$HA_CONFIG_DIR/mqtt.yaml" <<MQTTYAML
broker: 127.0.0.1
port: ${MQTT_PORT}
${MQTT_USER:+username: ${MQTT_USER}}
${MQTT_PASSWORD:+password: ${MQTT_PASSWORD}}
discovery: true
keepalive: 60
MQTTYAML
fi

# Bluetooth on HA Container: D-Bus + caps (see HA repairs / habluetooth.manager).
# https://www.home-assistant.io/integrations/bluetooth/#requirements-for-linux-systems
ha_homeassistant_bluetooth_ok() {
  docker inspect homeassistant -f '{{range $m := .Mounts}}{{println $m.Destination}}{{end}}' 2>/dev/null | grep -q '^/run/dbus$' || return 1
  local caps
  caps="$(docker inspect homeassistant -f '{{range .HostConfig.CapAdd}}{{.}} {{end}}' 2>/dev/null || true)"
  [[ "$caps" == *NET_ADMIN* ]] || return 1
  [[ "$caps" == *NET_RAW* ]] || return 1
  return 0
}

if docker ps -a --format '{{.Names}}' | grep -qw homeassistant; then
  if ! ha_homeassistant_bluetooth_ok; then
    echo "[deploy] Recreating homeassistant container (Bluetooth: /run/dbus + NET_ADMIN/NET_RAW per HA docs)..."
    docker rm -f homeassistant >/dev/null 2>&1 || true
  fi
fi

if docker ps -a --format '{{.Names}}' | grep -qw homeassistant; then
  docker start homeassistant >/dev/null || true
else
  docker run -d --name homeassistant --restart unless-stopped \
  --log-driver json-file --log-opt max-size=10m --log-opt max-file=5 \
  --network host -e TZ="$HA_TZ" \
  --cap-add NET_ADMIN --cap-add NET_RAW \
  -v "$HA_CONFIG_DIR":/config \
  -v /run/dbus:/run/dbus:ro \
    ghcr.io/home-assistant/home-assistant:stable >/dev/null
fi

if docker ps --format '{{.Names}}' | grep -qw homeassistant; then
  docker restart homeassistant >/dev/null || true
fi

echo "[deploy] Waiting for Home Assistant on http://localhost:8123 ..."
for i in {1..30}; do
  if curl -fsS http://localhost:8123 >/dev/null 2>&1; then
    echo "[deploy] Home Assistant is up."
    break
  fi
  sleep 2
done

# ------------------------------------------------------------
# 7) Quick sanity: show container status and recent logs snippet
# ------------------------------------------------------------
echo "[deploy] Container status:"
docker ps --format '{{.Names}}\t{{.Status}}' | egrep 'victron|homeassistant' || true

echo "[deploy] victron_ble2mqtt env (sanitized — passwords and ADVKEY hex hidden):"
# Config.Env may list the same key twice (--env-file placeholders + -e from redeploy).
# Last assignment wins at runtime; dedupe so this summary matches what the process sees.
if docker ps -a --format '{{.Names}}' | grep -qw victron_ble2mqtt; then
  docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' victron_ble2mqtt 2>/dev/null \
    | egrep '^(MQTT_|ADVKEY_|BLE_ADAPTER|VICTRON_BLE_ADAPTER)' | tac | awk -F= '!seen[$1]++' | tac \
  | while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" ]] && continue
    k="${line%%=*}"
    v="${line#*=}"
    case "$k" in
      MQTT_PASSWORD)
        if [[ -n "$v" ]]; then echo "MQTT_PASSWORD=(set, hidden)"; else echo "MQTT_PASSWORD=(empty)"; fi
        ;;
      ADVKEY_*)
        vl=${#v}
        if [[ "$vl" -eq 0 ]]; then echo "${k}=(empty)"
        elif [[ "$vl" -eq 32 ]]; then echo "${k}=(32 hex chars, hidden)"
        else echo "${k}=(length ${vl}, hidden)"; fi
        ;;
      *) printf '%s\n' "$line" ;;
    esac
  done || true
else
  echo "(victron_ble2mqtt container not present)"
fi

echo "[deploy] Tail victron_ble2mqtt logs: docker logs -f victron_ble2mqtt"
echo "[deploy] Done."
