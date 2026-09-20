# Dump-load plugs (template now, Shelly power when purchased)

**Status (2026-09-20):** Six HA dump switches (`switch.sim_ac_plug_*`). **No typed
watt rating.** Staging confirms **solar-system load delta** after
`input_number.dump_site_confirm_s` (default 5 s), not indoor Govee energy
monitoring. Optional Shelly path: mapped `sensor.sim_ac_plug_N_power` > 0.
Per plug: 15 min min-on (`timer.dump_plug_N_min_on`), 10 min cooldown after off
(`timer.dump_plug_N_cooldown`). See [DUMP_LOAD_HA_CONTROL.md](DUMP_LOAD_HA_CONTROL.md).

**Hardware when purchased:** official [Shelly](https://www.home-assistant.io/integrations/shelly/)
plug (local switch + `power` sensor). [Matter](https://www.home-assistant.io/integrations/matter/)
only if a future SKU is Matter-certified. Do not invent a custom watt protocol.

**Govee H5082:** HA Core [govee_ble](https://www.home-assistant.io/integrations/govee_ble/)
does **not** list H5082. No BLE plug path on `.93` or Pi 5. Template sim slots
do not change `sensor.sungold_sph302480a_load_power`; site-delta confirm fails
and that slot cools 10 min until Shelly/Matter hardware switches a real load.

**Hosts:** Home Assistant Container on **`.105:8123`**. alfa-ai on **`.111`**
observes via HA REST ([REST API](https://developers.home-assistant.io/docs/api/rest/)).
Do **not** use `POST /api/states` to control loads -- always service calls.

Official HA manuals (RULE #1):

- [Template integration](https://www.home-assistant.io/integrations/template/)
- [Input boolean](https://www.home-assistant.io/integrations/input_boolean/)
- [Input text](https://www.home-assistant.io/integrations/input_text/) (`dump_plug_N_power_entity`)
- [Switch domain](https://www.home-assistant.io/integrations/switch/)
- [Shelly](https://www.home-assistant.io/integrations/shelly/) (power measurement needs reachable SNTP on the device)
- [Matter](https://www.home-assistant.io/integrations/matter/) (future certified SKU only)
- [Govee Bluetooth](https://www.home-assistant.io/integrations/govee_ble/) (sensors; not H5082 plugs)
- [Timer](https://www.home-assistant.io/integrations/timer/) (per-plug min-on / cooldown)
- [Delay](https://www.home-assistant.io/docs/scripts/#wait-for-time-to-pass-delay) (site confirm seconds)
- [Configuration packages](https://www.home-assistant.io/docs/configuration/packages/)
- [Home Assistant Container](https://www.home-assistant.io/installation/linux#install-home-assistant-container)

Vendor dump/diversion role: Morningstar TriStar [Diversion Manual §6.0](https://www.morningstarcorp.com/wp-content/uploads/technical-doc-diversion-manual-en.pdf).

---

## What this is (and is not)

| | |
|---|---|
| **Is** | HA YAML: `input_boolean` + template switches + live power templates |
| **Is** | Power = the mapped Shelly (or other HA) power sensor while ON; `0` while OFF |
| **Is not** | A typed watt rating, MQTT sidecar, or Lovelace scraping |
| **Is not** | Loaded until the operator copies the package onto `.105` and restarts HA |

Dump **on/off** and staged add live in [DUMP_LOAD_HA_CONTROL.md](DUMP_LOAD_HA_CONTROL.md).
HA confirms **site load delta** (SPH `sensor.sungold_sph302480a_load_power`;
T2/KU signed pack power) after `dump_site_confirm_s` before adding another plug.
Inverter assignment is `input_select.dump_plug_N_inverter`.

---

## Entity contract (must match alfa-ai allowlist)

Use **`switch.sim_ac_plug_*`** in alfa-ai Settings -- **not** `input_boolean.*`.

| entity_id | Role |
|-----------|------|
| `switch.sim_ac_plug_1` ... `_6` | Dump switch (template until hardware) |
| `sensor.sim_ac_plug_N_power` | Live watts while ON (from mapped power entity) |
| `sensor.sim_dump_load_power` | Sum of numeric plug power sensors |
| `input_text.dump_plug_N_power_entity` | HA `entity_id` of that plug's power sensor (empty until hardware) |

Internal helpers (do **not** allowlist): `input_boolean.sim_ac_plug_N_internal`.

---

## When you buy smart plugs (one path)

1. Add the device with the official [Shelly](https://www.home-assistant.io/integrations/shelly/)
   integration (**Settings → Devices & services → Add integration → Shelly**).
2. Confirm the device Web UI SNTP server is reachable (Shelly docs: required for
   power measurement).
3. For slot N: remove that slot's **template** switch from
   `config/packages/sim_dump_plugs.yaml` (HA cannot have two entities with the
   same `entity_id`), reinstall the package, then in **Settings → Entities**
   rename the Shelly switch to `switch.sim_ac_plug_N`
   ([customizing entities](https://www.home-assistant.io/docs/configuration/customizing-devices/)).
4. On Solar plant, set **N power sensor** to the Shelly power `entity_id`
   (example shape `sensor.shellyplusplug_..._power` -- use the id HA assigned).
5. HA dump staging then may confirm via that live watt reading **or** site load
   delta. Ask ALFa inspects the same sensors.

---

## Enable on `.105` only (one path)

**Prerequisites:** HA Container running with config at `/opt/homeassistant`.

```bash
cd /home/ansible/victron-ble2mqtt-integration
git pull --ff-only origin main
bash scripts/install_sim_dump_plugs_ha.sh
```

Then dump control: `bash scripts/install_sim_dump_control_ha.sh`.
See [DUMP_LOAD_HA_CONTROL.md](DUMP_LOAD_HA_CONTROL.md).

---

## alfa-ai (observe)

The brain may **read** these switches and power sensors via HA REST. Dump
**actuation** is [DUMP_LOAD_HA_CONTROL.md](DUMP_LOAD_HA_CONTROL.md).

---

## Repo files

| File | Role |
|------|------|
| `config/packages/sim_dump_plugs.yaml` | Switches + live power mapping |
| `config/packages/sim_dump_control.yaml` | HA dump on/off + wait-for-watts |
| `scripts/install_sim_dump_plugs_ha.sh` | Copy plugs package + restart |
| `scripts/install_sim_dump_control_ha.sh` | Copy control package + restart |
| `tests/test_sim_dump_plugs.py` | Plug entity contract |
| `tests/test_sim_dump_control.py` | Control package contract |

---

## Tests

```bash
python -m pytest tests/test_sim_dump_plugs.py tests/test_sim_dump_control.py -q
```

---

## Related

- [DUMP_LOAD_HA_CONTROL.md](DUMP_LOAD_HA_CONTROL.md)
- [SOLAR_HA_DASHBOARD.md](SOLAR_HA_DASHBOARD.md)
- alfa-ai [HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md)
