# Node-RED solar diagram (`.105`)

HA stays authoritative for sensors. Node-RED reads HA and provides the **editable** diagram canvas.

## One-time setup

1. `cd /home/ansible/victron-ble2mqtt-integration`
2. `bash scripts/setup-nodered-solar-env.sh` (HA token from alfa-ai secrets + NR admin hash), or copy `nodered.env.example` manually.
3. `bash scripts/deploy-nodered-solar.sh`
4. Open **http://192.168.0.105:1880/** (Tailscale: same port on the `.105` name).

ufw (if enabled): allow LAN `1880/tcp` from `192.168.0.0/24` only.


## Eight panel boxes (diagram tab)

On **Solar plant diagram**, the group **Solar panels (8x 2s strings)** polls HA every 5s and drives eight **Panel 1..8** function nodes (status boxes). Comment nodes label where each pair connects: `-> T2 MPPT #1`, `-> KU MPPT #2`, `-> KU MPPT #3`, `-> KU PWM`. Drag boxes inside the group to match roof layout; est W per panel is half of its 2s string (see `scripts/nodered_solar_computed.js` `panelBoxes()`).
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

Open **http://192.168.0.105:1880/solar/computed** for HTML tiles (site totals, KU est, jumper, Sungold, plus an 8-panel table).

Site solar in HA stays **device-only**; do not re-add those template sensors to `solar_plant.yaml`.

Policy: [SOLAR_HA_NODERED_SPLIT.md](SOLAR_HA_NODERED_SPLIT.md).
