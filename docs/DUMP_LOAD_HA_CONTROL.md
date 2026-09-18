# Dump-load control in Home Assistant

Home Assistant owns dump-load **on/off**, **hysteresis**, and **charge-stage dwell**.
alfa-ai does **not** toggle these switches from its ticker. The brain may still
**observe** HA states, keep the cluster watt-ledger for Ask ALFa, and write
`ai_actions` audit rows.

Official manuals (RULE #1):

- Packages: [configuration packages](https://www.home-assistant.io/docs/configuration/packages/)
- Automations YAML (labeled `automation` block): [Automations in YAML](https://www.home-assistant.io/docs/automation/yaml/)
- Switch actions: [switch.turn_on](https://www.home-assistant.io/integrations/switch/) /
  [switch.turn_off](https://www.home-assistant.io/integrations/switch/)
- Threshold helper (numeric hysteresis): [Threshold](https://www.home-assistant.io/integrations/threshold/)
- State trigger `for:` (dwell): [State trigger](https://www.home-assistant.io/docs/automation/trigger/)
- Timer helper (min on/off dwell): [Timer](https://www.home-assistant.io/integrations/timer/)
- Derivative helper (PV rising/falling): [Derivative](https://www.home-assistant.io/integrations/derivative/)
- Template sensors: [Template](https://www.home-assistant.io/integrations/template/)
- Victron charge stages and 1-minute re-bulk: [BlueSolar operation](https://www.victronenergy.com/media/pg/Manual_BlueSolar_MPPT_75-10_up_to_100-20/en/operation.html)

Morningstar diversion role (excess after the battery is served):
[Diversion Manual §6.0](https://www.morningstarcorp.com/wp-content/uploads/technical-doc-diversion-manual-en.pdf).

Do **not** invent PV watts from Ecobee `weather.*`. Optional later: HA
[Forecast.Solar](https://www.home-assistant.io/integrations/forecast_solar/) sensors.

---

## What HA owns vs what the brain owns

| Job | Owner |
|-----|--------|
| Sim plug entities | HA package [SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md) |
| Surplus band (ON above ~200 W, OFF below ~50 W) | HA Threshold on `sensor.dump_surplus_w` |
| Charge stage must stay `absorption`/`float` before ON; leave that pair before OFF | HA `binary_sensor.dump_charge_ok` + state `for: 00:01:00` (Victron 1 minute) |
| Min ON 10 min / min OFF 5 min | HA `timer.dump_min_on` / `timer.dump_min_off` |
| PV falling (cloud valley) blocks new ON | HA Derivative + Threshold `binary_sensor.dump_pv_falling` |
| `switch.turn_on` / `turn_off` on `switch.sim_ac_plug_*` | HA automations in this package |
| Path-loss **briefing** / NIST `ai_actions` / Ask ALFa | alfa-ai only |
| Kill switch | HA `input_boolean.dump_control_enabled` on Solar plant **Now** (entities card) |

Do **not** add a second dump ticker in alfa-ai that calls `switch.turn_on` /
`turn_off` while this package is loaded.

---

## Package

Tracked source: `config/packages/sim_dump_control.yaml`.

Depends on:

- [SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md) (`switch.sim_ac_plug_*`, `sensor.sim_dump_load_power`)
- Optional: [SOLAR_HA_DASHBOARD.md](SOLAR_HA_DASHBOARD.md) `sensor.solar_component_losses_power` (0 W if missing)

PV watts: live MQTT id `sensor.solar_controller_solar`, with fallback
`sensor.solar_controller_solar_power`. Charge stage: live
`sensor.solar_controller_charge_state`, with fallback
`sensor.solar_controller_battery_state`.

Threshold math ([Threshold](https://www.home-assistant.io/integrations/threshold/)
upper + hysteresis): `upper: 125`, `hysteresis: 75` so the helper turns **on** when
surplus > 200 W and **off** when surplus < 50 W.

---

## Enable on `.105` (one path)

Prerequisites: sim dump plugs already installed
(`bash scripts/install_sim_dump_plugs_ha.sh`).

```bash
cd /home/ansible/victron-ble2mqtt-integration
git pull --ff-only origin main
bash scripts/install_sim_dump_control_ha.sh
```

The script copies `sim_dump_control.yaml` into `/opt/homeassistant/packages/` and
restarts the `homeassistant` container
([HA Container](https://www.home-assistant.io/installation/linux#install-home-assistant-container)).

Disable: turn off **Dump load HA control** on Solar plant **Now**
(`input_boolean.dump_control_enabled`), or delete the package file and restart HA.
The same toggle is also a helper under Settings, but the dashboard is the operator
control.

Default: this package is **not** on `/opt/homeassistant` until the operator runs
the install script.

---

## Related

- [SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md)
- [SOLAR_HA_DASHBOARD.md](SOLAR_HA_DASHBOARD.md)
- alfa-ai observe/audit only: sibling `docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md`
