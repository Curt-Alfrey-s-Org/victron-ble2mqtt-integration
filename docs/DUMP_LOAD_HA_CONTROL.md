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
- Number helper (AC watt cap and max battery discharge): [Input number](https://www.home-assistant.io/integrations/input_number/)
- Dropdown helper (which inverter feeds each plug): [Input select](https://www.home-assistant.io/integrations/input_select/)
- Live power entity id per plug: [Input text](https://www.home-assistant.io/integrations/input_text/)
- Staged ON (`repeat` / `while` / `wait_template` / `delay` / `if` / `stop`): [Script syntax](https://www.home-assistant.io/docs/scripts/)
- Real plug power (when purchased): [Shelly](https://www.home-assistant.io/integrations/shelly/) (switch + `power` sensor)
- Victron charge stages and 1-minute re-bulk: [BlueSolar operation](https://www.victronenergy.com/media/pg/Manual_BlueSolar_MPPT_75-10_up_to_100-20/en/operation.html)
- SmartShunt current sign (+charge / -discharge): [SmartShunt operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)

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
| How many plugs, and which ones | HA staged ON: one plug, **wait for live watts**, then another only if surplus / inverter headroom / batteries still allow it |
| Which inverter feeds each sim dump | HA `input_select.dump_plug_N_inverter` (`T2` / `KU` / `SPH`) on Solar plant |
| Per-inverter AC watt cap | HA `input_number.dump_ac_limit_t2_w` / `_ku_w` / `_sph_w` (default **2000** W each) |
| Live load on each inverter | T2/KU: SmartShunt `sensor.battery_1_power` / `sensor.battery_2_power` (negative = pack supplying the inverter). SPH: `sensor.sungold_sph302480a_load_power` (LCD INV OUTPUT) plus cart battery V×A. Do **not** type a watt rating for a random plug-in. |
| Battery must not be discharging | HA `binary_sensor.dump_batt_t2_ok` / `_ku_ok` / `_sph_ok` from live shunt / SPH V×A. Do not add that bus's dumps; turn that bus's plugs off after 1 minute even during min-on |
| Path-loss **briefing** / Ask ALFa helper writes | alfa-ai observes meters and may write dump helpers immediately via HA REST (`input_number.set_value` / `input_select.select_option`). HA automations still own dump switch on/off. |
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

### Staged ON (do not slam the inverter)

HA never turns all six on in one action. Each ON cycle adds **one** plug, then
reads that plug's **live watt sensor** before considering another
([repeat while](https://www.home-assistant.io/docs/scripts/#repeat-a-group-of-actions),
[wait_template](https://www.home-assistant.io/docs/scripts/#wait-for-a-template)):

1. Site budget = remaining `sensor.dump_surplus_w` (PV minus **live** dump-plug
   watts minus path losses). `sensor.sim_dump_load_power` is the sum of numeric
   `sensor.sim_ac_plug_N_power` values.
2. Each plug is assigned to **one** inverter (`T2` / `KU` / `SPH`) via
   `input_select.dump_plug_N_inverter`. Default **SPH**.
3. That inverter's **live** loading:
   - **T2 / KU Renogy:** SmartShunt `sensor.battery_1_power` / `sensor.battery_2_power`.
     Headroom = AC cap minus **live** watts of ON dump plugs on that bus minus
     `max(0, -shunt_W)`.
     [SmartShunt operation 5.2](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html).
   - **SPH:** `sensor.sungold_sph302480a_load_power` plus SPH-assigned dump-plug
     live watts.
4. Battery ok (`dump_batt_*_ok`) as before.
5. `sensor.dump_next_plug` picks an off plug whose **last measured watts**
   (`sensor.dump_plug_N_last_w`) still fit surplus and headroom. If a plug has
   never reported watts, HA may **probe** it only while every already-ON plug
   has a numeric power reading.
6. `switch.turn_on`, start `timer.dump_min_on`, wait up to 15 s for
   `sensor.sim_ac_plug_N_power` to be numeric. No reading: that plug turns **off**
   ([stop](https://www.home-assistant.io/docs/scripts/#stopping-a-script-sequence)).
   If surplus/charge/PV-falling fails after the reading, that plug turns off.
7. Stop when no off plug fits, or surplus/charge is no longer ok, or PV is falling.

Until a real smart-plug power entity is set on
`input_text.dump_plug_N_power_entity`, a probe has no live watts and will turn
off after the wait. That is fail-closed, not a typed rating.

**Already-ON leftover (required):** the staged-ON wait only runs after a **new**
`switch.turn_on`. Plugs that are already on with unknown watts (old slam-all-on,
or HA restart while sim templates are ON) never hit that wait, and surplus stays
high because unknown watts do not add to `sensor.sim_dump_load_power`. Automation
`sim_dump_turn_off_unknown_watts` fail-closes those plugs:

- [Template trigger](https://www.home-assistant.io/docs/automation/trigger/#template-trigger)
  `for: 00:00:15` when any dump switch is `on` and that plug's power sensor is
  not numeric.
- [Home Assistant start](https://www.home-assistant.io/triggers/homeassistant/)
  and [automation_reloaded](https://www.home-assistant.io/docs/configuration/events/)
  ([event trigger](https://www.home-assistant.io/triggers/event/)), then
  [delay](https://www.home-assistant.io/docs/scripts/#delay) 15 s, so leftover
  ON plugs are checked after a container restart or automation reload.
- Each ON plug with non-numeric live watts is turned **off** even during min-on
  ([switch.turn_off](https://www.home-assistant.io/integrations/switch/)); min-on
  is cancelled (same as bulk). Kill switch off = automations do nothing.

Hardware when purchased: official [Shelly](https://www.home-assistant.io/integrations/shelly/)
plug (local power sensor). See [SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md).

Default AC caps are **2000 W** per inverter (operator / Renogy 2 kW class).
SPH nameplate is **3000 W**; raise **SPH AC limit** only if dumps are on that
inverter and you want the higher cap. Do not set a helper above the inverter
that feeds those plugs.

SoC is **not** a dump gate while SmartShunt SoC is unsynchronised
([operation 5.7](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)).
Charge stage + signed watts/amps are the battery-served checks. Morningstar
diversion is excess **after** the battery is served
([§6.0](https://www.morningstarcorp.com/wp-content/uploads/technical-doc-diversion-manual-en.pdf)).

Turn-**off**:

- All six: surplus low (after min-on) or T2 MPPT leaves absorption/float (battery
  wins, cancels min-on).
- **That inverter only:** its `dump_batt_*_ok` stays off 1 minute (discharging
  beyond the helper). Plugs on the other inverters stay as they are.
- **That plug:** ON with non-numeric live watts for 15 s (failed probe or
  leftover already-on). Even during min-on; cancels min-on.

### Any load on any inverter (live meters)

You do **not** type the wattage of a heater/fan/PC you plug into T2, KU, or SPH.
HA already has the live meters:

| Inverter | How HA sees a new AC load |
|----------|---------------------------|
| T2 Renogy | Battery 1 SmartShunt `sensor.battery_1_power` / `_current` (negative = pack supplying the load) |
| KU Renogy | Battery 2 SmartShunt `sensor.battery_2_power` / `_current` (same sign) |
| SPH cart | `sensor.sungold_sph302480a_load_power` (AC out) and cart battery V×A |

If that bus's pack starts discharging, `dump_batt_*_ok` goes off: no new dumps on
that inverter, and existing dumps on **that** inverter turn off after 1 minute.
SPH AC-out watts also shrink SPH headroom immediately.

Dump-plug watts are the **smart plug power sensor** (via
`input_text.dump_plug_N_power_entity` → `sensor.sim_ac_plug_N_power`). There is
no typed rating helper.

Ask ALFa may **observe** shunt/SPH/plug power (`ha_get_states` / `ha_dump_tick`)
and write AC-cap / inverter helpers (`ha_set_number` / `ha_select_option`)
immediately. It does not invent plug watts.

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
