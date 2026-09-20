# Dump-load control in Home Assistant

Home Assistant owns dump-load **on/off**. The program follows Victron's charge
cycle, not a PV-minus-load watt band. In **float**, the MPPT already throttles to
match load; a 20 W "surplus" is normal. Dump then **claims leftover PV** by adding
plugs until bus voltage approaches **re-bulk**, then sheds so the packs stay full
when the sun stops (weather or end of day). Target: **95%+ SoC remaining** after
PV is gone -- dumps must not run as night loads.

alfa-ai does **not** toggle these switches from its ticker. The brain **observes**
HA states, keeps the watt-ledger for Ask ALFa, and may write dump **helpers**
(float/re-bulk volts, AC caps, inverter assign) immediately.

This site: LiTime 24 V 230 Ah on T2 and KU ([product](https://www.litime.com/products/24v-230ah-truck-lithium-battery)
charge **28.8 V +/- 0.4 V**). SPH cart is a separate LiTime 24 V pair.

Official manuals (RULE #1):

- Packages: [configuration packages](https://www.home-assistant.io/docs/configuration/packages/)
- Automations YAML (labeled `automation` block): [Automations in YAML](https://www.home-assistant.io/docs/automation/yaml/)
- Switch actions: [switch.turn_on](https://www.home-assistant.io/integrations/switch/) /
  [switch.turn_off](https://www.home-assistant.io/integrations/switch/)
- Threshold helper (numeric hysteresis): [Threshold](https://www.home-assistant.io/integrations/threshold/)
- State trigger `for:` (dwell): [State trigger](https://www.home-assistant.io/docs/automation/trigger/)
- Timer helper (per-plug min-on and cooldown): [Timer](https://www.home-assistant.io/integrations/timer/)
- Delay (`delay` seconds, templates): [Wait for time to pass](https://www.home-assistant.io/docs/scripts/#wait-for-time-to-pass-delay)
- Derivative helper (PV rising/falling): [Derivative](https://www.home-assistant.io/integrations/derivative/)
- Template sensors: [Template](https://www.home-assistant.io/integrations/template/)
- Number helper (AC watt cap and max battery discharge): [Input number](https://www.home-assistant.io/integrations/input_number/)
- Dropdown helper (which inverter feeds each plug): [Input select](https://www.home-assistant.io/integrations/input_select/)
- Live power entity id per plug: [Input text](https://www.home-assistant.io/integrations/input_text/)
- Staged ON (`repeat` / `while` / `delay` / `if` / `stop`): [Script syntax](https://www.home-assistant.io/docs/scripts/)
- MQTT discovery (same HA path Victron BLE already uses): [MQTT](https://www.home-assistant.io/integrations/mqtt/)
- Govee BLE sensors only (**not** H5082 plugs): [Govee Bluetooth](https://www.home-assistant.io/integrations/govee_ble/)
- Victron charge stages and 1-minute re-bulk: [BlueSolar operation](https://www.victronenergy.com/media/pg/Manual_BlueSolar_MPPT_75-10_up_to_100-20/en/operation.html)
- SmartShunt current sign (+charge / -discharge): [SmartShunt operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)

Morningstar diversion role (excess after the battery is served):
[Diversion Manual §6.0](https://www.morningstarcorp.com/wp-content/uploads/technical-doc-diversion-manual-en.pdf).

Do **not** invent PV watts from Ecobee `weather.*`. Optional later: HA
[Forecast.Solar](https://www.home-assistant.io/integrations/forecast_solar/) sensors.

---

## What HA owns vs what Ask ALFa / the brain owns

Victron [BlueSolar operation](https://www.victronenergy.com/media/pg/Manual_BlueSolar_MPPT_75-10_up_to_100-20/en/operation.html):
bulk fills, absorption holds CV (~**28.4 V** on Victron lithium / LiTime 28.4-29.2 V),
float **holds** Vfloat (Victron LiFePO4 default **27.0 V** on 24 V). Re-bulk when
`Vbat < (Vfloat - 0.1 V)` for **12 V**, **multiply by two on 24 V** (offset **0.2 V**
-> **26.8 V** if float is 27.0 V) for **one minute**. Morningstar
[Diversion §6.0](https://www.morningstarcorp.com/wp-content/uploads/technical-doc-diversion-manual-en.pdf):
divert excess **after** the battery is served. Confirm float on the T2 MPPT in
VictronConnect; helpers default to 27.0 / 26.8 and Ask ALFa may tune them.

| Job | Owner |
|-----|--------|
| Kill switch | HA `input_boolean.dump_control_enabled` |
| `switch.turn_on` / `turn_off` | HA automations only |
| **When** dump may start | HA: T2 MPPT **float** for 1 min **and** that bus's shunt/cart voltage **>= float helper** for 1 min **and** solar present. **Not** bulk. **Not** surplus watts. |
| **How many** plugs (claim leftover PV) | HA staged ON: one plug, **site load delta** after `dump_site_confirm_s` (default 5 s), then another while that bus stays above re-bulk, batt ok, inverter headroom, and that plug's cooldown is idle |
| **When** dump must stop (keep 95%+ after PV) | HA: solar gone 1 min (cancels min-on); bus voltage **<= re-bulk helper** 1 min; MPPT leaves absorb/float 1 min; `dump_batt_t2_ok` / `_ku_ok` / `_sph_ok` off 1 min |
| Float / re-bulk volt helpers | HA `input_number.dump_float_*_v` / `dump_rebulk_*_v` (defaults 27.0 / 26.8). Ask ALFa may `ha_set_number` immediately to match VictronConnect. |
| Min solar W (day vs night) | HA `input_number.dump_min_solar_w` (default 50). Below that for 1 min = PV stopped. |
| SoC 95% floor | HA `input_number.dump_min_soc_percent` (95) **only when** `input_boolean.dump_soc_unsynced` is **off**. While unsynced, float voltage **is** the full-enough gate (do not invent a voltage-to-% map). |
| Site confirm / delta | HA `input_number.dump_site_confirm_s` (5-30 s, default 5) and `input_number.dump_site_delta_min_w` (5-500 W, default 25) |
| Per-plug min-on / cooldown | HA `timer.dump_plug_N_min_on` (15 min, `restore: true`) and `timer.dump_plug_N_cooldown` (10 min, `restore: true`) |
| Inverter caps, plug->bus, live meters | HA `dump_ac_limit_t2_w` / `_ku_w` / `_sph_w`; `dump_plug_N_inverter`; optional `dump_plug_N_power_entity` |
| Watt-ledger, AI Actions, `ha_dump_tick` | alfa-ai **observe / audit** |
| Tune helpers, inspect meters | Ask ALFa `ha_set_number` / `ha_select_option` / `ha_get_states` (no Approve). **Never** dump-actuate standing night loads. |
| Surplus W (`sensor.dump_surplus_w`) | Briefing only. **Not** the ON/OFF trigger. |

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
`sensor.solar_controller_battery_state`. Bus volts: `sensor.battery_1_voltage` /
`sensor.battery_2_voltage` / `sensor.sungold_sph302480a_battery_voltage`.

`sensor.dump_surplus_w` remains for the watt-ledger. It is **not** the dump ON
trigger (float throttles PV watts to the load).

### Victron float hold then staged ON

**Bulk / absorb:** dump stays **off**. The pack is still being served (CV ~28.4-28.8 V).

**Float:** MPPT **holds** Vfloat (~27.0-27.4 V on this plant). HA may add dumps:

1. `binary_sensor.dump_charge_float` on for 1 min (T2 MPPT `float`).
2. `binary_sensor.dump_solar_present` on (PV >= `dump_min_solar_w`).
3. That plug's bus `dump_v_float_*` on for 1 min (shunt/cart V >= float helper).
4. `dump_soc_unsynced` off **and** SoC < `dump_min_soc_percent` (95) blocks T2/KU add.
   While unsynced, skip SoC (float voltage is the full-enough gate)
   ([SmartShunt 5.7](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)).
5. `sensor.dump_next_plug` picks an **off** plug whose **cooldown timer is idle**,
   on a bus still in the float band, batt ok, and inverter headroom. **Do not**
   require last_w <= surplus W. Unknown per-plug watts do **not** block staging.
6. One `switch.turn_on`, then [delay](https://www.home-assistant.io/docs/scripts/#wait-for-time-to-pass-delay)
   `input_number.dump_site_confirm_s` seconds (default **5**; Sungold Modbus poll
   default is also 5 s).
7. **Site confirm** (solar-system load, not indoor Govee energy monitoring):
   - **SPH:** `sensor.sungold_sph302480a_load_power` must rise by >=
     `dump_site_delta_min_w` (default 25 W).
   - **T2:** signed `-sensor.battery_1_power` (more AC load => more negative pack
     power / less charge).
   - **KU:** signed `-sensor.battery_2_power`.
   Optional: mapped `sensor.sim_ac_plug_N_power` numeric and > 0 also confirms.
8. If solar-present or charge-float is already off after the delay: turn that plug
   off, start its 10 min cooldown, cancel its min-on, stop staging.
9. If **not** confirmed: turn off, start 10 min cooldown, try the next plug (do
   not stop the whole automation).
10. If **confirmed**: start that plug's 15 min min-on timer, delay 1 s, stage
    another. Confirmed plugs are **not** fail-closed for missing per-plug watts;
    they stay on until solar-gone / bulk / re-bulk / batt-not-ok (1 min) as today.
    PV falling does **not** immediately turn off a confirmed plug.

That is how leftover PV is claimed: add until voltage sags toward re-bulk or the
inverter is full -- not until a 200 W surplus helper trips.

**Govee H5082 (this site's dump hardware):** same *shape* as Victron BLE, not
the same product. Victron Instant Readout is a documented advertisement;
`victron_ble2mqtt` on Pi 4 decodes it and publishes [MQTT discovery](https://www.home-assistant.io/integrations/mqtt/).
HA never speaks Victron BLE. H5082 also has no official HA plug integration
([govee_ble](https://www.home-assistant.io/integrations/govee_ble/) is sensors
only). Forums/GitHub drive it with extra software (HACS or a BLE/cloud MQTT
bridge). A **sidecar that publishes MQTT switches** (like this repo already
does for Victron) would keep HA on official MQTT. That sidecar is **not** in
the repo yet. Template `switch.sim_ac_plug_*` stay until it is. Confirm stays
**SPH AC-out** (and T2/KU pack sign), not Govee energy monitoring. HACS Govee
plugins are not used on this HA.

Until MQTT (or another official HA switch) actually toggles a load on SPH AC
out, site-delta fails confirm and that slot cools 10 min.

Default AC caps are **2000 W** per inverter (operator / Renogy 2 kW class).
SPH nameplate is **3000 W**; raise **SPH AC limit** only if dumps are on that
inverter and you want the higher cap. Do not set a helper above the inverter
that feeds those plugs.

SoC is **not** a dump-on gate while `dump_soc_unsynced` is on. Float voltage is
the battery-served check. After PV stops, dumps go off so overnight use is the
house/inverter, not dump plugs (95%+ leftover if the day reached float).

Turn-**off** (Victron 1 minute; per-plug 10 min cooldown after any off):

- **All six:** `dump_solar_present` off 1 min (weather / end of day) -- cancels
  all min-on, starts all cooldowns. This is the 95%+ after solar stops rule.
- **All six:** T2 MPPT leaves absorption/float 1 min (bulk / night) -- cancels
  all min-on, starts all cooldowns.
- **That inverter only:** bus voltage <= re-bulk helper 1 min, or `dump_batt_*_ok`
  off 1 min (pack supplying the inverter) -- turn off matching plugs, cancel each
  plug's min-on, start each plug's cooldown.
- **Failed site confirm:** turn off that plug only, start its 10 min cooldown
  (no min-on started).

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

Ask ALFa may **observe** shunt/SPH/plug power and voltage (`ha_get_states` /
`ha_dump_tick`) and write float/re-bulk/AC-cap/inverter helpers immediately.
It does not invent plug watts and does not own dump on/off.

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
After a later dump-package change, `git pull` then rerun this script (or
`install_solar_plant_ha.sh`, which refreshes the dump file when it already
exists). A stale copy leaves helpers such as
`input_boolean.dump_soc_unsynced` / `input_number.dump_float_t2_v` missing from
`/api/states` while Energy / Helpers still expect them.

Operator dump UI is **Energy** (individual device Sim dump), **Site solar**
(`/site-solar` storage tiles: SPH confirm W, site confirm/delta helpers, per-plug
15 min min-on / 10 min cooldown), plus **Settings > Devices & services > Helpers**.
Disable: `input_boolean.dump_control_enabled` (Dump Automations helper), or delete
the package file and restart HA. YAML Lovelace is not the daily dump control.

Default: this package is **not** on `/opt/homeassistant` until the operator runs
the install script.

---

## Related

- [SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md)
- [SOLAR_HA_DASHBOARD.md](SOLAR_HA_DASHBOARD.md)
- alfa-ai observe/audit only: sibling `docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md`
