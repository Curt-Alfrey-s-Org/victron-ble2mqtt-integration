# Solar flow dashboard (Victron GX-style)

**Status:** Operator doc for a **local** live energy-flow page served from this repo.
Implementation: `scripts/solar_flow_server.py` + static assets (sibling work). No Lovelace
scrape. No HA token in the browser or git.

**Official references (RULE #1):**

- Victron GX UI layout (sources left, storage centre, loads right; dark default; browser
  Remote Console): [Cerbo GX — The new user interface](https://www.victronenergy.com/media/pg/Cerbo_GX/en/the-new-user-interface.html)
- Home Assistant REST `GET /api/states` with `Authorization: Bearer`: [REST API](https://developers.home-assistant.io/docs/api/rest/)
- alfa-ai soak policy (deterministic, not LLM): [HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md)
  (sibling: `../alfa-ai/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md`)

**Site physics:** [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md) — T2 vs KU buses, EM16 A3
semantics, sim soak plugs.

---

## What it is

A **Victron GX Overview**-style single-page view of this site's 24 V plant:

| GX region | This site |
|-----------|-----------|
| **Left — sources** | T2 MPPT (live HA reporter, all BlueSolar datapoints). KU Victron chargers 2-3: **grey unmetered** (no live W; do not print 2x T2 as a reading). KU Renogy PWM: **grey unmetered** (not in HA). |
| **Centre — storage** | Two LiTime 24 V packs: T2 (`HQ2239CQYT2`) and KU (`HQ2239JTRKU`). Jumper is not a numbered bus. |
| **Right — loads** | KU Renogy AC path, EM16 A3 (15 Sep Sungold-AC-in caveat), six sim A/C plugs. T2 Renogy 30A RV is a **grey unmetered** dead-end (idle if no RV). |
| **Island — Sungold cart** | SPH302480A + 2x 100 Ah. **Separate plant** (not merged into T2/KU DC). Live MQTT when the sidecar is up. |
| **Meters — Refoss** | All EM16 A1-C6 numeric channels as **meters**, not extra loads. **Do not add A3+B2.** |

Dark theme by default (matches GX). Numbers on every node: **W**, **V**, **A**, **SoC %**, MPPT
**charge state** where available.

Animated SVG power lines show energy direction when data is flowing. Sim plug **fans** spin when
the switch is ON. **Green LED** = on or flowing; **grey** = off or unavailable.

A side **AI panel** is a **deterministic soak explainer** — same thresholds and allowlist
policy as alfa-ai `src/ops/solar_soak.py`. It is **not** an LLM. It shows thinking text
(surplus math, SoC gate, charge stage, hysteresis, min on/off dwell) and **planned / held**
plug actions. Actuation stays on alfa-ai; this page is read-only for loads.

---

## Topology

```
Browser  http://127.0.0.1:8765/
    |
    v
scripts/solar_flow_server.py   (this repo clone — any LAN host with Python 3)
    |  Authorization: Bearer <token from file>
    |  GET http://192.168.0.105:8123/api/states
    v
Home Assistant Container (.105:8123)
    ^ MQTT / Refoss / Modbus
Pi4 Victron BLE, optional Sungold, Pi5 Theengs, EM16
```

Do **not** call HA from browser JavaScript. Do **not** scrape Lovelace (`/dashboard-solar/0`).
The Python proxy holds the long-lived token server-side only
([REST API](https://developers.home-assistant.io/docs/api/rest/)).

---

## Operator (one path)

**Prerequisites:** Python 3.11+ in the victron clone. HA reachable on the LAN. Token file
on disk (gitignored) — create per alfa-ai
[HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md)
(HA UI → Profile → Long-lived access token).

**Step 1 — From the host running the dashboard** (e.g. `.93` dev box or `.105`):

```bash
cd /path/to/victron-ble2mqtt-integration
export HA_BASE_URL=http://192.168.0.105:8123
export HA_TOKEN_FILE=/path/to/long-lived.token
python scripts/solar_flow_server.py
```

**Step 2 —** Open in a local browser:

```text
http://127.0.0.1:8765/
```

Default bind is **localhost only** (`127.0.0.1:8765`). Do not expose the server to the public
internet without an explicit operator change.

The browser polls `GET /api/snapshot` every **2 s** with `cache: 'no-store'`. The proxy
sends `Cache-Control: no-store` ([RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html#name-cache-control);
[http.server](https://docs.python.org/3/library/http.server.html)). Header **HA HH:MM:SS**
is snapshot `fetched_at`. Watts / SoC / switch state come from HA
[`last_updated`](https://www.home-assistant.io/docs/configuration/state_object/) on each
entity. Demo mode still refreshes `fetched_at` every poll; numeric values stay static until
a token is present.

---

### Environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `HA_BASE_URL` | `http://192.168.0.105:8123` | HA Container base URL (no trailing slash) |
| `HA_TOKEN_FILE` | — | Path to one-line long-lived token (preferred) |
| `HA_LONG_LIVED_TOKEN_FILE` | — | Alias for `HA_TOKEN_FILE` if the first is unset |
| `SOLAR_FLOW_HOST` | `127.0.0.1` | Listen address (`--host`; `--lan` binds `0.0.0.0`) |
| `SOLAR_FLOW_PORT` | `8765` | Listen port |

**Demo mode:** If no token file exists or `HA_TOKEN_FILE` is unreadable, the server serves
**static demo values**, sets `mode: demo`, and the page shows a **DEMO** badge plus the
snapshot `label` (illustrative, not live). Soak math still runs on demo numbers for UI
testing; no HA calls are made. The browser polls `GET /api/snapshot` every **2 s**.

**Secrets:** Never commit the token. Never pass the token as a query string or embed it in
HTML/JS. Keep the file mode `600` on shared hosts.

---

## Layout and site physics

Follows Victron GX Overview
([Cerbo GX UI](https://www.victronenergy.com/media/pg/Cerbo_GX/en/the-new-user-interface.html)):
energy sources on the **left**, batteries in the **centre**, consumers on the **right**.
Sungold is a **second plant** drawn as a dashed island under the two trailer buses -- not a
third 24 V bus and not a DC hub.

Plant detail is from [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md). Live `entity_id`s
below are from HA `.storage/core.entity_registry` on `.105` (16 Sep 2026). Soak canonicals
(`*_solar_power`, `*_battery_state`, `*_soc`) still work: the proxy aliases Lovelace ids
onto them ([HA REST `GET /api/states`](https://developers.home-assistant.io/docs/api/rest/)).

Charge window for Victron strings: **09:30-16:00 ET**.

### Sources (left)

| Node | Live HA / display | Notes |
|------|-------------------|-------|
| **T2 MPPT** (charger 1) | `sensor.solar_controller_solar` (alias of soak `..._solar_power`); `charge_state`; `battery`; `battery_charging`; `charging_power`; `load`; `load_power`; `yield_today`; `rssi` | Only **reporter** in MQTT. Animate PV flow when solar W is numeric and > 0. BlueSolar fields: [monitoring](https://www.victronenergy.com/media/pg/Manual_BlueSolar_MPPT_75-10_up_to_100-20/en/monitoring.html). |
| **KU Victron** (chargers 2+3) | **No entity.** Grey tile, `--` W, dashed wire, **never** animated | Silent until Instant Readout keys ([DEVICES.md](DEVICES.md)). Do **not** display 2x T2 watts as live. |
| **KU Renogy PWM** | **No entity** (Voyager 20A). Grey tile, `--` W, dashed wire, never animated | Unmetered into KU shunt. Shown because the operator asked for the datapoint; still not in HA. |

### Storage (centre)

| Node | Live HA entities | Notes |
|------|------------------|-------|
| **LiTime T2** | `sensor.battery_1_state_of_charge` (alias of `battery_1_soc`), `voltage`, `current`, `power`, `consumed_ah`, `remaining_minutes`, `rssi`, `auxiliary_mode`, `midpoint_voltage`, `midpoint_shift`, `midpoint_shift_2` | SmartShunt `HQ2239CQYT2` |
| **LiTime KU** | `sensor.battery_2_state_of_charge` (alias of `battery_2_soc`), `voltage`, `current`, `power`, `consumed_ah`, `remaining_minutes`, `rssi`, `auxiliary_mode` | Net of KU chargers + PWM minus KU Renogy |
| **T2-KU jumper** | Not a numbered bus (dim label only) | Amp-less workaround; see jumper table in SOLAR_POWER_BALANCE |

**Primary numbers (16 Sep 2026):** shunt **V** and signed **A** (and **W**, or V x A if the
power sensor is missing). Charge **+** / discharge **-** per SmartShunt
[operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html).
**SoC % is shown but not used for control or animation** -- the shunts are unsynced
(site history: KU **SoC 0%** at ~27-29 V). Victron displays SoC as `---` when
unsynchronised; this page labels the HA % **SoC unsynced**. Do **not** invent a
software SoC from voltage. LiTime absorb **28.4-29.2 V** is nameplate, not an 85%
substitute. Pips and wires follow numeric V/A/W and switch ON only.

### Loads (right) and Renogy inverters

| Node | Live HA / display | Notes |
|------|-------------------|-------|
| **T2 Renogy 2 kW** | **No inverter entity.** Grey `--` W. EM16 A2/B4 are **candidate** idle watts on the meter bank, not confirmed inverter W | 30A RV outlet. Idle if no RV. Do not treat A2 as a second site load. |
| **KU Renogy 2 kW** | No inverter entity. AC path continues to the riser. Watts come from EM16 A3 when that clamp is on trailer AC | Trailer + optional RV via ATS. |
| **EM16 A3** | `sensor.em16_a3_power` (+ `voltage`, `current`, `power_factor`, `this_month_energy`, `this_month_energy_returned`) | **10-11 Sep:** KU trailer/cluster. **15 Sep:** A3/B2 = Sungold AC-in. Static caveat on the tile. Refoss naming: [EM16 integration](https://www.home-assistant.io/integrations/refoss/). |
| **Sim A/C plugs 1-6** | `switch.sim_ac_plug_*`, `sensor.sim_ac_plug_*_power`, `sensor.sim_soak_load_power` | [SIM_SOAK_PLUGS.md](SIM_SOAK_PLUGS.md). Fan spins when ON. Do **not** show `input_boolean.sim_ac_plug_*_internal` as extra tiles. |
| **Other EM16 channels** | `sensor.em16_{a1-c6}_{power,voltage,current,...}` | Meter bank only. **Never add A3+B2.** B2 labeled return of A3. C1-C6 unused CTs (~0 W). |

### Sungold cart (separate island)

SPH302480A LCD names: [SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md),
[reprint §4.1](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf).
Live MQTT `entity_id`s (unique_id in parentheses):

| Tile | Live `entity_id` | unique_id |
|------|------------------|-----------|
| PV V / A / W | `sensor.sungold_sph302480a_pv_voltage` / `_pv_current` / `_pv_power` | `...-pv1-voltage` / `-pv1-current` / `-pv1-power` |
| Remaining battery | `sensor.sungold_sph302480a_battery_soc` | `...-battery-soc` |
| INPUT BATT V / A / KW | `..._battery_voltage` / `_battery_current` / `_charging_power` | `...-battery-voltage` / `-battery-current` / `-inverter-charging_power` |
| Charge state | `sensor.sungold_sph302480a_charge_state` | `...-battery-charge_state` |
| AC INPUT V / A / Hz | `..._grid_voltage` / `_grid_current` / `_grid_frequency` | `...-grid-*` (LCD: mains / AC input, not "grid power") |
| INV OUTPUT LOAD | `..._load_power` / `_load_current` | `...-load-power` / `-load-current` |
| OUTPUT LOAD V / AC OUTPUT Hz | `..._ac_output_voltage` / `_ac_output_frequency` | `...-inverter-voltage` / `-inverter-frequency` |
| Output mode / fault | `..._inverter_state`, `..._fail_code`, `binary_sensor.sungold_sph302480a_fault_active` | |

Older Lovelace `sensor.sungold_sph302480a_load_active_power` aliases onto `_load_power` if present.

If those entities are missing (sidecar off), tiles stay grey `--` and live snapshot lists them in `missing_entity_ids`. **No** Renogy PWM / inverter ids are invented.

### SVG conductors (snap to node edges)

Plant is **two 24 V buses** plus a Sungold island, not one DC hub.

```
T2:  BlueSolar MPPT  --wire-->  Battery 1 (HQ2239CQYT2)
                     --wire-->  T2 Renogy (grey, unmetered, RV idle)
KU:  chargers 2-3 (dashed, unmetered, `--` W, never animated)
     PWM (dashed, unmetered, `--` W, never animated)
        --wire-->  Battery 2 (HQ2239JTRKU)
        --wire-->  KU Renogy (trailer AC)
        --wire-->  vertical AC bus
                    |-- EM16 A3
                    |-- sim plugs 1-6 (one tap each)
Sungold island (not on T2/KU DC):
     PV --wire--> cart battery --wire--> SPH inverter --wire--> AC out
     AC in --wire--> SPH inverter
```

| Path id | Connects |
|---------|----------|
| `path-t2-mppt-batt1` | MPPT right edge to Battery 1 left edge |
| `path-t2-batt1-renogy` | Battery 1 right to T2 Renogy (idle, not animated unless a confirmed inverter W exists) |
| `path-ku-chargers-batt2` | KU chargers 2-3 (dashed) to Battery 2 |
| `path-ku-pwm-batt2` | KU PWM (dashed) to Battery 2 |
| `path-ku-batt2-inverter` | Battery 2 right to KU Renogy left |
| `path-inverter-acbus` | KU Renogy right to AC riser |
| `path-ac-riser` | Vertical AC bus |
| `path-ac-em16` | Riser to EM16 A3 |
| `path-ac-plug-1` … `path-ac-plug-6` | Riser to each sim plug |
| `path-sg-pv-batt` | Sungold PV to cart battery |
| `path-sg-batt-inv` | Cart battery to SPH inverter |
| `path-sg-acin-inv` | Sungold AC in to SPH inverter |
| `path-sg-inv-acout` | SPH inverter to AC out |

Idle conductors stay visible (grey stroke). Animated cyan only when that hop has numeric W
or an ON switch. KU 2-3 and PWM stay dashed and never flow. T2 Renogy stays idle unless HA
later grows a Renogy entity. Sungold island wires animate from SPH MQTT watts only.

---

## Visual rules

| Signal | Meaning |
|--------|---------|
| **Green LED / cyan flow line** | Switch ON, or **numeric** W/A flow on that hop |
| **Grey LED / grey conductor** | Switch OFF, `unavailable` / `unknown`, or idle connected wire |
| **Dashed KU 2-3 / PWM conductors** | Physical KU Victron pair and Voyager PWM exist; **no** live W. Never animated. Do **not** print 2x T2 watts. |
| **Spinning fan** (plugs 1, 4, 5) | `switch.sim_ac_plug_*` state `on` |
| **`prefers-reduced-motion: reduce`** | Disable line animation and fan spin; keep numeric updates |

GX manuals do **not** publish Overview hex colors; dark charcoal + cyan is operator choice, not a Victron palette. Do **not** copy Victron logos, GX/VRM screenshots, or product bitmaps ([press assets](https://www.victronenergy.com/information/press) are for press, not this UI). Structure only: three columns, dark default, tappable-looking tiles. Title is **Solar flow**, not Cerbo / VRM / Remote Console.

Every node tile shows live numbers where HA provides them. Missing sensors show `--` and grey
state.

---

## AI panel (deterministic soak explainer)

Read-only mirror of alfa-ai `decide_soak()` — same defaults as
[HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md).
**No LLM.** No `POST` to HA switch services from this page.

### Inputs (default entity ids)

| Setting key | Default entity | Role |
|-------------|----------------|------|
| `ha_solar_entity` | `sensor.solar_controller_solar_power` | T2 PV W. Live Lovelace is `sensor.solar_controller_solar` -- proxy copies that onto the canonical id. |
| `ha_load_entity` | `sensor.em16_a3_power` | AC load W (see A3 caveat above) |
| `ha_soc_entity` | `sensor.battery_1_soc` | Display only while unsynced. Live MQTT is `sensor.battery_1_state_of_charge`. |
| `ha_shunt_voltage_entity` | `sensor.battery_1_voltage` | Thinking text (LiTime 28.4-29.2 V nameplate). Not a SoC substitute. |
| `ha_shunt_current_entity` | `sensor.battery_1_current` | Thinking text; +charge / -discharge. |
| `ha_soc_unsynced` | `true` | Skip the 85% SoC gate. Victron publishes **no** voltage-to-% map. |
| `ha_charge_state_entity` | `sensor.solar_controller_battery_state` | Must be in `float` or `absorption` to arm soak-on. Live Lovelace is `sensor.solar_controller_charge_state`. |
| `ha_switch_allowlist` | six `switch.sim_ac_plug_*` | Plugs eligible for decisions |
| `ha_switch_watts` | rated W per plug | Added to effective load when ON |

### Surplus math

```
effective_load_w = (load_sensor_W or 0) + sum(rated_W for each ON plug in ha_switch_watts)
surplus_w = solar_W - effective_load_w
```

### Gates (thinking text)

The panel lists why soak is armed or skipped:

1. `ha_solar_soak_enabled` — policy on/off
2. Solar sensor numeric — else skip
3. **SoC gate skipped** while `ha_soc_unsynced=true` (default). Official SmartShunt
   [operation 5.7](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)
   is silent on a numeric substitute for 85% SoC; thinking text is
   `SoC gate skipped: unsynced; using V/A + charge state only`. Set
   `ha_soc_unsynced=false` after VictronConnect synchronise to restore
   `ha_min_soc_percent` (85).
4. Charge state in **`float` or `absorption`** (`ha_charge_states_ok`) — else skip
5. **Surplus > 200 W** (`ha_min_surplus_watts`) → target **on**; **<= 50 W** (`ha_off_surplus_watts`) → target **off**; between → hysteresis hold
6. **Min on 600 s / min off 300 s** — dwell timers
7. **Max concurrent on 6** — cap simultaneous sim plugs

Shunt V/A appear in thinking only (LiTime 28.4-29.2 V nameplate;
+charge / -discharge). They are **not** a new skip threshold.

### Operator: synchronise SmartShunt SoC (VictronConnect only)

Victron: unsynchronised SoC / consumed Ah / time remaining show `---`. A
synchronisation **resets SoC to 100%** when the battery is **actually full**
([operation 5.7](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)).

1. Confirm pack capacity **230 Ah** in VictronConnect battery settings
   ([installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html)
   configuration; site LiTime 24 V 230 Ah).
2. Charge until the MPPT is in **absorption** then **float** and the LiTime is in
   its **28.4-29.2 V** charge window.
3. **Automatic:** charged voltage + tail current + charged detection time all
   met (Victron 12 V example: 13.2 V, tail 4% of capacity, 3 minutes -- scale
   charged voltage for 24 V in VictronConnect; do not invent a homebrew %).
4. **Manual if auto did not fire:** VictronConnect → Settings → Battery
   settings → **Synchronise**. Only when the battery is full.
5. This repo **does not** reset SoC over MQTT or Home Assistant.

After a real sync, set `ha_soc_unsynced=false` so the 85% SoC gate returns.

### Output display

| UI section | Content |
|------------|---------|
| **Thinking** | Human-readable lines: solar W, load W, sim plug W, surplus, SoC, charge stage, skip reason |
| **Planned** | Per-allowlist plug: `on`, `off`, or `skip` with reason |
| **Actuation** | Panel note **read-only — alfa-ai actuates**. This page never `POST`s switch services. |

Confirm entity ids with `GET /api/states` or Ask ALFa `ha_get_states` on host `105` after token
setup. Lovelace Solar tiles use `sensor.solar_controller_solar` (see
`tests/test_ha_label_victron_refoss.py`); soak defaults keep `_solar_power`. The proxy aliases
both. Battery SoC is `sensor.battery_*_state_of_charge` (MQTT name "State of charge").
Sungold tiles use the live MQTT ids in the table above (`tests/test_ha_label_sungold_solar.py`).

---

## Security and scope

| Rule | Why |
|------|-----|
| Token in file only | HA [REST API](https://developers.home-assistant.io/docs/api/rest/) Bearer auth |
| No Lovelace scrape | Frontend is not a machine API (alfa-ai policy) |
| Localhost bind default | Dashboard is operator LAN tooling, not a public surface |
| Read-only loads | Soak **actuation** stays on alfa-ai `.111` with audit (`solar_soak_actuated`) |
| Victron BLE / Sungold publishers unchanged | Sensor-only; no MQTT publish back to hardware |

---

## Related

- [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md) — buses, EM16 A3 history, formulas
- [SIM_SOAK_PLUGS.md](SIM_SOAK_PLUGS.md) — six sim switches on `.105`
- [ALFA_AI_HOW_TO_USE.md](ALFA_AI_HOW_TO_USE.md) — brain ↔ HA pointer
- [ALFA_CLUSTER_INTEGRATION.md](ALFA_CLUSTER_INTEGRATION.md) — hub / multi-repo layout
- alfa-ai [HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md) — soak settings and token
