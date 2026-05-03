Quick deploy (recommended)

Preconditions (on the host):
- Debian/Raspberry Pi OS host with sudo
- Network access and Bluetooth enabled (BlueZ)
- Optional: `.env` with MQTT creds and ADVKEY_* (script will prompt/create placeholders if missing)

What the installer does (idempotent):
- Installs Docker Engine + Compose plugin if missing and enables the service
- Configures safe Docker logging defaults globally (json-file with rotation 10MB x3)
   - If `/etc/docker/daemon.json` is malformed, it will be backed up, rewritten with valid JSON, and Docker will be restarted
- Sets journald caps (disk/RAM) and logrotate for app/HA logs
- Installs Mosquitto (broker + clients) and configures auth if MQTT_USER/MQTT_PASSWORD are set
- Builds the app image and installs a systemd runner (`victron-ble2mqtt.service`)
   - The service safely starts bluetooth (no forced restart) and waits briefly before running
- Starts Home Assistant (host network) and optional helper timers (docker prune, MQTT watchdog, VS Code cleanup)

Steps (copy/paste):

### Fresh Raspberry Pi OS (optional one-shot)

As a **non-root** user with `sudo` (updates OS, installs `git`, clones or pulls this repo, seeds optional `swarm/*.env`, then runs deploy):

```bash
bash scripts/bootstrap_pi4_victron_ble2mqtt_integration.sh
```

1) Clone the repo and create `.env` for MQTT (and optional Wi‑Fi / tools)

   git clone https://github.com/curtalfrey/victron-ble2mqtt-integration.git
   cd victron-ble2mqtt-integration
   cp -n dotenv.sample .env && chmod 600 .env   # then edit: MQTT_USER, MQTT_PASSWORD
   # ADVKEY_* may live in .env **or** ./victron-secrets.env — if both set the same
   # variable, **.env wins** (see scripts/redeploy_victron.sh). Prefer victron-secrets.env
   # for keys only (chmod 600); deploy creates empty placeholders there on first run.
   # Or run deploy once — it creates/appends MQTT_* lines if `.env` is missing or has no MQTT_USER=.
   cp config/user_settings.example.py user_settings.local.py # optional

2) Build and run (unified installer)

   sudo bash scripts/deploy.sh

   # Optional features via env flags (set before running):
   # ENABLE_PERF_TUNING=1     # apply systemd+udev performance tweaks
   # ENABLE_TOOLS=1           # enable tools stack via systemd (docker-compose.tools.yml)
   # ENABLE_FAILOVER_MONITOR=1# enable Wi‑Fi failover monitor@user service
   # FORCE_HA_MQTT_YAML=1     # write HA mqtt.yaml and include it

3) Verify

   docker ps --filter name=victron_ble2mqtt
   docker logs -f victron_ble2mqtt

   If `docker ps` as your normal user says **permission denied**, deploy already added you to the **docker** group — **log out and back in** (or `newgrp docker`) so the socket is usable interactively. The `victron-ble2mqtt.service` unit includes **SupplementaryGroups=docker** so the systemd runner can call Docker without sudo.

Notes:
- **Home Assistant → MQTT:** broker **`127.0.0.1`**, port **`1883`**, same **`MQTT_USER` / `MQTT_PASSWORD` as `.env`**, TLS **off**. Preflight on the Pi: `set -a; . ./.env; set +a` then `mosquitto_sub -h 127.0.0.1 -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t '$SYS/broker/uptime' -C 1` — if that fails, check Mosquitto before the HA UI (`journalctl -u mosquitto -n 40`).
- **Home Assistant → Bluetooth:** the `homeassistant` container gets **`-v /run/dbus:/run/dbus:ro`**, **`--cap-add NET_ADMIN`**, and **`--cap-add NET_RAW`** (required since HA ~2025.9 for adapter recovery / full BlueZ access; see [Bluetooth — Docker](https://www.home-assistant.io/integrations/bluetooth/#requirements-for-linux-systems)). If an older container lacked these, **`sudo bash scripts/deploy.sh`** recreates it (**`/opt/homeassistant`** volume unchanged).
- Uses host networking for Bluetooth and MQTT (see `docker-compose.victron.yml`).
- If you prefer prebuilt images, push to GHCR and adjust compose to pull.
- Logging/operations hardening included:
   - Docker daemon log rotation (10MB x3) via `/etc/docker/daemon.json` (auto-repaired if broken)
   - journald caps and logrotate for app/HA logs
   - Mosquitto logs routed to syslog with reduced verbosity
- Optional automation: HA watchdog, MQTT watchdog, weekly docker prune, VS Code cleanup timer.

Troubleshooting quick wins:
- Docker won’t start after running the installer: check `/etc/docker/daemon.json`. The installer backs up invalid files and writes valid JSON, then restarts Docker.
- `victron-ble2mqtt.service` fails with bluetooth errors: the unit uses `ExecStartPre=-/usr/bin/systemctl start bluetooth` (no hard restart). Verify `bluetoothctl show` reports `Powered: yes`.
- No HA entities after discovery: ensure the Victron app is closed (it can stop adverts), and verify ADVKEY_* values are correct.

Network failover (eth0 -> wlan0):
- Ensure Wi‑Fi credentials are present in `.env` as WIFI_SSID/WIFI_PASSWORD or saved in NetworkManager.
- The deploy script prefers Ethernet and falls back to Wi‑Fi automatically via route metrics.
- Optional watchdog to keep Wi‑Fi up when Ethernet drops:
   1. Install unit: `sudo install -m 644 systemd/wifi-failover-monitor@.service /etc/systemd/system/wifi-failover-monitor@.service`
   2. Reload: `sudo systemctl daemon-reload`
   3. Enable: `sudo systemctl enable --now wifi-failover-monitor@<user>.service`
   4. Logs: `journalctl -u wifi-failover-monitor@<user>.service -f`
