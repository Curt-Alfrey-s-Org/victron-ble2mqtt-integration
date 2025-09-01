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

1) Clone the repo and ensure `.env` is present

   git clone https://github.com/curtalfrey/victron-ble2mqtt-integration.git
   cd victron-ble2mqtt-integration
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

Notes:
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
