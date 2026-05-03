# victron-ble2mqtt-integration

Bridge Victron BLE advertisements → MQTT with Home Assistant discovery. Designed for Raspberry Pi with BlueZ; publishes entities via [`ha_services`](https://pypi.org/project/ha_services/).

---

## What’s working (verified)

- ✅ BLE scanning on `hci0` (LE-only) is stable.
- ✅ Victron **Solar Charger (VE.Direct SmarT / BlueSolar MPPT 75/15 rev3)** is detected and decoded.
- ✅ MQTT discovery + states arrive in HA (entities like `battery_voltage`, `charge_state`, `solar_power`, etc.).
- ✅ Optional: Dozzle is running and can be used to tail container logs.

See Home Assistant → Settings → Devices & Services → MQTT for discovered entities.



---

## Requirements

- Raspberry Pi with BlueZ (Bluetooth) enabled
- Docker Engine + Compose v2 (installed by deploy script if missing)

## System info publishing (Pi4)

- Previously, Pi system metrics (CPU, temp, load, wifi, etc.) were only published when a BLE packet was decoded and forwarded. If no Victron BLE adverts were seen, these sensors appeared to “stall.”
- Now, a periodic publisher runs inside `override/victron_ble2mqtt/__main__.py`, pushing system metrics at a fixed interval regardless of BLE activity. This makes Pi4 data flow consistently, including right after container start.
- Tuning: `SYSTEM_POLL_THROTTLE_SEC` (default 3s) in `docker-compose.victron.yml`.
- Reboot-proof via systemd runner installed by `scripts/deploy.sh`.

> If you run tails/clients in Docker, set `MQTT_HOST` to the broker’s **LAN IP**, not `localhost`.

---

## Deploy

Run the unified installer:

```bash
sudo bash scripts/deploy.sh
```

It installs prerequisites, configures logging (Docker daemon json-file rotation and journald caps), sets up Mosquitto, starts Home Assistant, and installs the `victron-ble2mqtt` systemd runner.
See `DEPLOY.md` for options and troubleshooting.

**Same LAN as the Alfa cluster?** See [docs/ALFA_CLUSTER_INTEGRATION.md](docs/ALFA_CLUSTER_INTEGRATION.md) for TrueNAS hub usage, cross-links to **alfa-ai**, and **monitoring** (Prometheus / `node_exporter` on the Pi).

---

## Production deployment & tools

Do not commit secrets (ADVKEY_*, MQTT_PASSWORD, etc.). Provide via `.env` or environment-managed secrets.


### VS Code RAM usage on Raspberry Pi

If VS Code Server uses too much memory:

- Use the workspace settings in `.vscode/settings.json` (already included) to reduce indexers and watchers.
- Kill all VS Code Server processes on demand:
  - `bash scripts/kill_vscode_server.sh`
- Automatic cleanup runs every 10 minutes and removes stale VS Code Server processes older than 15 minutes: see `scripts/vscode_server_cleanup.sh` and systemd units `vscode-server-cleanup@.service` and `.timer`.


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

**USB BLE dongle (common fix when the Pi’s built-in radio is weak or busy):** list adapters with `bluetoothctl list`, then put the dongle’s interface in `.env` (e.g. `BLE_ADAPTER=hci1`). Re-run `scripts/redeploy_victron.sh` or `deploy.sh` so the container picks it up; startup logs include `BLE scanner using adapter hci1`. Scan with the same index: `sudo btmgmt -i hci1 find -l`. Point **Home Assistant** at the other adapter (Settings → Bluetooth) if you want HA on built-in and Victron on the dongle.

If you have a second adapter you are **not** using for Victron, you can power it off to reduce noise:

sudo btmgmt -i hci1 power off

2) Watch MQTT

From the Pi:

mosquitto_sub -h "$MQTT_HOST" -p "${MQTT_PORT:-1883}" -u "$MQTT_USER" -P "$MQTT_PASSWORD" -v \
  -t 'homeassistant/#' -t 'victron_ble/#'


If you prefer Docker tailing + Dozzle, run your own small alpine container with mosquitto_sub and view logs in Dozzle.

Home Assistant

Go to Settings → Devices & Services → MQTT.

The device should appear under your host device.

Entities include: battery_voltage, battery_charging_current, charge_state, solar_power, charging_power, load, load_power, yield_today, and an rssi sensor.

Troubleshooting

Discovery config but no states

Ensure the Victron app is closed.

Re-check VICTRON_DEVICE_KEYS formatting and MACs.

Confirm adverts show up during btmgmt find -l while the publisher runs.

Docker tails show “Lookup error”

MQTT_HOST was a placeholder/comment. Set it to the broker’s LAN IP.

Notes
- The deploy script can repair a malformed `/etc/docker/daemon.json` and restart Docker safely.
- The systemd unit starts bluetooth safely before running the container (no forced restart).

License

MIT (or the project’s existing license).


::contentReference[oaicite:0]{index=0}
