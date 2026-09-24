# Node-RED solar diagram (`.105`)

HA stays authoritative for sensors. Node-RED reads HA and provides the **editable** diagram canvas.

## One-time setup

1. `cd /home/ansible/victron-ble2mqtt-integration`
2. `bash scripts/setup-nodered-solar-env.sh` (HA token from alfa-ai secrets + NR admin hash), or copy `nodered.env.example` manually.
3. `bash scripts/deploy-nodered-solar.sh`
4. Open **http://192.168.0.105:1880/** (Tailscale: same port on the `.105` name).

ufw (if enabled): allow LAN `1880/tcp` from `192.168.0.0/24` only.

## Edit the diagram

1. Open the **Solar plant diagram** tab.
2. Drag nodes and wires to match the physical layout ([SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md)).
3. Add a clamp: create the HA template sensor first (`config/packages/solar_plant.yaml`), then duplicate a poll node triple (function / http / status) and wire it.
4. **Deploy** in Node-RED, then export: **Menu > Export > current flow** into `flows/solar_plant_diagram.json` and commit.

Green node status shows live HA state. Red `no HA token` means fix `nodered.env` and restart the container.

## Sync with HA package changes

After `install_solar_plant_ha.sh`, reload Node-RED or wait for the 5s poll -- no NR change unless you add new entities to the canvas.
