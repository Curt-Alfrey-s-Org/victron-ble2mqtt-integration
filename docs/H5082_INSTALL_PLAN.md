# H5082 real dump plugs, then fix the Grafana one-line

**Status:** plan only. Nothing in this file is installed.
**Resume here:** the first checkpoint whose box is still `[ ]`.
**Do not start at the Grafana redraw.** That is last, after real outlets exist.

## Hard gates (do not skip)

- **No HACS.** [Govee Bluetooth](https://www.home-assistant.io/integrations/govee_ble/) does not list H5082. [Govee lights local](https://www.home-assistant.io/integrations/govee_light_local/) is lights only. This repo already says not to install a HACS Govee plugin ([SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md), [DUMP_LOAD_HA_CONTROL.md](DUMP_LOAD_HA_CONTROL.md)). HACS is not the next step.
- **Official control** is Govee's Open API, then MQTT discovery into the HA that already runs on `.105`. Dual sockets use `devices.capabilities.toggle` instances `socketToggle1` and `socketToggle2` ([Control You Device](https://developer.govee.com/reference/control-you-devices)). A single `powerSwitch` is the wrong command for a two-outlet plug.
- **API key** stays in a mode-`600` file on `.105`, never in git. Apply for the key in the Govee Home app (About → Request API Key).
- **Sim plugs stay until a real socket toggles a real load.** Then delete them. Deleting them first leaves dump automations pointing at nothing.
- **Do not run** the untracked `/home/ansible/victron-ble2mqtt-integration/deploy-nodered-solar.sh`. It calls scripts removed in `1f5822a`. Use `scripts/deploy-nodered-solar.sh`.

## What is already built

| Piece | State |
|---|---|
| `config/packages/sim_dump_plugs.yaml` | Six **fake** template switches `switch.sim_ac_plug_1`…`_6` plus optional power sensors. Header says "until Govee H5082 MQTT switches exist." |
| `config/packages/sim_dump_control.yaml` | Dump on/off, confirm, shed. Hardcoded to those six switches. |
| `docs/SIM_DUMP_PLUGS.md` | Says hardware is an H5082 **4-pack = 8 sockets**, and dump uses **six** of them. Sidecar "is not in this repo yet." |
| Node-RED `/solar/metrics` | Computed plant watts only. No plug switches. |
| Grafana `solar-plant-oneline` | Plant lanes. No real outlets. Layout is the one to redraw **after** plugs exist. |
| HA on `.105` | Container `2026.7.3`, Bluetooth left off. Do not turn on `default_config:` to chase BLE. |

## Checkpoint 0 — socket count (stop until answered)

`[ ]` Operator answers one number.

The repo text is **4 dual plugs = 8 sockets, dump uses 6**. The request says **8 double outlet plugs**, which can mean **16 sockets** (8 devices × 2). Do not generate entity ids until this is answered.

Record the answer here when known:

```text
devices: 
sockets: 
dump slots used: 
```

Each device is two MQTT switches (`socketToggle1`, `socketToggle2`), not one.

## Checkpoint 1 — prove the API sees these plugs

`[ ]` On `.105`, with the key only in the secrets file, call Govee `GET /router/api/v1/user/devices` ([device list](https://developer.govee.com/reference/get-you-devices)).

Pass if the JSON includes SKU `H5082` and each device lists `socketToggle1` and `socketToggle2`. Write the device id, sku, and capability names into this doc (ids are not secrets; the API key is).

**Stop** if H5082 is missing or those toggle instances are absent. Say what the payload actually contains. Do not install HACS to paper over that. Do not invent a BLE parser.

## Checkpoint 2 — docs before code

`[ ]` Update [SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md) and [DUMP_LOAD_HA_CONTROL.md](DUMP_LOAD_HA_CONTROL.md) in the same change as the sidecar:

- Sim templates are temporary and will be removed after Checkpoint 4.
- Real switches come from MQTT discovery ([MQTT discovery](https://www.home-assistant.io/integrations/mqtt/)).
- Control command is `socketToggle1` / `socketToggle2`, not `powerSwitch`.
- Socket count from Checkpoint 0.
- Dump confirm stays the Sungold AC-out / shunt site delta unless Checkpoint 1 shows a per-socket watt capability. If it does, map that sensor. Do not invent watts.

## Checkpoint 3 — sidecar on `.105`

`[ ]` A small service next to Mosquitto (not on the Pi 4 Victron radio, not a second HA):

- Poll device state on the official interval (state is 30 requests/minute/device; control is 2 requests/second/device). Do not poll faster than that.
- Publish one MQTT switch per socket via discovery, plus a power sensor **only if** the state payload has a numeric watt field.
- Subscribe to the HA command topic and POST `/router/api/v1/device/control` with `devices.capabilities.toggle`.
- No key in the repo. No HACS. No `POST /api/states` to fake a switch.

Pass: one socket off→on→off in HA Developer Tools changes the physical outlet, and the Govee app shows the same state.

## Checkpoint 4 — point dump at real switches, then delete sim

`[ ]` Retarget `sim_dump_control.yaml` (or its successor) at the MQTT switch entity ids. Keep min-on, cooldown, shed-one, and solar-gone behavior. The count must match Checkpoint 0, not a hardcoded 6, if the operator said more than 6.

`[ ]` Only after one full dump cycle uses real outlets: remove `sim_dump_plugs.yaml` from `/opt/homeassistant/packages/`, remove the template package from git, and drop sim entities from the Site solar seed. Restart HA once. Do not leave both a template `switch.sim_ac_plug_1` and an MQTT switch with that id.

## Checkpoint 5 — Node-RED

`[ ]` Extend `/solar/metrics` so it prints the **HA states** of those sockets (on = 1/0 and watts if present). Same cache path as the plant watts. No second watt formula. Redeploy with `scripts/deploy-nodered-solar.sh` only.

Pass: `curl -fsS http://127.0.0.1:1880/solar/metrics` on `.105` shows one sample per socket.

## Checkpoint 6 — Grafana layout (only after 5)

`[ ]` Redraw `grafana/dashboards/solar_plant_oneline.json` (generator: `monitoring/scripts/render_solar_oneline_dashboard.py`).

Flow, left to right, three bands, plugs in one row under Sungold AC out:

1. T2 panels → T2 MPPT → Battery 1, jumper down to Battery 2.
2. KU panels → KU MPPT 2+3 est and PWM est → Battery 2 → trailer / EM16 → Sungold AC in.
3. Sungold PV → cart battery. Sungold AC out → one card per real socket (label = device + socket 1 or 2), then the house load total.

Do not stack cards on top of each other. Do not put sim switches back. Arrow rules stay as they are (sign for jumper and shunts, fixed forward elsewhere). No particle animation.

Prometheus on `.107` already scrapes `/solar/metrics`. After the yml file itself changes, recreate the container (`docker compose up -d --force-recreate --no-deps prometheus`) because that file is a bind mount. A dashboard-only change does not need a Grafana restart.

## Checkpoint 7 — done when

`[ ]` Physical outlet tracks the HA switch.
`[ ]` Dump shed turns that outlet off.
`[ ]` Sim switches are gone from HA.
`[ ]` Grafana cards follow the three bands and show the real sockets.
`[ ]` Docs match the code.

## Where a new session starts

Read this file. Do the first `[ ]` only. Do not jump to Checkpoint 6 because the current canvas looks bad.
