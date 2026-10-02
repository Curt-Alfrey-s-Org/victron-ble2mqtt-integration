# Solar plant (Home Assistant Energy)

**Energy** on **`.105:8123`** stays the simple built-in sankey. The detailed one-line is Grafana Canvas **Solar plant one-line** at `http://192.168.0.107:3000` (uid `solar-plant-oneline`). Node-RED still owns derived watts. See [SOLAR_DIAGRAM_POLICY.md](SOLAR_DIAGRAM_POLICY.md).

**Home Assistant** on **`.105:8123`**: built-in **Energy**
for kWh / Sankey, MQTT **Solar** for discovery, and **Site solar** (`/site-solar`)
for device tiles. Site solar is **storage** mode so you can move cards.

| Surface | Who draws it | What you plug in |
|---------|----------------|------------------|
| [Energy](https://www.home-assistant.io/docs/energy/) | HA (built-in) | kWh + W sensors via [Energy settings](https://www.home-assistant.io/docs/energy/) / `energy/save_prefs` |
| [Home](https://www.home-assistant.io/dashboards/dashboards/#home-dashboard) | HA (built-in) | Devices assigned to [areas](https://www.home-assistant.io/docs/organizing/areas/) (official sections view) |
| Sidebar **Solar** | HA storage + MQTT discovery | Live Victron / Sungold / shunt tiles. Live-only (not in git); its cards are being merged onto Site solar, see [SOLAR_TAB_MERGE_PLAN.md](SOLAR_TAB_MERGE_PLAN.md) |
| **Site solar** | HA **storage** Lovelace | Leftover live tiles Energy cannot plot (jumper, KU est., dump, NWS, Ecobee). Cards are movable. |
| [History](https://www.home-assistant.io/dashboards/dashboards/#history-dashboard) | HA (built-in) | Pick entities; no YAML cards |

The custom SVG proxy on `:8765` is **retired** ([SOLAR_FLOW_DASHBOARD.md](SOLAR_FLOW_DASHBOARD.md)).

**Built-in first.** [Energy](https://www.home-assistant.io/docs/energy/) is kWh / Sankey.
MQTT **Solar** is the discovery list. Leftover live tiles go on **Site solar**
(`/site-solar`) as a **storage** dashboard
([creating a dashboard](https://www.home-assistant.io/dashboards/dashboards/#creating-a-new-dashboard);
[lovelace/dashboards/create](https://github.com/home-assistant/core/blob/master/homeassistant/components/lovelace/dashboard.py)
+ `lovelace/config/save`). `mode: storage` lets you move cards in the UI.
A [YAML dashboard](https://www.home-assistant.io/dashboards/dashboards/#adding-yaml-dashboards)
(`mode: yaml`) is **file-only**. Do **not** re-register YAML Lovelace.

`config/dashboards/solar-plant.yaml` is the official-card seed for that storage
dashboard. The package install script **does not** register it as YAML and
**unregisters** `/solar-plant` if a prior install added it. Do **not** add HACS /
`custom:` cards.

**Data YAML (keep):** package `config/packages/solar_plant.yaml` -- template
W sensors and Riemann kWh ([Template](https://www.home-assistant.io/integrations/template/),
[Integral](https://www.home-assistant.io/integrations/integration/#energy),
[packages](https://www.home-assistant.io/docs/configuration/packages/)).
That is how numbers get **into** Energy. Dump on/off stays
`dump_control.yaml` ([DUMP_LOAD_HA_CONTROL.md](DUMP_LOAD_HA_CONTROL.md));
knobs live under **Settings > Helpers** (`input_boolean.dump_control_enabled`).

Site physics: [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md).
Energy solar clamp is the **paired KU 75/15** (`sensor.solar_controller_solar`) only until T2 100/50 and second KU 75/15 keys exist. Do **not** add KU equal-share (retired 2026-10-02) or A3 as grid.
Dump is an Energy **individual device** nested under Sungold AC-out
(`included_in_stat` in `save_solar_plant_energy_prefs.py`).
Sungold A/C out is the house-load device. Trailer-outlet A/C-in is a Site solar
tile only, not a second Energy device.

### Phone (Companion)

This HA has no `default_config:` (Bluetooth / Cloud / USB stay off on `.105`).
Companion needs [Mobile App](https://www.home-assistant.io/integrations/mobile_app/)
`mobile_app:` only (`install_solar_plant_ha.sh` appends it). Do **not** add
`default_config:`.

Official [Companion](https://companion.home-assistant.io/docs/getting_started/):
LAN `http://192.168.0.105:8123`. Away: Tailscale ([TAILSCALE.md](TAILSCALE.md)).
On **that phone**: User profile or Settings > Dashboards > **Energy** >
**Set as default on this device**
([default dashboard](https://www.home-assistant.io/dashboards/dashboards/#setting-a-default-dashboard)).
Do **not** port-forward `:8123`.

---

## What you get

| Surface | Role |
|---------|------|
| **Energy** (built-in) | Solar / battery / load now + today. HA draws it. |
| **Home** (built-in) | Area tiles after devices have [areas](https://www.home-assistant.io/docs/organizing/areas/) |
| **Solar** sidebar | MQTT entity list |
| Template sensors | Jumper est., trailer outlet W, KU PV est., site solar/charge sums |
| Integral sensors | kWh for Energy (paired 75/15 MPPT, batteries, trailer outlet, dump, Sungold load) |
| NWS REST | `sensor.nws_watauga_lake_alerts` (package; not an Energy card) |

HA Energy / `power-sankey` is a **sources / battery / home / devices** Sankey, not a
Victron GX two-bus cartoon. Only one Victron MPPT is live in HA (paired KU 75/15). T2 100/50 and second KU 75/15 have **no** entities until Instant Readout keys ([DEVICES.md](DEVICES.md)).

---

## Template entity ids

| entity_id | Meaning |
|-----------|---------|
| `sensor.t2_ku_jumper_power` | T2 leftover `solar_controller_solar - battery_1_power` (T2 Renogy idle = 0). **Canonical + = T2→KU.** **Shunt-to-shunt:** those watts are already in Battery 1 and Battery 2. Used to **isolate** KU PV est. (subtract T2-sourced charge from Batt 2), on the **KU** tile (**Jumper from T2**), and History. Not a third generation/load clamp. Do **not** add into Solar now / Charge now / Load now ([SmartShunt installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html) step 2). |
| `sensor.t2_ku_jumper_at_t2_power` | Same leftover, T2-end sign: `-(t2_ku_jumper_power)`. **T2 tile only** (**Jumper to KU**). Negative = leaving T2 (T2→KU); positive = arriving at T2 (KU→T2). Not extra watts. Do **not** Riemann this. Do **not** put it on History. |
| `sensor.trailer_outlet_power` | `\|B3\|` if \|B3\| >= 0.5 W, else `\|A3\|`. EM16 hot leg on the KU trailer outlet (Sungold UTI cord). Vent fan and LEDs are on **Sungold AC out**, not a separate A3 sibling. |
| `sensor.ku_renogy_ac_load_power` | `max(trailer_outlet_power, sungold_uti_va_power)`. KU Renogy inverter AC load (cord into Sungold UTI). Not house load. |
| `sensor.sungold_cart_to_load_power` | `max(0, Sungold AC-out − ku_renogy_ac_load)`. **0** while KU feeds every house watt (T2 RV empty; mains bypass). Nonzero only if the cart/PV invert into AC-out. |
| `sensor.ku_unmetered_pv_est_power` | Legacy combined lower bound (`battery_2_power - jumper + ku_renogy_ac_load_power`). **Retired** as equal-share / PWM truth (2026-10-02); Node-RED may still compute until script update. |
| `sensor.ku_charger_equal_share_power` | **Retired 2026-10-02** (was KU PV est. / 3 for two MPPTs + PWM). |
| `sensor.battery_1_charge_power` / `_discharge_power` | `max(0, +/- battery_1_power)` |
| `sensor.battery_2_charge_power` / `_discharge_power` | same for Battery 2 |
| `sensor.t2_mppt_conversion_loss_power` | Paired 75/15 conversion loss: `max(0, solar_controller_solar - charge - load)`; skip when charge 0/missing and jumper flowing |
| `sensor.sungold_conversion_loss_power` | Sungold `SG_loss`: `max(0, (UTI V×A + PV) - batt_in - AC_out)`. `0` V×A is valid. Do **not** substitute AC-out for missing/zero AC INPUT. |
| `sensor.sungold_uti_va_power` | Sungold grid `\|V × A\|` ([reprint](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf) §4.1 AC INPUT). Cross-check vs trailer clamp. Not house load. |
| `sensor.sungold_ac_out_va_power` | Sungold `\|AC out V × Load A\|`. Cross-check vs LCD `load_power`. |
| `sensor.solar_component_losses_power` | `combined_losses_w` = paired 75/15 MPPT loss + Sungold loss ([SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md)) |
| `sensor.site_solar_power` | **Site solar now:** T2 `solar_controller_solar` + Sungold `sungold_sph302480a_pv_power` + `max(0, ku_unmetered_pv_est_power)`. Missing addends count as 0. Night KU est. is clamped so solar is not a negative residual. Attributes `t2_w`, `sph_pv_w`, `ku_est_w`, `ku_clamped_w` ([template attributes](https://www.home-assistant.io/integrations/template/)). |
| `sensor.site_charge_power` | **Site charge now:** into the three packs — `battery_1_charge_power` + `battery_2_charge_power` + `max(0, sungold_sph302480a_charging_power)`. Not T2 MPPT `charging_power` (that can leave T2 on the jumper). |
| `sensor.site_solar_energy_kwh` | Riemann of `site_solar_power` ([Integral](https://www.home-assistant.io/integrations/integration/#energy), left + 5 min). **Lifetime** total; use `sensor.site_solar_today` on Site totals. |
| `sensor.site_charge_energy_kwh` | Riemann of `site_charge_power` (same method). Lifetime; use `sensor.site_charge_today`. |
| `sensor.site_solar_today` | [Utility meter](https://www.home-assistant.io/integrations/utility_meter/) daily on `site_solar_energy_kwh` -- **Solar today** tile. |
| `sensor.site_charge_today` | Daily utility meter on `site_charge_energy_kwh` -- **Charge today** tile. |
| `sensor.sungold_load_today` | Daily utility meter on `sungold_load_energy_kwh` -- **Load today** tile. |

**Site load** reuses `sensor.sungold_sph302480a_load_power` / `sensor.sungold_load_energy_kwh` (Sungold INV OUTPUT). Do **not** add a second load template or integral. Do **not** add dump watts or trailer-outlet (AC-in) into that total -- dump is on Sungold OUTPUT; AC-in is the cord, not house load. T2/KU Renogy inverter loads are **not in HA**.

**Today** kWh is the built-in [Energy dashboard](https://www.home-assistant.io/docs/energy/)
(calendar day in this HA `time_zone` `America/New_York`). Package Riemann sensors
feed Energy; do **not** add a Utility Meter (first cycle incomplete --
[utility meter](https://www.home-assistant.io/integrations/utility_meter/)).
Do **not** put `energy-sources-table` on a custom Lovelace view: Energy solar is
T2-only ([energy cards](https://www.home-assistant.io/dashboards/energy/)).
Energy individual device is Sungold **AC-out**
([individual devices](https://www.home-assistant.io/docs/energy/individual-devices/)).
The sim dump device is retired (2026-09-28); H5082 dump sockets report no watts.
Do **not** add trailer-outlet / Sungold AC-in as a house-load device (that double-counts
the cord against INV OUTPUT).

Do **not** treat KU equal-share as a live Victron watt clamp. Do **not** add A3 as
utility grid. Do **not** put `sensor.ku_unmetered_pv_est_power` on Energy as solar -- night
**negative** values are balance residual / losses, not KU solar generation.

---

## Enable on `.105` (one path)

**Prerequisites:** HA Container `homeassistant`, config `/opt/homeassistant`, victron
clone pulled.

```bash
cd /home/ansible/victron-ble2mqtt-integration
bash scripts/install_solar_plant_ha.sh
```

The script copies the **package** (sensors). It does **not** register a YAML
Lovelace dashboard ([YAML dashboards](https://www.home-assistant.io/dashboards/dashboards/#adding-yaml-dashboards)
are not movable in the UI). If a prior install added `lovelace: solar-plant`,
the script unregisters it. It appends `recorder:` / `history:` / `energy:` /
`mobile_app:` when missing,
refreshes `packages/dump_control.yaml` **if that file is already installed**
(and removes a retired `sim_dump_control.yaml` / `sim_dump_plugs.yaml`),
runs `check_config`, then `docker restart homeassistant`.

Open **Energy** (sidebar, or Settings > Dashboards > Energy). Configure sources
once with `python scripts/save_solar_plant_energy_prefs.py` if they are empty (it backs
up the live prefs and refuses to change configured prefs without `--force`).

Seed leftover tiles onto **Site solar** (storage, movable) from a host that can
reach `.105:8123`, with the long-lived token in `HA_TOKEN` or `HA_TOKEN_FILE`
(never commit the token):

```bash
python scripts/save_solar_plant_storage_dashboard.py            # first time: creates it
python scripts/save_solar_plant_storage_dashboard.py --dry-run  # compare only
python scripts/save_solar_plant_storage_dashboard.py --force    # replace UI edits
```

The script always backs up the live `/site-solar` config first
(`.backups/site-solar/<stamp>-before-seed/`, git-ignored). If a dashboard already
exists and differs from the seed it **refuses** (exit 3) unless you pass `--force`, so
UI edits are no longer overwritten by accident. Undo a forced save with
`python3 scripts/site_solar_settings.py restore --from <folder> --dashboard`.
Export / restore helper values and the dashboard at any time with
`python3 scripts/site_solar_settings.py export` / `restore --from LATEST --helpers`.

Open:

```text
http://192.168.0.105:8123/energy
http://192.168.0.105:8123/site-solar
```

Do **not** re-add `mode: yaml`.

### One session on `.105` (`site_solar_session.sh`)

The token / wait / backup / seed commands usually run together, so one wrapper does them
in order, printing a `==> step` line for each:

```bash
cd ~/victron-ble2mqtt-integration
bash scripts/site_solar_session.sh backup               # pull, token, wait for HA, backup
bash scripts/site_solar_session.sh solar-compare        # + export the Solar tab, print the compare table
bash scripts/site_solar_session.sh dashboard-dry-run    # + seed --dry-run (writes nothing to HA)
bash scripts/site_solar_session.sh dashboard-apply      # + seed --force (replaces UI edits; backed up first)
bash scripts/site_solar_session.sh restore --from LATEST --dashboard --dry-run   # passthrough
```

Every action first:

1. goes to the repo root and runs `git pull --ff-only origin main` (default on; `--no-pull` skips it);
2. uses `$HA_TOKEN_FILE`, else `~/.ha_token`; if neither exists it creates `~/.ha_token`
   with `install -m 600 /dev/null` and opens `${EDITOR:-nano}` so you paste a long-lived
   token there (the token is never read from the terminal or printed);
3. exports `HA_TOKEN_FILE` and `HA_URL` (default `http://127.0.0.1:8123`; an `HA_URL`
   already in the environment wins);
4. waits for HA with `curl` (`--wait SECONDS`, default 300, then stops with a message);
5. backs up with `python3 scripts/site_solar_settings.py export`.

`dashboard-dry-run` runs `save_solar_plant_storage_dashboard.py --dry-run`; if that
refuses (exit 3: live `/site-solar` has UI edits), it also shows what `--force` would do,
still writing nothing. `dashboard-apply` runs `--force` and prints the restore command.

On exit (success or failure) a trap removes `~/.ha_token` **only if this run created it**
(`--keep-token` keeps it), removes `config/dashboards/exports/solar-tab.json` if this run
created it (`--keep-export` keeps it), and unsets `HA_TOKEN_FILE`. Run it with `bash`, not
`source`. `bash scripts/site_solar_session.sh --help` prints the full usage.

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
python scripts/save_solar_plant_energy_prefs.py          # only when prefs are empty or already match
python scripts/save_solar_plant_energy_prefs.py --force  # replace configured prefs
```

That command backs up the live prefs, then writes the table below (without `--force`
it refuses when Energy is already configured differently, exit 3). It does **not** add grid, Electricity Maps,
gas, water, A1 monthly kWh, or KU equal-share solar.

Add **power** sensors (W) and the matching **integral kWh** sensors:

| Energy slot | Power (W) | Energy (kWh, after integral exists) |
|-------------|-----------|-------------------------------------|
| Solar | `sensor.solar_controller_solar` | `sensor.t2_mppt_energy_kwh` |
| Battery T2 | charge `sensor.battery_1_charge_power`, discharge `sensor.battery_1_discharge_power` | matching `*_energy_kwh` |
| Battery KU | charge/discharge `sensor.battery_2_*` | matching `*_energy_kwh` |
| Device: Sungold A/C out | `sensor.sungold_sph302480a_load_power` | `sensor.sungold_load_energy_kwh` |

The script also sets the display name (Sungold A/C out). Trailer-outlet
(`sensor.trailer_outlet_power` / `sensor.em16_a3_energy_kwh`) stays on Site solar
tiles and History; it is **not** an Energy house-load device. Dump loads are
already inside Sungold INV OUTPUT, so they get no Energy device of their own.
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

### After Site solar math fix (history / statistics)

HA cannot recompute past **states** from a new template formula. Deploy fixed
YAML first, then **wipe solar-related HA history** so bad template math does not
taint Energy / statistics going forward.

1. **`.105`:** `bash scripts/install_solar_plant_ha.sh` (reloads `solar_plant.yaml`).
2. **Energy prefs:** `python scripts/save_solar_plant_energy_prefs.py --force` (drops
   Sungold A/C-in as a house device and the retired Sim dump device).
3. **Site solar Lovelace:** re-seed storage dashboard from repo YAML if Load now
   still points at the wrong entity (see install script / storage seed docs).
4. **Purge recorder + statistics (recommended after formula fix):**
   ```bash
   cd ~/victron-ble2mqtt-integration
   python scripts/purge_solar_plant_ha_history.py --dry-run
   python scripts/purge_solar_plant_ha_history.py --apply
   ```
   Uses [recorder.purge_entities](https://www.home-assistant.io/actions/recorder/purge_entities/)
   (`keep_days: 0`) and WebSocket `recorder/clear_statistics` for Victron,
   Sungold, site totals, retired sim dump leftovers, and `solar_plant.yaml` helpers. Excludes NWS
   and Ecobee. Set `HA_TOKEN` or `HA_TOKEN_FILE` (admin long-lived token).
5. **Victron / Sungold on-device logs** are unchanged; only the Home Assistant
   database is cleared. Integral kWh sensors restart from zero after purge.

`sensor.em16_a3_power` is a signed CT. Integrating it made `sensor.em16_a3_energy_kwh`
negative (`-0.02` kWh) and Energy warned that individual devices need a positive
state. The integral source is `sensor.trailer_outlet_power` (absolute watts). If
the warning remains, adjust that entity in
[Settings > Tools > Statistics](https://www.home-assistant.io/docs/energy/faq/#why-is-my-energy-dashboard-showing-inflated-totals).

Integral sensors use Riemann **left** + `max_sub_interval` 5 minutes per the
[Integral energy example](https://www.home-assistant.io/integrations/integration/#energy).

If graph history is empty, this HA instance has no `default_config:` -- the
install script adds `recorder:` and `history:` when missing
([Recorder](https://www.home-assistant.io/integrations/recorder/),
[History](https://www.home-assistant.io/integrations/history/)).
It also adds `energy:` so the Energy settings page exists
([Energy FAQ](https://www.home-assistant.io/docs/energy/faq/#the-energy-dashboard-is-not-visible)).

---

## Graphs (Site solar + Energy + History)

The MQTT **Solar** sidebar is the full discovery list. Extra live points live on
**Site solar** (`/site-solar` storage). Do **not** add them as Energy grid/solar.

Official cards:

- [History graph](https://www.home-assistant.io/dashboards/history-graph/) -- at most
  **eight** entities per card; group by `unit_of_measurement` (switches with no
  unit get their own on/off graphs)
- [Statistics graph](https://www.home-assistant.io/dashboards/statistics-graph/) -- kWh helpers
- [Tile](https://www.home-assistant.io/dashboards/tile/) -- one live value per tile on **Now**
- [Statistic](https://www.home-assistant.io/dashboards/statistic/) -- History / Energy only (not Site totals **today**; use utility meters below)
- [Heading](https://www.home-assistant.io/dashboards/heading/) -- totals / bus / dump / house section titles
- [Entities](https://www.home-assistant.io/dashboards/entities/) -- Dump voltages / limits / plug wiring
- [Thermostat](https://www.home-assistant.io/dashboards/thermostat/) -- house Ecobee indoor setpoint (`climate.417373300314`, name **Ecobee**; not trailer)
- [Weather forecast](https://www.home-assistant.io/dashboards/weather-forecast/) -- outdoor ambient + daily/hourly forecast (`weather.417373300314`; same Overview popup)
- [Picture](https://www.home-assistant.io/dashboards/picture/) -- NWS Morristown **KMRX** standard radar loop (plays on the page)
- [Distribution](https://www.home-assistant.io/dashboards/distribution/) -- Instant W

Do **not** add these to Energy sources: shunt Ah/min/RSSI, Sungold PV/V/A/Hz/faults,
hygrometer, climate humidity, KU equal-share, A1 monthly, A3 as grid,
`site_solar_energy_kwh` / `site_charge_energy_kwh` (T2 solar and pack charge
are already Energy sources; the site sums would double-count).

### Now (group by bus, no duplicate cards)

Group **T2 with T2**, **KU with KU**, **Sungold with Sungold**, dump with dump,
house climate with house climate. Each group is one [sections](https://www.home-assistant.io/dashboards/sections/)
`type: grid` block with a [heading](https://www.home-assistant.io/dashboards/heading/)
and [tiles](https://www.home-assistant.io/dashboards/tile/) (or stock
thermostat / weather / picture / entities). Do **not** put a gauge row of the
same watts that already sit on those tiles. Do **not** use masonry glance
`columns: 3` (phone clip). Do **not** use vertical-stack just to keep a group
together.

**Instant W** is the only mixed-bus pie (live clamps + dump). Bus detail watts
stay on that bus's tiles. H5082 dump sockets have no watt reading.

| Card | Entities |
|------|----------|
| Site totals | First **Now** section. Heading + markdown (what is summed) + tiles **Solar now** / **Charge now** / **Load now** + **Solar today** / **Charge today** / **Load today** on `sensor.site_solar_today`, `sensor.site_charge_today`, `sensor.sungold_load_today` ([utility meter](https://www.home-assistant.io/integrations/utility_meter/) daily on each kWh integral). Do **not** use statistic-card `change` on `*_energy_kwh` (lifetime state != today). Load now/today = Sungold AC out / `sungold_load_today`. |
| Intro markdown | Energy sankey hint; dump header toggle is manual; Sungold AC out = total INV OUTPUT LOAD KW; trailer outlet = Sungold A/C-in (not LED/vent). Do **not** show KU PV est or KU share est (unmetered residual, not a clamp). |
| Instant W distribution | T2 MPPT, Sungold **AC out**, Sungold PV — **no** trailer outlet (that would double-count Sungold A/C-in vs A/C-out), **no** KU PV est., **no** LED/vent tiles, **no** KU share est. |
| T2 24 V | Heading + tiles: MPPT W, charge state, charge W, yield today, **Jumper to KU** (`sensor.t2_ku_jumper_at_t2_power`, leftover already in Batt 1; negative when T2→KU), Batt 1 W/V/A, `sensor.battery_1_state_of_charge`, `sensor.battery_1_consumed_ah`, `sensor.battery_1_remaining_minutes`, RSSI, T2 MPPT conversion loss. Do **not** duplicate as gauges. |
| KU 24 V | Heading + tiles: **Jumper from T2**, Batt 2 W/V/A, SoC, consumed Ah, remaining min, RSSI. No KU PV est / KU share est (those sensors stay in the package for Solar now clamp only). Do **not** put Sungold A/C-in here. |
| KU outlet to Sungold | Measured cord only: **Trailer outlet**, **Trailer CT A3**, B3 breaker, UTI V×A, AC out V×A, Cart to AC out, Sungold conversion loss. No KU Renogy AC est tile. |
| Sungold | Sungold MQTT only (LCD §4.1 names): PV V/A/W, INPUT BATT kW/V/A, remaining battery, charge state, output mode, INV OUTPUT LOAD KW, AC INPUT V/A/Hz, OUTPUT LOAD V/Hz/A, fault / error flags. **No** EM16, **no** V×A helpers, **no** battery temperature (not an LCD page; 0 °C shows as 32 °F). Unknown output-mode codes stay the raw integer. |
| Dump | One section per box (heading, help card with a Help link, then the box): master switch, status (why / why not, plus **Dump sockets by name (live)**), voltage, start conditions, confirm, inverter AC limits, battery limits, alerts, timers (auto-entities over `timer.h5082_*`), **Plugs** (button-card per socket), **Plug names (Where / Load)** (live **Current names** table + per-plug entities), **Socket Use** and **Socket inverter** (auto-entities templates naming each row from the live Where / Load text), activity log and settings change log. See [DUMP_LOAD_HA_CONTROL.md](DUMP_LOAD_HA_CONTROL.md#site-solar-help-one-page-per-dashboard-box). What is plugged into each socket and where each plug is are **never** written in the seed: they are the `input_text.h5082_<id>_location` / `_<side>_load` helpers, with the plug id and side shown when blank. Do **not** repeat T2/KU shunt W or Sungold AC out here. |
| House | Thermostat [name](https://www.home-assistant.io/dashboards/thermostat/) **Ecobee** on `climate.417373300314` -- **indoor setpoint** (house, not trailer). Humidity is on History (SoC / %). Device is cloud **ecobee3 lite**, HA area Living Room. Serial `417373300314` is the ecobee identifier ([12-digit ESN](https://support.ecobee.com/s/articles/Where-s-my-ecobee-device-s-serial-number); [ecobee integration](https://www.home-assistant.io/integrations/ecobee)). Site solar **Sungold A/C-in** is `sensor.trailer_outlet_power` (watts), not this thermostat and not LED/vent. Stock [weather-forecast](https://www.home-assistant.io/dashboards/weather-forecast/) `weather.417373300314` daily + hourly (`forecast_type` required). **NWS KMRX radar** is a [picture](https://www.home-assistant.io/dashboards/picture/) of the official standard loop `https://radar.weather.gov/ridge/standard/KMRX_loop.gif` ([animated GIFs](https://www.weather.gov/radarfaq/), [ridge/standard](https://radar.weather.gov/ridge/standard/)). [api.weather.gov points](https://www.weather.gov/documentation/services-web-api) for Watauga Lake `36.32,-82.12` returns `radarStation: KMRX` (Hampton / Carter County). The GIF **plays on this page**. Tap opens [KMRX standard radar](https://radar.weather.gov/station/KMRX/standard). Alerts: `sensor.nws_watauga_lake_alerts` ([RESTful](https://www.home-assistant.io/integrations/rest/), NWS `User-Agent` required). Do **not** iframe `radar.weather.gov` RIDGE2 (GIS app; [webpage card](https://www.home-assistant.io/dashboards/iframe/) is for pages that allow embedding). Do **not** add HACS radar cards. Optional later: [Generic Camera](https://www.home-assistant.io/integrations/generic/) UI still-image URL uses the same NWS `ridge/standard` path (HA example is `CONUS_0.gif`). Trailer hygrometer Govee H5072/75 MQTT Theengs `sensor.thermo_hygrometer_caaf6f_h5072_75_tempc`, `_hum`, `_batt` (MAC `A4:C1:38:CA:AF:6F`, HA area Front Cargo Trailer; may be unknown if cells are dead -- [DEVICES.md](DEVICES.md)). |

Do **not** add a **Loads (not losses)** card, a **Conversion losses** card, **Sungold cart** /
**Sungold AC** split, or headline [gauge](https://www.home-assistant.io/dashboards/gauge/) stacks.
T2/Sungold conversion-loss watts live on those bus tiles. Combined total is History
**Watts (losses)** (`sensor.solar_component_losses_power`).

### History (one unit per graph, max 8)

| Graph | Entities (live ids) |
|-------|---------------------|
| Watts | `solar_controller_solar`, `battery_1_power`, `battery_2_power`, `t2_ku_jumper_power`, `trailer_outlet_power` (label **Sungold A/C-in**), `sungold_sph302480a_load_power` (label **Sungold A/C out**), `sungold_sph302480a_pv_power` |
| Watts (chargers) | `solar_controller_charging_power`, `sungold_sph302480a_charging_power` (no KU PV/share est on the graph) |
| Watts (losses) | `solar_component_losses_power`, `t2_mppt_conversion_loss_power`, `sungold_conversion_loss_power` |
| H5082 sockets | Site solar **Plugs** cards. On/off, Where, Load, Use, and Inverter. Grafana tables read `solar_plant_socket`. Sim dump switches and packages are removed. |
| Hz | Sungold `grid_frequency`, `ac_output_frequency` |
| Volts | `battery_1_voltage`, `battery_2_voltage`, `solar_controller_battery`, `sungold_sph302480a_battery_voltage`, `sungold_sph302480a_pv_voltage`, `sungold_sph302480a_grid_voltage`, `sungold_sph302480a_ac_output_voltage` |
| Amps | `battery_1_current`, `battery_2_current`, `solar_controller_battery_charging`, `sungold_sph302480a_battery_current`, `sungold_sph302480a_pv_current`, `sungold_sph302480a_load_current`, `sungold_sph302480a_grid_current` |
| SoC / % | `battery_1_state_of_charge`, `battery_2_state_of_charge`, `sungold_sph302480a_battery_soc`, Ecobee `sensor.417373300314_humidity`, trailer hygrometer hum/batt |
| Temperature | Ecobee `sensor.417373300314_temperature`, trailer hygrometer tempc, Sungold batt/heatsink temps |
| kWh (statistics-graph) | T2 MPPT + batt 1/2 charge/discharge + Sungold A/C-in (`em16_a3_energy_kwh` from trailer outlet W) + Sungold A/C out |

`hours_to_show: 72` on history-graph ([history graph](https://www.home-assistant.io/dashboards/history-graph/); minimum 1 hour).
`days_to_show: 7` on the kWh statistics-graph ([statistics graph](https://www.home-assistant.io/dashboards/statistics-graph/); minimum 1 day).

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
Damaged suitcases (shattered cargo-trailer glass with film still sealed; historical hot-spot note
on unfold) stay in the array -- [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md#suitcase-panel-condition-operator-2026-09-19).
PWM retired 2026-10-02; do not read the paired 75/15 clamp as the T2 100/50.

---

## Retired SVG (`:8765`)

The custom GX proxy is gone. After pull on `.105`:

```bash
bash scripts/uninstall_solar_flow.sh
```

## Node-RED solar diagram (editable canvas)

Live **Site solar** tiles stay in HA. **Build/edit the topology diagram** in Node-RED (`http://192.168.0.105:1880/`, tab **Solar plant diagram**). NR reads HA REST only; see [SOLAR_NODERED_OPERATOR.md](SOLAR_NODERED_OPERATOR.md) and [SOLAR_DIAGRAM_POLICY.md](SOLAR_DIAGRAM_POLICY.md). Do not use Mermaid or SVG for this.

`install_solar_plant_ha.sh` no longer touches **Site solar** (`/site-solar`). It used to
run `sync_site_solar_storage_from_seed.py`, which rewrote `.storage/lovelace.site_solar`
while HA was running, so the repo seed replaced UI edits at the next restart. To load
the seed on purpose (backs up first, see above):

```bash
HA_TOKEN_FILE=... python3 scripts/save_solar_plant_storage_dashboard.py --force
```

`sync_site_solar_storage_from_seed.py` is an **offline** fallback only (HA stopped):
`docker stop homeassistant && sudo python3 scripts/sync_site_solar_storage_from_seed.py --force && docker start homeassistant`.
