# Simulated A/C dump-load plugs (FAKE loads for alfa-ai)

**Status (2026-09-17):** Six **simulated** Shelly-like switches in Home Assistant. No
physical smart plugs. Used to exercise alfa-ai solar dump-load decisions and manual
`switch.turn_on` / `turn_off` before wiring real dump loads on **Sungold AC out**.

**Hosts:** Home Assistant Container on **`.105:8123`**. alfa-ai brain on **`.111`**
controls plugs via the official HA REST API ([REST API](https://developers.home-assistant.io/docs/api/rest/)).
Do **not** use `POST /api/states` to control loads -- always service calls.

Official HA manuals (RULE #1):

- [Template integration](https://www.home-assistant.io/integrations/template/) (`unique_id`, `default_entity_id`)
- [Input boolean](https://www.home-assistant.io/integrations/input_boolean/)
- [Switch domain](https://www.home-assistant.io/integrations/switch/)
- [Configuration packages](https://www.home-assistant.io/docs/configuration/packages/) (split YAML into `packages/`)
- [Home Assistant Container](https://www.home-assistant.io/installation/linux#install-home-assistant-container) (`docker restart homeassistant` after package changes)
- [Customizing entities](https://www.home-assistant.io/docs/configuration/customizing-devices/) (entity_id changes in UI; no documented in-place `unique_id` rename API)

Vendor dump/diversion role: Morningstar TriStar [Diversion Manual §6.0](https://www.morningstarcorp.com/wp-content/uploads/technical-doc-diversion-manual-en.pdf).

---

## What this is (and is not)

| | |
|---|---|
| **Is** | HA YAML package: `input_boolean` internal state + **template switches** + template power sensors |
| **Is** | Companion watts: rated W when ON, `unknown`/none when OFF (never the string `"off"`) |
| **Is not** | Real Shelly hardware, MQTT sidecar, cloud APIs, or Lovelace scraping |
| **Is not** | Loaded until the operator copies the package onto `.105` and restarts HA |

Load control policy (allowlist, auto-actuate, kill switches) lives in alfa-ai:
[HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md)
(sibling: `../alfa-ai/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md`).

Dump loads are fed from **Sungold AC out** (SPH INV OUTPUT), not KU Renogy:
[SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md).

---

## Entity contract (must match alfa-ai allowlist)

Use **`switch.sim_ac_plug_*`** in alfa-ai Settings -- **not** `input_boolean.*`.

| entity_id (allowlist) | Device name | Rated W |
|-----------------------|-------------|---------|
| `switch.sim_ac_plug_1` | Sim A/C plug 1 fan | 180 |
| `switch.sim_ac_plug_2` | Sim A/C plug 2 dehumidifier | 300 |
| `switch.sim_ac_plug_3` | Sim A/C plug 3 water heater | 1200 |
| `switch.sim_ac_plug_4` | Sim A/C plug 4 fan | 130 |
| `switch.sim_ac_plug_5` | Sim A/C plug 5 fan | 130 |
| `switch.sim_ac_plug_6` | Sim A/C plug 6 gaming PC | 300 |

Internal helpers (do **not** allowlist): `input_boolean.sim_ac_plug_N_internal`.

Power sensors (template):

| entity_id | When ON | When OFF |
|-----------|---------|----------|
| `sensor.sim_ac_plug_1_power` ... `sensor.sim_ac_plug_6_power` | Rated W (number) | none / unknown |
| `sensor.sim_dump_load_power` | Sum of ON plug watts | `0` when all OFF |

Each switch has pinned `unique_id` + `default_entity_id` so slugs stay `sim_ac_plug_1`
through `_6` (no `_2` suffix drift). The aggregate sensor `unique_id` is
`sim_dump_load_power` (was `sim_soak_load_power`). Changing `unique_id` registers a
**new** entity ([template unique_id](https://www.home-assistant.io/integrations/template/));
HA has no documented in-place unique_id rename. After reinstall, remove leftover
`sensor.sim_soak_load_power` in **Settings > Entities** if it remains. alfa-ai
`solar_dump.py` still reads the leftover entity_id until that cleanup.

---

## Enable on `.105` only (one path)

**Prerequisites:** HA Container running with config at `/opt/homeassistant`
(this repo's `docker-compose.homeassistant.yml` on `.105`).

1. On **`.105`**, in the victron checkout (e.g. `/home/ansible/victron-ble2mqtt-integration`):

```bash
cd /home/ansible/victron-ble2mqtt-integration
git pull --ff-only origin main
bash scripts/install_sim_dump_plugs_ha.sh
```

The script:

- Copies `config/packages/sim_dump_plugs.yaml` to `/opt/homeassistant/packages/`
- Removes leftover `/opt/homeassistant/packages/sim_soak_plugs.yaml` if present
- Ensures `configuration.yaml` includes `packages: !include_dir_named packages`
  ([packages doc](https://www.home-assistant.io/docs/configuration/packages/))
- Runs `docker restart homeassistant` ([HA Container restart](https://www.home-assistant.io/installation/linux#install-home-assistant-container))

2. After HA is back (~2 min), verify:

```bash
curl -fsS -H "Authorization: Bearer <token>" http://127.0.0.1:8123/api/states/switch.sim_ac_plug_1
```

3. In alfa-ai **Admin -> AI Actions -> Settings**, add allowlist (example):

```
switch.sim_ac_plug_1,switch.sim_ac_plug_2,switch.sim_ac_plug_3,switch.sim_ac_plug_4,switch.sim_ac_plug_5,switch.sim_ac_plug_6
```

Keep `ha_solar_dump_auto_actuate=false` until you want the dump-load ticker to toggle sim loads
(allowlist still required). When HA is enabled on the brain (`ALFA_AI_HOME_ASSISTANT_ENABLED=1`
+ token file), Ask ALFa `ha_switch_on` / `ha_switch_off` auto-actuate without Approve; see
alfa-ai [HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md).

**Disable / remove:** delete `/opt/homeassistant/packages/sim_dump_plugs.yaml`, restart HA,
remove entities from the registry if needed.

Default: package is **not** on `/opt/homeassistant` until the operator runs the install script.

---

## alfa-ai REST control (brain on `.111`)

alfa-ai calls HA on `.105` ([REST API](https://developers.home-assistant.io/docs/api/rest/)):

```http
POST /api/services/switch/turn_on
Content-Type: application/json
Authorization: Bearer <long-lived token>

{"entity_id": "switch.sim_ac_plug_1"}
```

```http
POST /api/services/switch/turn_off
{"entity_id": "switch.sim_ac_plug_1"}
```

Template switches run `input_boolean.turn_on` / `turn_off` internally; power sensors
update from the same internal state. See [ALFA_AI_HOW_TO_USE.md](ALFA_AI_HOW_TO_USE.md).

---

## Repo files

| File | Role |
|------|------|
| `config/packages/sim_dump_plugs.yaml` | Tracked HA package (source of truth) |
| `scripts/install_sim_dump_plugs_ha.sh` | Copy + packages include + container restart |
| `tests/test_sim_dump_plugs.py` | Entity id / watt table validation |

---

## Tests

```bash
python -m pytest tests/test_sim_dump_plugs.py -q
```

---

## Related

- [SOLAR_HA_DASHBOARD.md](SOLAR_HA_DASHBOARD.md) -- HA Solar plant (canonical)
- [ALFA_AI_HOW_TO_USE.md](ALFA_AI_HOW_TO_USE.md)
- [ALFA_CLUSTER_INTEGRATION.md](ALFA_CLUSTER_INTEGRATION.md)
- alfa-ai [HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md)
