# Agent instructions — victron-ble2mqtt-integration

## Scope

- **Home / IoT edge:** Victron BLE → MQTT, Home Assistant, Mosquitto on a Raspberry Pi (or similar).
- **Not automatic cluster membership:** Do **not** add the Pi to the **Petals** GPU cluster or **CPU worker fleet** unless the operator explicitly asks.

## Working with alfa-ai and monitoring

- Open **alfa-ai**, **victron-ble2mqtt-integration**, and **monitoring** in one **Cursor multi-root workspace** (sibling paths on the dev host, e.g. under `/home/ansible/`) so analysis and edits can span repos.
- Hub policy and TrueNAS layout: **`alfa-ai/docs/HUB_ARTIFACTS.md`** (GitHub or local clone).
- After changing deploy or Docker on the Pi, align **monitoring** scrape config via **`monitoring/hosts/pi4-victron/README.md`**.

## Doc map

- [docs/ALFA_CLUSTER_INTEGRATION.md](docs/ALFA_CLUSTER_INTEGRATION.md) — hub + Cursor + Prometheus wiring
- [DEPLOY.md](DEPLOY.md) — installer behaviour and flags
