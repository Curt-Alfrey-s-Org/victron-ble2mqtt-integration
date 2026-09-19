# Solar plant (Home Assistant Lovelace)

**Canonical operator power-flow view** is this Lovelace dashboard on **`.105:8123`**.
The custom SVG proxy on `:8765` is **retired** ([SOLAR_FLOW_DASHBOARD.md](SOLAR_FLOW_DASHBOARD.md)).

Home Assistant already holds the Victron, shunt, Refoss, Sungold, and sim-dump
entities. This dashboard uses **stock cards** only:

- [Energy cards](https://www.home-assistant.io/dashboards/energy/) (`power-sankey`)
- [Glance](https://www.home-assistant.io/dashboards/glance/) (`columns` set so names and watts fit; omitting it uses `min(entity count, 5)` in the [glance card](https://github.com/home-assistant/frontend/blob/dev/src/panels/lovelace/cards/hui-glance-card.ts) and ellipsizes)
- [Vertical stack](https://www.home-assistant.io/dashboards/vertical-stack/) (dump, house)
- [Entities](https://www.home-assistant.io/dashboards/entities/) (sim dump plug switches)
- [History graph](https://www.home-assistant.io/dashboards/history-graph/)
- [Statistics graph](https://www.home-assistant.io/dashboards/statistics-graph/)
- [Thermostat](https://www.home-assistant.io/dashboards/thermostat/)
- [Weather forecast](https://www.home-assistant.io/dashboards/weather-forecast/) (`weather.417373300314` outdoor ambient + forecast)
- [Distribution](https://www.home-assistant.io/dashboards/distribution/)
- [Markdown](https://www.home-assistant.io/dashboards/markdown/)

YAML dashboards: [Adding YAML dashboards](https://www.home-assistant.io/dashboards/dashboards/#adding-yaml-dashboards).
Packages: [Configuration packages](https://www.home-assistant.io/docs/configuration/packages/).
Template sensors: [Template](https://www.home-assistant.io/integrations/template/).
Watt-hours from watts: [Integral (Riemann)](https://www.home-assistant.io/integrations/integration/).
Energy sources: [Home energy management](https://www.home-assistant.io/docs/energy/).

Dump ON/OFF is Home Assistant automations in `sim_dump_control.yaml`
([DUMP_LOAD_HA_CONTROL.md](DUMP_LOAD_HA_CONTROL.md)): Victron **float hold** then
staged plugs; **solar-gone / re-bulk** off so packs stay 95%+ after PV stops.
Solar plant **Now** has an [entities](https://www.home-assistant.io/dashboards/entities/)
card **Dump load HA control** with the kill switch
`input_boolean.dump_control_enabled` (toggle on this page; do not hunt Helpers).
The six `switch.sim_ac_plug_*` rows are visibility (and optional manual). A header
toggle on that plug card is **manual** only. Per-plug watts live on **History**.
Do **not** put `input_boolean.sim_ac_plug_*_internal` on Lovelace. Do **not** add a
second dump ticker in alfa-ai.

**Do not** add hops, SVG wires, or Node-RED for this view.

Site physics (two 24 V buses, jumper estimate, A3/B3 = trailer outlet feeding
Sungold A/C-in, not LED/vent): [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md).

The existing storage-mode sidebar item **Solar** (`dashboard-solar`) stays as the
MQTT/Sungold **entity list**. This YAML dashboard is **Solar plant**
(`/solar-plant`).

---

## What you get

| Surface | Role |
|---------|------|
| **Solar plant** Lovelace | Live W glances grouped by bus + `power-sankey` (after Energy is configured) |
| Template sensors | Jumper est. (+ = T2→KU), T2-end jumper sign, trailer outlet W, KU PV est., KU equal-share est. |
| Integral sensors | kWh from live W (T2 MPPT, battery charge/discharge, trailer outlet, dump, Sungold load) |

HA Energy / `power-sankey` is a **sources / battery / home / devices** Sankey, not a
Victron GX two-bus cartoon. KU MPPT/PWM remain **estimates** (no live Victron clamps).

---

## Template entity ids

| entity_id | Meaning |
|-----------|---------|
| `sensor.t2_ku_jumper_power` | Est. `solar_controller_solar - battery_1_power` (T2 Renogy idle = 0). **Canonical + = T2→KU.** Used on **KU** glance (**Jumper from T2**), KU PV est., and History. There is no KU-end clamp ([SmartShunt operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)). |
| `sensor.t2_ku_jumper_at_t2_power` | Same estimate, T2-end sign: `-(t2_ku_jumper_power)`. **T2 glance only** (**Jumper to KU**). Negative = leaving T2 (T2→KU); positive = arriving at T2 (KU→T2). Not a second clamp. Do **not** Riemann this. Do **not** put it on History. |
| `sensor.trailer_outlet_power` | `\|B3\|` if \|B3\| >= 0.5 W, else `\|A3\|`. That clamp is the **trailer outlet / Sungold A/C-in** (SPH cord). Cargo LED (~0.01 W) and vent fan (~0.1 W) are not separately metered and must **not** be the Lovelace name. |
| `sensor.ku_unmetered_pv_est_power` | `battery_2_power - jumper + trailer_outlet` |
| `sensor.ku_charger_equal_share_power` | KU PV est. / 3 (MPPT 1, MPPT 2, PWM each) |
| `sensor.battery_1_charge_power` / `_discharge_power` | `max(0, +/- battery_1_power)` |
| `sensor.battery_2_charge_power` / `_discharge_power` | same for Battery 2 |
| `sensor.t2_mppt_conversion_loss_power` | T2 MPPT conversion loss: `max(0, solar - charge - load)`; skip when charge 0/missing and jumper flowing |
| `sensor.sungold_conversion_loss_power` | Sungold `SG_loss`: `max(0, (AC_in + PV) - batt_in - AC_out)` |
| `sensor.solar_component_losses_power` | `combined_losses_w` = T2 MPPT loss + Sungold loss ([SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md)) |

Do **not** treat KU equal-share as a live Victron watt clamp. Do **not** add A3 as
utility grid. Do **not** put `sensor.ku_unmetered_pv_est_power` on the Instant W
distribution card — night **negative** values are balance residual / losses, not
KU solar generation.

---

## Enable on `.105` (one path)

**Prerequisites:** HA Container `homeassistant`, config `/opt/homeassistant`, victron
clone pulled.

```bash
cd /home/ansible/victron-ble2mqtt-integration
bash scripts/install_solar_plant_ha.sh
```

The script copies the package and dashboard YAML, appends `lovelace:` / `recorder:` /
`history:` / `energy:` when missing, runs
`python -m homeassistant --script check_config -c /config` inside the container
([check configuration](https://www.home-assistant.io/docs/configuration/troubleshooting/)),
then `docker restart homeassistant`
([Container install](https://www.home-assistant.io/installation/linux#install-home-assistant-container)).
This HA has no `default_config:`. Recorder/history are required for graphs; Energy
(`energy`) is required for **Settings > Dashboards > Energy**
([default config](https://www.home-assistant.io/integrations/default_config/),
[Energy FAQ](https://www.home-assistant.io/docs/energy/faq/#the-energy-dashboard-is-not-visible)).

Open:

```text
http://192.168.0.105:8123/solar-plant
```

YAML dashboard reload after later file edits: dashboard three-dots **Refresh**
(not only the browser reload).

---

## Display precision (tenths)

Numeric tiles use Home Assistant **display precision**, not rounded MQTT payloads.
That is the same control as **Settings > Devices & services > Entities >
Display precision**. The user override lives in
`options.sensor.display_precision` (and `options.number.display_precision`)
on the entity registry
([WebSocket entity registry](https://developers.home-assistant.io/docs/api/websocket/),
[MQTT suggested_display_precision](https://www.home-assistant.io/integrations/sensor.mqtt/#suggested_display_precision)).
MQTT `suggested_display_precision` is only a default; Refoss and other
integrations can still show hundredths until the user override is `1`.

Site default: **tenths** (`1`) on every `sensor` and `number` entity except
`timestamp` / `date` / `enum`. Change individuals afterward in the entity UI.
Stop the `homeassistant` container before writing `.storage`
([Container common tasks](https://www.home-assistant.io/common-tasks/container/)):

```bash
bash scripts/apply_ha_display_precision.sh
```

---

## Energy dashboard (CLI)

`power-sankey` stays empty until Energy sources exist
([Energy cards](https://www.home-assistant.io/dashboards/energy/)). There is no
supported YAML for the Energy config store. Home Assistant exposes
`energy/get_prefs` and `energy/save_prefs` on the official
[WebSocket API](https://developers.home-assistant.io/docs/api/websocket/)
([energy websocket_api.py](https://github.com/home-assistant/core/blob/master/homeassistant/components/energy/websocket_api.py)).

From a host that can reach `.105:8123`, with a long-lived token in `HA_TOKEN`
or `HA_TOKEN_FILE` (never commit the token):

```bash
python scripts/save_solar_plant_energy_prefs.py
```

That command writes the table below. It does **not** add grid, Electricity Maps,
gas, water, A1 monthly kWh, or KU equal-share solar.

Add **power** sensors (W) and the matching **integral kWh** sensors:

| Energy slot | Power (W) | Energy (kWh, after integral exists) |
|-------------|-----------|-------------------------------------|
| Solar | `sensor.solar_controller_solar` | `sensor.t2_mppt_energy_kwh` |
| Battery T2 | charge `sensor.battery_1_charge_power`, discharge `sensor.battery_1_discharge_power` | matching `*_energy_kwh` |
| Battery KU | charge/discharge `sensor.battery_2_*` | matching `*_energy_kwh` |
| Device: Sungold A/C-in | `sensor.trailer_outlet_power` (always >= 0 W) | `sensor.em16_a3_energy_kwh` |
| Device: sim dump | `sensor.sim_dump_load_power` | `sensor.sim_dump_energy_kwh` |
| Device: Sungold A/C out | `sensor.sungold_sph302480a_load_power` | `sensor.sungold_load_energy_kwh` |

The script also sets display names (Sungold A/C-in, Sungold A/C out, Sim dump).
Energy **Sungold A/C-in** is the trailer-outlet clamp (SPH cord), not LED/vent.
Leave **grid**, Electricity Maps, gas, and water empty. Do **not** add KU
equal-share as a second solar source (double-count). Do **not** add A1 monthly
kWh or battery charge/discharge as individual devices.

Energy may warn `sensor.battery_1_discharge_energy_kwh` is **unknown** while Battery 1
is only charging (discharge watts stay `0`). The Integral helper does not leave
`unknown` until its source changes
([Integral data updates](https://www.home-assistant.io/integrations/integration/#data-updates)).
That is not a bad battery config. It clears on the first T2 discharge, or after
[Developer tools > States](https://www.home-assistant.io/docs/tools/dev-tools/)
sets `sensor.battery_1_discharge_power` to `0` so the helper records a sample.

Do **not** configure EM16 A3 as the electricity **grid**. This site is not on
utility import.

`sensor.em16_a3_power` is a signed CT. Integrating it made `sensor.em16_a3_energy_kwh`
negative (`-0.02` kWh) and Energy warned that individual devices need a positive
state. The integral source is `sensor.trailer_outlet_power` (absolute watts). If
the warning remains, adjust that entity in
[Settings > Tools > Statistics](https://www.home-assistant.io/docs/energy/faq/#why-is-my-energy-dashboard-showing-inflated-totals).

Integral sensors use Riemann **left** + `max_sub_interval` 5 minutes per the
[Integral energy example](https://www.home-assistant.io/integrations/integration/#energy).

If glance history is empty, this HA instance has no `default_config:` -- the
install script adds `recorder:` and `history:` when missing
([Recorder](https://www.home-assistant.io/integrations/recorder/),
[History](https://www.home-assistant.io/integrations/history/)).
It also adds `energy:` so the Energy settings page exists
([Energy FAQ](https://www.home-assistant.io/docs/energy/faq/#the-energy-dashboard-is-not-visible)).

---

## Graphs (Solar plant History + Now)

The MQTT **Solar** sidebar is the full entity list. Extra live points belong on
**Solar plant** stock cards, not as Energy grid/solar.

Official cards:

- [History graph](https://www.home-assistant.io/dashboards/history-graph/) -- at most
  **eight** entities per card; group by `unit_of_measurement` (switches with no
  unit get their own on/off graphs)
- [Statistics graph](https://www.home-assistant.io/dashboards/statistics-graph/) -- kWh helpers
- [Glance](https://www.home-assistant.io/dashboards/glance/)
- [Entities](https://www.home-assistant.io/dashboards/entities/) -- sim dump plug ON/OFF
- [Thermostat](https://www.home-assistant.io/dashboards/thermostat/) -- house Ecobee indoor setpoint (`climate.417373300314`, name **Ecobee**; not trailer)
- [Weather forecast](https://www.home-assistant.io/dashboards/weather-forecast/) -- outdoor ambient + daily/hourly forecast (`weather.417373300314`; same Overview popup)
- [Distribution](https://www.home-assistant.io/dashboards/distribution/) -- Instant W

Do **not** add these to Energy sources: shunt Ah/min/RSSI, Sungold PV/V/A/Hz/faults,
hygrometer, climate humidity, KU equal-share, A1 monthly, A3 as grid.

### Now (group by bus, no duplicate cards)

Group **T2 with T2**, **KU with KU**, **Sungold with Sungold**, dump with dump,
house climate with house climate. Do **not** put a gauge row of the same watts
that already sit in those glances. T2 and KU are **sibling** [glance](https://www.home-assistant.io/dashboards/glance/)
cards so [masonry](https://www.home-assistant.io/dashboards/masonry/) can size each box.
Do **not** wrap them in a [grid](https://www.home-assistant.io/dashboards/grid/) (`columns: 2`):
that packs both into **one** masonry column and glance `text-overflow: ellipsis` clips
`Jumper est.` / watts (`hui-glance-card.ts`). Glance `columns: 3` (not omitted: omit =
`min(n, 5)`). [Vertical stack](https://www.home-assistant.io/dashboards/vertical-stack/)
holds dump and house so masonry cannot split those groups.

**Instant W** is the only mixed-bus pie (live clamps + dump). Bus detail watts
stay in that bus glance. Per-plug dump watts stay on **History**.

| Card | Entities |
|------|----------|
| Intro markdown | Energy sankey hint; dump header toggle is manual; Sungold AC out = total INV OUTPUT LOAD KW; trailer outlet = Sungold A/C-in (not LED/vent); KU PV est. may be negative at night |
| Instant W distribution | T2 MPPT, Sungold **AC out**, Sungold PV, Sim dump — **no** trailer outlet (that would double-count Sungold A/C-in vs A/C-out), **no** KU PV est., **no** LED/vent tiles, **no** KU share est. |
| T2 24 V | MPPT W, charge state, charge W, yield today, **Jumper to KU** (`sensor.t2_ku_jumper_at_t2_power`, negative when T2→KU), Batt 1 W/V/A, `sensor.battery_1_state_of_charge`, `sensor.battery_1_consumed_ah`, `sensor.battery_1_remaining_minutes`, RSSI, T2 MPPT conversion loss. Do **not** duplicate as gauges. |
| KU 24 V (est. chargers) | **KU PV est.**, **KU share est.** (`ku_charger_equal_share_power` = KU PV / 3; not a battery, not a Victron clamp), **Jumper from T2** (`sensor.t2_ku_jumper_power`, positive when T2→KU). Batt 2 W/V/A, SoC, consumed Ah, remaining min, RSSI. Do **not** put Sungold A/C-in here. Do **not** put KU share on a T2/battery gauge row. |
| Sungold | One glance: cart PV/batt + **Sungold A/C-in** (`trailer_outlet_power`) + **Sungold A/C out** (`sensor.sungold_sph302480a_load_power` = **total** SPH OUTPUT, not Pi4) + **Trailer CT A3** + **Sungold breaker** (B3) + AC V/Hz/A + faults + Sungold conversion loss. Do **not** split cart vs AC vs Loads. |
| Dump | Markdown + **Dump load HA control** + [entities](https://www.home-assistant.io/dashboards/entities/) `switch.sim_ac_plug_1` ... `_6` (`show_header_toggle: true`). Lab names that say fan are **dump loads**, not trailer LED/fan or Pi4. Kill-switch card does **not** repeat T2/KU shunt W or SPH AC out (those live on T2 / KU / Sungold). |
| House | Thermostat [name](https://www.home-assistant.io/dashboards/thermostat/) **Ecobee** on `climate.417373300314` -- **indoor setpoint** (house, not trailer). Humidity is on History (SoC / %). Device is cloud **ecobee3 lite**, HA area Living Room. Serial `417373300314` is the ecobee identifier ([12-digit ESN](https://support.ecobee.com/s/articles/Where-s-my-ecobee-device-s-serial-number); [ecobee integration](https://www.home-assistant.io/integrations/ecobee)). Energy **Sungold A/C-in** is `sensor.trailer_outlet_power` (watts), not this thermostat and not LED/vent. Stock [weather-forecast](https://www.home-assistant.io/dashboards/weather-forecast/) `weather.417373300314` daily + hourly (`forecast_type` required). Trailer hygrometer Govee H5072/75 MQTT Theengs `sensor.thermo_hygrometer_caaf6f_h5072_75_tempc`, `_hum`, `_batt` (MAC `A4:C1:38:CA:AF:6F`, HA area Front Cargo Trailer; may be unknown if cells are dead -- [DEVICES.md](DEVICES.md)). |

Do **not** add a **Loads (not losses)** card, a **Conversion losses** card, **Sungold cart** /
**Sungold AC** split, or headline [gauge](https://www.home-assistant.io/dashboards/gauge/) stacks.
T2/Sungold conversion-loss watts live on those bus glances. Combined total is History
**Watts (losses)** (`sensor.solar_component_losses_power`).

### History (one unit per graph, max 8)

| Graph | Entities (live ids) |
|-------|---------------------|
| Watts | `solar_controller_solar`, `battery_1_power`, `battery_2_power`, `t2_ku_jumper_power`, `trailer_outlet_power` (label **Sungold A/C-in**), `sim_dump_load_power`, `sungold_sph302480a_load_power` (label **Sungold A/C out**), `sungold_sph302480a_pv_power` |
| Watts (chargers) | `ku_unmetered_pv_est_power`, `ku_charger_equal_share_power`, `solar_controller_charging_power`, `sungold_sph302480a_charging_power` |
| Watts (losses) | `solar_component_losses_power`, `t2_mppt_conversion_loss_power`, `sungold_conversion_loss_power` |
| Sim dump plugs | `switch.sim_ac_plug_1` ... `_6` (on/off) |
| Sim dump plug W | `sensor.sim_ac_plug_1_power` ... `_6_power` plus aggregate `sim_dump_load_power` |
| Hz | Sungold `grid_frequency`, `ac_output_frequency` |
| Volts | `battery_1_voltage`, `battery_2_voltage`, `solar_controller_battery`, `sungold_sph302480a_battery_voltage`, `sungold_sph302480a_pv_voltage`, `sungold_sph302480a_grid_voltage`, `sungold_sph302480a_ac_output_voltage` |
| Amps | `battery_1_current`, `battery_2_current`, `solar_controller_battery_charging`, `sungold_sph302480a_battery_current`, `sungold_sph302480a_pv_current`, `sungold_sph302480a_load_current`, `sungold_sph302480a_grid_current` |
| SoC / % | `battery_1_state_of_charge`, `battery_2_state_of_charge`, `sungold_sph302480a_battery_soc`, Ecobee `sensor.417373300314_humidity`, trailer hygrometer hum/batt |
| Temperature | Ecobee `sensor.417373300314_temperature`, trailer hygrometer tempc, Sungold batt/heatsink temps |
| kWh (statistics-graph) | T2 MPPT + batt 1/2 charge/discharge + Sungold A/C-in (`em16_a3_energy_kwh` from trailer outlet W) + Sungold A/C out + sim dump |

`hours_to_show: 72` on history-graph ([history graph](https://www.home-assistant.io/dashboards/history-graph/); minimum 1 hour).
`days_to_show: 7` on the kWh statistics-graph ([statistics graph](https://www.home-assistant.io/dashboards/statistics-graph/); minimum 1 day).
After YAML copy, dashboard three-dots **Refresh** (not only the browser reload).

This HA has no `default_config:`. Recorder/history started when `recorder:` / `history:` were appended
([Recorder](https://www.home-assistant.io/integrations/recorder/) `purge_keep_days` default **10** if unset).
States history cannot pre-date that. Long-term statistics (hourly) are kept for sensors with
`state_class` `measurement`, `total`, or `total_increasing` and are never purged
([History](https://www.home-assistant.io/integrations/history/)).

**History sidebar (longer range than the card):** left sidebar **History** (built-in History dashboard),
pick the MPPT entities, then set the time frame
([History panel](https://www.home-assistant.io/integrations/history/#exporting-data-from-the-history-panel),
[History dashboard](https://www.home-assistant.io/dashboards/dashboards/#history-dashboard)).

Do **not** treat `sensor.solar_controller_yield_today` as multi-day kWh. It is Victron Instant Readout
**yield today** (Wh, resets each day; `state_class: total_increasing` is valid for a daily meter)
([BlueSolar monitoring](https://www.victronenergy.com/media/pg/Manual_BlueSolar_MPPT_75-10_up_to_100-20/en/monitoring.html)).
Multi-day energy in HA is `sensor.t2_mppt_energy_kwh` (Riemann integral, `state_class: total`).
Days before recorder existed are not in HA; VictronConnect **History** on the charger still holds
the last 30 daily yield bars.

**18 Sep 2026 T2** (two 200 W suitcases, 400 W STC): peak **356 W**, yield today **1670 Wh**.
Damaged suitcases (shattered cargo-trailer glass with film still sealed; PWM wing hot-spot
on unfold) stay in the array -- [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md#suitcase-panel-condition-operator-2026-09-19).
PWM is still unmetered; do not read T2 as a PWM clamp.

---

## Retired SVG (`:8765`)

The custom GX proxy is gone. After pull on `.105`:

```bash
bash scripts/uninstall_solar_flow.sh
```
