# Node-RED solar diagram (`.105`)

HA stays authoritative for sensors. Node-RED reads HA and provides the **editable** diagram canvas.

## One-time setup

1. `cd /home/ansible/victron-ble2mqtt-integration`
2. `bash scripts/setup-nodered-solar-env.sh` (HA token from alfa-ai secrets + NR admin hash), or copy `nodered.env.example` manually.
3. `bash scripts/deploy-nodered-solar.sh  # systemd user nodered-solar.service on :1880`
4. Open **http://192.168.0.105:1880/** (Tailscale: same port on the `.105` name).

ufw (if enabled): allow LAN `1880/tcp` from `192.168.0.0/24` only.


## Panel strings (diagram tab, operator 2026-10-02)

Physical layout is **three strings** (PWM and third 75/15 retired):

| String | Bus | Charger | Panels |
|--------|-----|---------|--------|
| 2s3p | T2 | SmartSolar MPPT **100/50** | six panels -- **no HA entities** until VictronConnect Instant Readout key |
| 2p Renogy | KU | second BlueSolar **75/15** | two 24 V Renogy panels parallel -- **pending key** |
| 2s suitcase | KU | paired BlueSolar **75/15** (`sensor.solar_controller_*`) | two suitcase panels series -- which KU string is on the paired unit is **unconfirmed** |

The diagram may still show eight legacy panel boxes until flows are redrawn. **Retired:** `-> KU PWM`, third KU MPPT, and 8-panel equal-share est in `scripts/nodered_solar_computed.js` -- per-panel W waits on the new BLE keys and a Node-RED update (out of scope for doc-only pass).

After editing positions in the editor, export to `flows/solar_plant_diagram.json`.
## Edit the diagram

1. Open the **Solar plant diagram** tab.
2. Drag nodes and wires to match the physical layout ([SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md)).
3. Add a clamp: create the HA template sensor first (`config/packages/solar_plant.yaml`), then duplicate a poll node triple (function / http / status) and wire it.
4. **Deploy** in Node-RED, then export: **Menu > Export > current flow** into `flows/solar_plant_diagram.json` and commit.

Green node status shows live HA state. Red `no HA token` means fix `nodered.env` and restart the container.

## Sync with HA package changes

After `install_solar_plant_ha.sh`, reload Node-RED or wait for the 5s poll -- no NR change unless you add new entities to the canvas.


## Solar computed meters (derived tiles)

Tab **Solar computed meters** polls HA `/api/states` every 5s and runs `scripts/nodered_solar_computed.js`.

Open **http://192.168.0.105:1880/solar/computed** for HTML tiles (site totals, jumper, Sungold; legacy 8-panel / PWM est retired until NR script update).

**http://192.168.0.105:1880/solar/metrics** is the same cached object as Prometheus text ([exposition format](https://prometheus.io/docs/instrumenting/exposition_formats/)). It does not recalculate. Grafana on `.107` scrapes it. The [http in](https://nodered.org/docs/user-guide/nodes) / [http response](https://nodered.org/docs/user-guide/nodes) nodes are the official Node-RED HTTP endpoints.

Site solar in HA stays **device-only**; do not re-add those template sensors to `solar_plant.yaml`.

Policy: [SOLAR_HA_NODERED_SPLIT.md](SOLAR_HA_NODERED_SPLIT.md).
