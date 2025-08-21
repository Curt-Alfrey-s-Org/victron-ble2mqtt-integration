# victron-ble2mqtt-integration

Bridge Victron **BLE** advertisements → **MQTT** with Home Assistant discovery.

This repo currently runs on a Raspberry Pi with BlueZ and publishes entities via [`ha_services`](https://pypi.org/project/ha_services/) into Home Assistant’s MQTT discovery.

---

## What’s working (verified)

- ✅ BLE scanning on `hci0` (LE-only) is stable.
- ✅ Victron **Solar Charger (VE.Direct SmarT / BlueSolar MPPT 75/15 rev3)** is detected and decoded.
- ✅ MQTT discovery + states arrive in HA (entities like `battery_voltage`, `charge_state`, `solar_power`, etc.).
- ✅ Optional: Dozzle is running and can be used to tail container logs.

**Example topics observed**



---

## Requirements

- Raspberry Pi with **BlueZ** (Bluetooth) enabled.
- Python 3 (system packages already include `bleak`, `victron_ble`, `ha_services` on the target used here).
- An MQTT broker reachable from the Pi.

> If you run tails/clients in Docker, set `MQTT_HOST` to the broker’s **LAN IP**, not `localhost`.

---

## Configuration

Two env files are used:

- `swarm/ha-discovery.env`
  - `MQTT_HOST` – broker LAN IP (not 127.0.0.1 inside containers)
  - `MQTT_PORT` (default 1883)
  - `MQTT_USER` / `MQTT_PASSWORD`
  - Optional: `PUBLISH_CONFIG_THROTTLE_SEC` (default 60), `MAIN_UID` (defaults to hostname)

- `swarm/victron-secrets.env`
  - `VICTRON_DEVICE_KEYS` – semicolon-separated `MAC=32hex` pairs, e.g.  
    `D4:EF:FB:B3:D7:0C=<32-hex>;CB:0D:C2:0A:AE:0F=<32-hex>;D7:69:EB:1F:F8:3D=<32-hex>`

Ensure the MACs match your devices and the keys are correct.

---

## Production deployment & tools

This repository now includes a production-friendly deployment path using Docker Compose and small systemd runners. See `deploy/README.md` for a full walkthrough. Highlights:

- Docker Compose stacks: `docker-compose.victron.yml` (the main BLE->MQTT service) and `docker-compose.tools.yml` (Portainer, Dozzle, Watchtower, nginx reverse proxy).
- Systemd units: `systemd/victron.service` and a long-running `victron-runner.sh` are included to auto-start and monitor the compose stack on reboot.
- Security: nginx reverse-proxy (TLS + basic auth) sits in front of Portainer/Dozzle; `nginx/.htpasswd` is used for basic auth — rotate the password and replace the self-signed certs before exposing to untrusted networks.
- CI/Images: A GitHub Actions workflow builds multi-arch images and can publish to GHCR; use Buildx or the provided workflow to create arm64 images for Raspberry Pi.

Do not commit secrets (ADVKEY_*, MQTT_PASSWORD, etc.) — they should be provided at runtime via `.env` or environment-managed secrets.


## One-shot debug run

Publishes discovery + live states to MQTT (Ctrl-C to stop):

```bash
cd ~/victron-ble2mqtt-integration
set -a
. swarm/ha-discovery.env
. swarm/victron-secrets.env
set +a
PYTHONPATH="$PWD/override:$PWD/fixes:$PWD" python3 - <<'PY'
from victron_ble2mqtt.cli_app.mqtt import publish_loop
publish_loop(verbosity=3)  # DEBUG
PY

You should see BLE detections and MQTT “CONNECT/CONNACK” logs, followed by discovery/state publishes.

Quick checks
1) Verify Victron devices are advertising

Close the Victron app on your phone (it can suppress adverts), then:

sudo btmgmt -i hci0 power off
sudo btmgmt -i hci0 le on
sudo btmgmt -i hci0 bredr off
sudo btmgmt -i hci0 power on

# Short scan; you should see your device MACs
sudo timeout 25s btmgmt -i hci0 find -l \
 | egrep 'D4:EF:FB:B3:D7:0C|CB:0D:C2:0A:AE:0F|D7:69:EB:1F:F8:3D' || echo 'NO MATCHES'


If you have a second adapter (e.g., hci1) and don’t want it used:

sudo btmgmt -i hci1 power off

2) Watch MQTT

From the Pi:

mosquitto_sub -h "$MQTT_HOST" -p "${MQTT_PORT:-1883}" -u "$MQTT_USER" -P "$MQTT_PASSWORD" -v \
  -t 'homeassistant/#' -t 'victron_ble/#'


If you prefer Docker tailing + Dozzle, run your own small alpine container with mosquitto_sub and view logs in Dozzle.

Home Assistant

Go to Settings → Devices & Services → MQTT.

The device should appear (e.g., VE.Direct SmarT under a device like raspberrypi-d769eb1ff83d).

Entities include: battery_voltage, battery_charging_current, charge_state, solar_power, charging_power, load, load_power, yield_today, and an rssi sensor.

Troubleshooting

Discovery config but no states

Ensure the Victron app is closed.

Re-check VICTRON_DEVICE_KEYS formatting and MACs.

Confirm adverts show up during btmgmt find -l while the publisher runs.

Docker tails show “Lookup error”

MQTT_HOST was a placeholder/comment. Set it to the broker’s LAN IP.

Local note (temporary override)

We added this import to keep detection working with current libs:

# override/victron_ble2mqtt/victron_ble_utils.py
from victron_ble.devices import detect_device_type


This can be revisited if the upstream dependency changes.

License

MIT (or the project’s existing license).


::contentReference[oaicite:0]{index=0}
