Quick deploy instructions

Preconditions (on the host):
- Docker and Docker Compose (or Docker Compose plugin) installed
- You have a `.env` file in the repo root with required values (MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, MAIN_UID, optionally ADVKEY_...)

Steps (copy/paste):

1) Clone the repo and ensure `.env` is present

   git clone https://github.com/curtalfrey/victron-ble2mqtt-integration.git
   cd victron-ble2mqtt-integration
   cp config/user_settings.example.py user_settings.local.py # optional

2) Build and run

   ./scripts/deploy_local.sh

3) Verify

   docker ps --filter name=victron_ble2mqtt
   docker logs -f victron_ble2mqtt

Notes:
- The container uses host networking to access Bluetooth and MQTT in the LAN (see `docker-compose.victron.yml`).
- If you prefer a prebuilt image, push to GHCR and update `docker-compose.victron.yml` to pull the image.

Troubleshooting:
- If the container fails to start, check `docker logs -f victron_ble2mqtt` for errors (missing ADVKEY, MQTT auth errors, missing device files).
- Ensure the host has BlueZ installed for BLE scanning.

Network failover (eth0 -> wlan0):
- Ensure Wi‑Fi credentials are present in `.env` as WIFI_SSID/WIFI_PASSWORD or saved in NetworkManager.
- The deploy script prefers Ethernet and falls back to Wi‑Fi automatically via route metrics.
- Optional watchdog to keep Wi‑Fi up when Ethernet drops:
   1. Install unit: `sudo install -m 644 systemd/wifi-failover-monitor.service /etc/systemd/system/wifi-failover-monitor@.service`
   2. Reload: `sudo systemctl daemon-reload`
   3. Enable: `sudo systemctl enable --now wifi-failover-monitor@<user>.service`
   4. Logs: `journalctl -u wifi-failover-monitor@<user>.service -f`
