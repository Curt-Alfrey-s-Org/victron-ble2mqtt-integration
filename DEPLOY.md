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
