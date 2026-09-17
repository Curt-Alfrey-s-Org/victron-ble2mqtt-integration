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
| **Right — loads** | KU Renogy AC path (**-- W**, no HA inverter), EM16 A3 (**Sungold AC-in clamp**), six sim A/C plugs. T2 Renogy 30A RV is a **grey unmetered** dead-end (idle if no RV). |
| **Sungold cart (AC from KU outlet)** | SPH302480A + 2x 100 Ah. **DC stays off T2/KU.** Operator (16 Sep): **AC input is plugged into a KU Renogy trailer outlet.** Draw that AC hop on the Overview (not a disconnected island). Live MQTT when the sidecar is up. |
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
entity. Demo mode still refreshes `fetched_at` every poll but the header shows **DEMO not HA**,
not `HA HH:MM:SS`. Numeric values stay static until a token is present.

---

### Environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `HA_BASE_URL` | `http://192.168.0.105:8123` | HA Container base URL (no trailing slash) |
| `HA_TOKEN_FILE` | — | Path to one-line long-lived token (preferred) |
| `HA_LONG_LIVED_TOKEN_FILE` | — | Alias for `HA_TOKEN_FILE` if the first is unset |
| (default files, if env unset) | — | `../alfa-ai/deploy/secrets/home-assistant/long-lived.token` then `deploy/secrets/home-assistant/long-lived.token` in this clone |
| `SOLAR_FLOW_HOST` | `127.0.0.1` | Listen address (`--host`; `--lan` binds `0.0.0.0`) |
| `SOLAR_FLOW_PORT` | `8765` | Listen port |

**Demo mode:** If no token file exists or `HA_TOKEN_FILE` is unreadable, the server serves
**static demo values**, sets `mode: demo`, and the page must be **unmistakable**: red
**DEMO not live** badge, full-width amber banner, large watermark, `DEMO` prefix on every
tile number, header clock **DEMO not HA** (not `HA HH:MM:SS`), and **no** wire/fan
animation. The watermark is `display: none` unless `body.demo-mode` (live snapshots must
not show it). Author `display: flex` on `.demo-watermark` otherwise overrides HTML
`hidden` ([hidden attribute](https://html.spec.whatwg.org/multipage/interaction.html#the-hidden-attribute)).
Soak math still runs on those demo numbers for UI testing; no HA calls are
made. Demo watts are **not** a live observation -- do not treat 400 W / 10 W Sungold
load as the plant. The browser polls `GET /api/snapshot` every **2 s**.

**Go live (one path, no paste):** keep the long-lived token as gitignored
`alfa-ai/deploy/secrets/home-assistant/long-lived.token` (never in git, chat, or
`host105-ai.env`). **`.93`:** that file is already next to this clone
(`C:\Users\gamerx\alfa-ai\deploy\secrets\home-assistant\long-lived.token`); solar-flow
reads it as the first default path. **`.111`:** same relative path for the brain API
mount. **`.105`:** same relative path under `/home/ansible/alfa-ai/` when solar-flow
runs there (copy from `.93`; HA Container does not need the file).
`~/.config/host105-ai.env` has no HA token keys.
Optional second path: `victron-ble2mqtt-integration/deploy/secrets/home-assistant/long-lived.token`.
Then start `python scripts/solar_flow_server.py`. Never paste the token. Never commit it.
The proxy also reads those default paths when `HA_TOKEN_FILE` is unset
([pathlib `Path.read_text`](https://docs.python.org/3/library/pathlib.html#pathlib.Path.read_text)).
`GET /api/snapshot` `mode` becomes `live` only after a successful
[HA REST `GET /api/states`](https://developers.home-assistant.io/docs/api/rest/).

**Secrets:** Never commit the token. Never pass the token as a query string or embed it in
HTML/JS. This clone gitignores `deploy/secrets/home-assistant/*` (keep `.gitkeep` only).
Keep the file mode `600` on shared hosts.

---

## Layout and site physics

Follows Victron GX Overview
([Cerbo GX UI](https://www.victronenergy.com/media/pg/Cerbo_GX/en/the-new-user-interface.html)):
energy sources on the **left** (including **suitcase panel** tiles), batteries in the
**centre**, consumers on the **right**. Sungold **DC** stays off T2/KU. Sungold **AC in**
is a KU Renogy **trailer outlet** hop (operator 16 Sep; 15 Sep EM16 A3 matched Sungold
`AC INPUT` in [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md)). Click a node for HA
recorder history via proxy `GET /api/history` (never call HA from the browser).

Plant detail is from [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md). Live `entity_id`s
below are from HA `.storage/core.entity_registry` on `.105` (16 Sep 2026). **Lovelace /
MQTT live ids win** when both a soak canonical and a live row exist (example: Sungold
`sensor.sungold_sph302480a_load_active_power` over a stale `_load_power`). Soak
canonicals (`*_solar_power`, `*_battery_state`, `*_soc`) still work: the proxy copies
the live row onto the canonical when the live id is present
([HA REST `GET /api/states`](https://developers.home-assistant.io/docs/api/rest/)).

Charge window for Victron strings: **09:30-16:00 ET**.

### Sources (left)

| Node | Live HA / display | Notes |
|------|-------------------|-------|
| **T2 suitcase (2 in series)** | No per-panel entity. Tile shows T2 MPPT **solar W** as the only live PV for that pair | Victron charger 1. Unmetered at the panel; meter is the MPPT. |
| **KU Victron suitcases (2+2)** | **No entity.** Grey `--` W | Chargers 2 and 3. Do not print 2x T2 as live. |
| **KU PWM suitcases (2)** | **No entity.** Grey `--` W | Voyager PWM. |
| **T2 MPPT** (charger 1) | Live: `sensor.solar_controller_solar` (W), `sensor.solar_controller_charge_state`; also `battery`, `battery_charging`, `charging_power`, `load`, `load_power`, `yield_today`, `rssi`. Soak canonical `..._solar_power` / `..._battery_state` is filled from these. | Only **reporter** in MQTT. Animate PV flow when **live** solar W is numeric and > 0 (not in demo). BlueSolar fields: [monitoring](https://www.victronenergy.com/media/pg/Manual_BlueSolar_MPPT_75-10_up_to_100-20/en/monitoring.html). |
| **KU Victron** (chargers 2+3) | **No entity.** Grey tile, `--` W, dashed wire, **never** animated | Silent until Instant Readout keys ([DEVICES.md](DEVICES.md)). Do **not** display 2x T2 watts as live. |
| **KU Renogy PWM** | **No entity** (Voyager 20A). Grey tile, `--` W, dashed wire, never animated | Unmetered into KU shunt. |

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
| **KU Renogy 2 kW** | **No inverter entity.** Tile stays **-- W** (unmetered). Do **not** paint EM16 A3 onto this node. | Trailer + optional RV via ATS. **Operator 16 Sep:** Sungold cart **AC INPUT** cord is in a **KU Renogy outlet**. |
| **Trailer outlet (to Sungold)** | **Unmetered** on the KU Renogy tile. Sungold AC-in hop watts: `path-ku-outlet-sg-acin` only (see below). | Not a third DC bus. Physical outlet hop; no invented KU trailer meter. |
| **EM16 A3** | `sensor.em16_a3_power` (+ `voltage`, `current`, `power_factor`, `this_month_energy`, `this_month_energy_returned`) | **Sungold AC-in clamp** (operator 16 Sep). B2 is return -- never sum. Refoss naming: [EM16 integration](https://www.home-assistant.io/integrations/refoss/). |
| **Sim A/C plugs 1-6** | `switch.sim_ac_plug_*`, `sensor.sim_ac_plug_*_power`, `sensor.sim_soak_load_power` | [SIM_SOAK_PLUGS.md](SIM_SOAK_PLUGS.md). Fan spins when ON. Do **not** show `input_boolean.sim_ac_plug_*_internal` as extra tiles. |
| **Other EM16 channels** | `sensor.em16_{a1-c6}_{power,voltage,current,...}` | Meter bank only. **Never add A3+B2.** B2 labeled return of A3. C1-C6 unused CTs (~0 W). |

### Sungold cart (AC from KU Renogy outlet; DC separate)

SPH302480A LCD names: [SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md),
[reprint §4.1](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf).
**DC** of the cart (2x 100 Ah) is **not** paralleled onto T2/KU. **AC INPUT** is
mains-side on the hybrid ([reprint §4.1](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf))
and on this site is the **KU Renogy outlet**, not a utility meter.

Put Sungold **on the same Overview as the trailer AC path** (outlet wire from KU Renogy
to Sungold AC-in). Do not hide it below the fold as an unrelated island. **Layout (16 Sep,
geometry pass):** Sungold AC-in and the **trailer outlet** are separate tiles **left of the
AC riser** (x&lt;560). Trailer is painted **after** AC-in in the SVG so its fill covers any
overlap; Hz and EM16 sublabel must still sit **outside both fills**.

| Element | Bounding box (x, y, w, h) | Notes |
|---------|---------------------------|-------|
| `node-sg-acin` rect fill | 400, 404, 120, 42 → **400–520 × 404–446** | Label/W/V·A inside fill |
| `node-sg-acin` Hz + sublabel | center x=460, y=458 / y=470 | Below fill, above trailer |
| `node-trailer-outlet` | 522, 512, 72, 36 → **522–594 × 512–548** | Down/right of AC-in labels |
| `node-plug-6` | 700, 435, 170, 44 → **700–870 × 435–479** | Unchanged; on riser branch |

Plugs stay x=700+; `path-ac-riser` (x=560, y=115–479) and `path-ac-plug-6` (y=457) stay
clear of the AC-in tile. Do **not** restore the disconnected y=680 island.

**Conductors (snap to node edges):**

| Path id | `d` (SVG) | Hop label |
|---------|-----------|-----------|
| `path-ku-outlet-sg-acin` | `M 530 360 L 530 512 L 558 512 L 558 530 L 460 446` | `hop-path-ku-outlet-sg-acin` at (538, 475) — right of AC-in fill |
| `path-sg-acin-inv` | `M 460 446 L 460 550 L 492 550 L 492 568` | `hop-path-sg-acin-inv` at (452, 508) — left of trailer fill |

`path-ku-outlet-sg-acin` runs KU Renogy right edge (530, 360) down past AC-in, into trailer
outlet, then into AC-in bottom (460, 446). No vertical segment through the AC-in rect.
`path-sg-acin-inv` drops below the trailer tile before routing to SPH.
Live MQTT `entity_id`s (unique_id in parentheses):

| Tile | Live `entity_id` | unique_id |
|------|------------------|-----------|
| PV V / A / W | `sensor.sungold_sph302480a_pv_voltage` / `_pv_current` / `_pv_power` | `...-pv1-voltage` / `-pv1-current` / `-pv1-power` |
| Remaining battery | `sensor.sungold_sph302480a_battery_soc` | `...-battery-soc` |
| INPUT BATT V / A / KW | `..._battery_voltage` / `_battery_current` / `_charging_power` | `...-battery-voltage` / `-battery-current` / `-inverter-charging_power` |
| Charge state | `sensor.sungold_sph302480a_charge_state` | `...-battery-charge_state` |
| AC INPUT V / A / Hz | `..._grid_voltage` / `_grid_current` / `_grid_frequency` | `...-grid-*` (LCD: mains / AC input, not "grid power") |
| INV OUTPUT LOAD | `sensor.sungold_sph302480a_load_active_power` (fallback `_load_power`) / `_load_current` | `...-load-power` / `-load-current`. Lovelace tile is **Load active power**; live id wins if both exist. |
| OUTPUT LOAD V / AC OUTPUT Hz | `..._ac_output_voltage` / `_ac_output_frequency` | `...-inverter-voltage` / `-inverter-frequency` |
| Output mode / fault | `..._inverter_state`, `..._fail_code`, `binary_sensor.sungold_sph302480a_fault_active` | |

`sensor.sungold_sph302480a_load_active_power` is the **live** Lovelace tile. The proxy
copies it onto `_load_power` for soak math. If both exist, **active power wins**.

If those entities are missing (sidecar off), tiles stay grey `--` and live snapshot lists them in `missing_entity_ids`. **No** Renogy PWM / inverter ids are invented.

Lovelace Solar tiles to GX fields (live REST ids):

| Lovelace tile | Diagram field | Live `entity_id` |
|---------------|---------------|------------------|
| BlueSolar solar W / charge / batt V/A / load / yield / RSSI | MPPT node | `sensor.solar_controller_solar`, `_charge_state`, `_battery`, `_battery_charging`, `_load`, `_yield_today`, `_rssi` |
| SmartShunt T2 V/A/W / SoC / Ah / rem / RSSI | Battery 1 | `sensor.battery_1_voltage`, `_current`, `_power`, `_state_of_charge`, `_consumed_ah`, `_remaining_minutes`, `_rssi` |
| SmartShunt KU (same) | Battery 2 | `sensor.battery_2_*` |
| Sungold PV V/A/W | Sungold PV | `sensor.sungold_sph302480a_pv_*` |
| Remaining battery | Cart remain % | `..._battery_soc` |
| INPUT BATT V/A + charge state | Cart battery | `..._battery_voltage`, `_battery_current`, `_charging_power`, `_charge_state` |
| Load active power + AC out V/A/Hz | Sungold AC out | `..._load_active_power`, `_ac_output_voltage`, `_load_current`, `_ac_output_frequency` |
| AC INPUT V/A/Hz (+ W hop) | Sungold AC in | Tile V/A/Hz: `..._grid_*`. Click history + hop W: `sensor.em16_a3_power` (allowlisted); fallback display W is grid V x A when A3 is missing. |
| Output mode / fault | SPH tile | `..._inverter_state`, `_fail_code`, `binary_sensor.sungold_sph302480a_fault_active` |
| Refoss A1-C6 | Meter bank | `sensor.em16_*` |

### SVG conductors (snap to node edges)

End-to-end watt path (operator 16 Sep):

```
T2 suitcases (2) --> BlueSolar MPPT --W--> Battery 1 -- --> T2 Renogy RV (idle)
KU suitcases (2+2, unmetered) --> chargers 2-3 --dashed--> Battery 2
KU PWM suitcases (2, unmetered) --> Voyager --dashed--> Battery 2
Battery 2 --> KU Renogy 2 kW --> trailer AC bus
   |-- EM16 A3 (15 Sep: this clamp = Sungold AC-in)
   |-- sim plugs 1-6
   |-- trailer outlet --AC W--> Sungold AC INPUT --> SPH302480A
                              |-- cart 2x 100 Ah (DC, not T2/KU)
                              |-- Sungold PV panels --> SPH
                              |-- Sungold AC OUTPUT (cart loads)
```

Hop watt labels sit on each conductor (live numeric W, or `--` if unmetered).

**Trailer AC bus hops** (`path-inverter-acbus`, `path-ac-riser`): sum of **sim soak plug** watts when any plug reports W; otherwise `--` (unmetered). **Do not** drive these from EM16 A3.

**Sungold AC-in hop** (`path-ku-outlet-sg-acin`, `path-sg-acin-inv`): `|sensor.em16_a3_power|` when present, else Sungold `grid_voltage * grid_current`.

| Path id | Connects | Hop watts |
|---------|----------|-----------|
| `path-t2-panels-mppt` | T2 suitcase pair to BlueSolar | T2 MPPT solar W |
| `path-t2-mppt-batt1` | MPPT to Battery 1 | `sensor.solar_controller_charging_power` when present; else `battery_charging` x `battery` V; else solar W (unmetered split vs panels hop) |
| `path-t2-batt1-renogy` | Battery 1 to T2 Renogy (idle) | unmetered |
| `path-ku-panels-chargers` | KU Victron suitcase groups to chargers 2-3 (dashed) | unmetered |
| `path-ku-chargers-batt2` | Chargers 2-3 to Battery 2 (dashed) | unmetered |
| `path-ku-pwm-panels` | PWM suitcases to Voyager (dashed) | unmetered |
| `path-ku-pwm-batt2` | PWM to Battery 2 (dashed) | unmetered |
| `path-ku-batt2-inverter` | Battery 2 to KU Renogy | \|Battery 2 W\| when discharging |
| `path-inverter-acbus` | KU Renogy to AC riser | sim plug sum or `--` |
| `path-ac-riser` | Vertical AC bus | sim plug sum or `--` |
| `path-ac-em16` | Riser branch to **EM16 A3 clamp tile** (Sungold AC-in meter tap) | \|A3 power\| — same clamp as `path-ku-outlet-sg-acin`; **not** a second plant load and **not** added to soak AC-bus totals |
| `path-ac-plug-1` … `path-ac-plug-6` | Riser to each sim plug | per-plug W |
| `path-ku-outlet-sg-acin` | **KU Renogy / trailer outlet to Sungold AC-in** | A3 or grid V x A |
| `path-sg-pv-panels` | Sungold PV panels to SPH / cart PV tile |
| `path-sg-pv-batt` | Sungold PV to cart battery |
| `path-sg-batt-inv` | Cart battery to SPH |
| `path-sg-acin-inv` | Sungold AC in to SPH |
| `path-sg-inv-acout` | SPH to AC out |

---

## Click history (HA recorder)

Token stays on the proxy. Browser calls **only**
`GET /api/history?entity_id=<id>&hours=24` on localhost (the UI may request `hours=24`).
The proxy **clamps** the window to **10 hours** (`HISTORY_HOURS_MAX` in
`solar_flow_server.py`); that cap is a proxy policy, not HA `recorder.purge_keep_days`.
The JSON response includes the clamped `hours` value actually fetched.

The proxy allowlists plant entity ids and calls HA

`GET /api/history/period/<start>?filter_entity_id=<id>&end_time=<end>&minimal_response&no_attributes`

per the [REST API](https://developers.home-assistant.io/docs/api/rest/) (`filter_entity_id`
required; `end_time`, `minimal_response`, and `no_attributes` optional). Timestamps in the
path and `end_time` use URL-encoded ISO-8601 (`:` as `%3A`, `+` as `%2B`) as in the official
curl sample. Click a node (cursor pointer) to fill the History aside: entity id, up to **10 h**
of states as a simple polyline plus a short table (`last_changed`, `state`). Sungold AC-in
click history prefers `sensor.em16_a3_power` (power-ish, allowlisted) over `grid_voltage` alone.
Unknown ids return 400. Demo mode: history stays **unavailable** (no fake series).

### Recorder required on `.105`

History depends on the [Recorder](https://www.home-assistant.io/integrations/recorder/)
integration ([History](https://www.home-assistant.io/integrations/history/) reads the same
database). Both are enabled by default unless `default_config:` was removed from
`/opt/homeassistant/configuration.yaml` on `.105` without adding explicit blocks.

**Symptom:** proxy log `history endpoint 404` and the aside shows
`HA recorder or history integration is not enabled` (live diagnosis Sep 2026: `.105` had
neither `recorder` nor `history` in `GET /api/config` `components`).

**Enable on `.105`** (edit `/opt/homeassistant/configuration.yaml`, then restart the HA
container per [common tasks](https://www.home-assistant.io/common-tasks/container/)):

```yaml
recorder:
history:
```

If `default_config:` is present, recorder and history should already load; a 404 then means
the integration failed to start (check HA logs). After enable, wait for state changes to be
recorded; an empty `points` array is valid when the entity has no rows in the retention
window (default 10 days per History integration docs).

### significant_changes_only

The [REST history parameters](https://developers.home-assistant.io/docs/api/rest/) list
`significant_changes_only` as an optional query flag but do not document a disable value or
a core default on that page. The proxy does **not** send that flag.

### Other failures

If recorder is on but HA returns another HTTP error, the aside shows a generic
`history fetch failed` (no token text).

---

## Visual rules

| Signal | Meaning |
|--------|---------|
| **Green LED / cyan flow line** | Switch ON, or **numeric** W/A flow on that hop |
| **Grey LED / grey conductor** | Switch OFF, `unavailable` / `unknown`, or idle connected wire |
| **Dashed KU 2-3 / PWM conductors** | Physical KU Victron pair and Voyager PWM exist; **no** live W. Never animated. Do **not** print 2x T2 watts. |
| **Spinning fan** (plugs 1, 4, 5) | `switch.sim_ac_plug_*` state `on` |
| **`prefers-reduced-motion: reduce`** | Disable line animation and fan spin; keep numeric updates |
| **Demo mode** | Red **DEMO not live** badge, amber banner, watermark **only** when `body.demo-mode`. Live: green **live** badge, no watermark. |

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
| `ha_load_entity` | `sensor.sim_soak_load_power` | Plant AC load W for surplus math (sim-plug aggregate; `0` when all OFF). **16 Sep topology:** EM16 A3 is Sungold SPH AC-in on the KU Renogy trailer outlet, **not** KU trailer house load -- do **not** point soak at `sensor.em16_a3_power` while A3 is Sungold AC-in. When a real KU house clamp exists, set `ha_load_entity` to that sensor; see [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md). |
| `ha_soc_entity` | `sensor.battery_1_soc` | Display only while unsynced. Live MQTT is `sensor.battery_1_state_of_charge`. |
| `ha_shunt_voltage_entity` | `sensor.battery_1_voltage` | Thinking text (LiTime 28.4-29.2 V nameplate). Not a SoC substitute. |
| `ha_shunt_current_entity` | `sensor.battery_1_current` | Thinking text; +charge / -discharge. |
| `ha_soc_unsynced` | `true` | Skip the 85% SoC gate. Victron publishes **no** voltage-to-% map. |
| `ha_charge_state_entity` | `sensor.solar_controller_battery_state` | Must be in `float` or `absorption` to arm soak-on. Live Lovelace is `sensor.solar_controller_charge_state`. |
| `ha_switch_allowlist` | six `switch.sim_ac_plug_*` | Plugs eligible for decisions |
| `ha_switch_watts` | rated W per plug | Rated W per ON switch (fallback when load sensor unavailable; **not** added when `ha_load_entity` is `sensor.sim_soak_load_power`) |

### Surplus math

```
surplus_w = solar_W - effective_load_w
```

- **Default (`ha_load_entity` = `sensor.sim_soak_load_power`):** `effective_load_w` is the
  aggregate sensor only (no double-count with `ha_switch_watts`). If the sensor is
  `unavailable`, fall back to the sum of rated W for ON plugs in `ha_switch_watts`.
- **Real plant clamp configured:** when `ha_load_entity` is a house/trailer EM16 sensor
  (not `sensor.sim_soak_load_power`), `effective_load_w = load_sensor_W + sum(rated_W for
  each ON plug in ha_switch_watts)`.

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
