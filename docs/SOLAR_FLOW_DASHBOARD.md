# Solar flow dashboard (Victron GX-style)

**Status:** Operator doc for a **local** live energy-flow page served from this repo.
Implementation: `scripts/solar_flow_server.py` + static assets (sibling work). No Lovelace
scrape. No HA token in the browser or git.

**Official references (RULE #1):**

- Victron GX UI layout (sources left, storage centre, loads right; dark default; browser
  Remote Console): [Cerbo GX — The new user interface](https://www.victronenergy.com/media/pg/Cerbo_GX/en/the-new-user-interface.html)
- Home Assistant REST `GET /api/states` with `Authorization: Bearer`: [REST API](https://developers.home-assistant.io/docs/api/rest/)
- alfa-ai dump-load policy (deterministic, not LLM; brain code `solar_dump.py`): [HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md)
  (sibling: `../alfa-ai/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md`)
- Off-grid / hybrid **diversion load** (vendor term; this UI says **dump load**): Morningstar
  TriStar [Diversion Manual §6.0](https://www.morningstarcorp.com/wp-content/uploads/technical-doc-diversion-manual-en.pdf)
  — when the battery is full, excess source energy is routed to a dedicated **diversion load**
  (resistive sink). Same role as the six simulated AC **dump loads** on this page.

**Site physics:** [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md) — T2 vs KU buses, EM16 A3
semantics, sim dump load plugs.

---

## What it is

A **Victron GX Overview**-style single-page view of this site's 24 V plant:

| GX region | This site |
|-----------|-----------|
| **Left — sources** | T2 MPPT (live HA reporter, all BlueSolar datapoints). KU Victron chargers 2-3: **grey unmetered** (no live W; do not print 2x T2 as a reading). KU Renogy PWM: **grey unmetered** (not in HA). |
| **Centre — storage** | Two LiTime 24 V packs: T2 (`HQ2239CQYT2`) and KU (`HQ2239JTRKU`). Jumper is not a numbered bus. |
| **Right — loads** | KU Renogy AC path (**-- W**, no HA inverter) through **cargo-trailer breaker panel** (Refoss EM16): **A3 hot leg**, **B3 Sungold-outlet breaker**, trailer outlet, **Sungold UTI / AC INPUT**, then SPH, then **Sungold AC out** ([reprint §4.1 INV OUTPUT LOAD](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf)). **Sim dump load** plugs 1-6 sit in a **separate column** fed from Sungold AC out (not trailer outlets; not a branch from KU Renogy). T2 Renogy 30A RV is a **grey unmetered** dead-end (idle if no RV). |
| **Sungold cart (AC from KU outlet)** | SPH302480A + 2x 100 Ah. **DC stays off T2/KU.** Operator (16 Sep): **AC input is plugged into a KU Renogy trailer outlet.** Draw that AC hop on the Overview (not a disconnected island). Live MQTT when the sidecar is up. |
| **Meters — Refoss** | All EM16 A1-C6 numeric channels as **meters**, not extra loads. **Do not add A3+B2.** |

Dark theme by default (matches GX). Numbers on every node: **W**, **V**, **A**, **SoC %**, MPPT
**charge state** where available.

Animated SVG power lines show energy direction when data is flowing. Sim plug **fans** spin when
the switch is ON. **Green LED** = on or flowing; **grey** = off or unavailable.

A side **ALFa dump loads** panel is a **deterministic dump-load explainer** — same thresholds
and allowlist policy as alfa-ai `src/ops/solar_dump.py` (brain setting keys
`ha_solar_dump_*`). It is **not** an LLM. It shows thinking text (surplus math, SoC gate,
charge stage, hysteresis, min on/off dwell) and **planned / held** plug actions. Actuation
stays on alfa-ai; this page is read-only for loads.

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

The browser polls `GET /api/snapshot?view=production` or `?view=demo` every **2 s** with
`cache: 'no-store'`. The proxy sends `Cache-Control: no-store`
([RFC 9111](https://www.rfc-editor.org/rfc/rfc9111.html#name-cache-control);
[http.server](https://docs.python.org/3/library/http.server.html)). The UI view preference
is stored in browser `localStorage` under key `solar-flow-view` (`production` or `demo`;
default `production`) per [MDN localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage).

Header **HA HH:MM:SS** is snapshot `fetched_at`. Watts / SoC / switch state come from HA
[`last_updated`](https://www.home-assistant.io/docs/configuration/state_object/) on each
entity in **production**. **Demo** view uses static illustrative numbers from
`web/solar-flow/demo-snapshot.json` and refreshes `fetched_at` every poll with the same
header clock format.

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

### Production view (default)

Header toggle **Production** (default). Browser requests `GET /api/snapshot?view=production`.

When a readable HA token exists, the proxy calls
[HA REST `GET /api/states`](https://developers.home-assistant.io/docs/api/rest/) for
**plant** entities (MPPT, SmartShunts, EM16, Sungold, etc.) and **sim dump load plugs**
from HA (`config/packages/sim_dump_plugs.yaml` on `.105`):
`switch.sim_ac_plug_*`, `sensor.sim_ac_plug_*_power`, `sensor.sim_dump_load_power`.
Do **not** overwrite HA plug states with `demo-snapshot.json` when those entities exist.

If any required sim-dump entity is **missing** from HA (package not installed), the proxy
fills **only** those ids from `demo-snapshot.json` and sets `sim_dump_demo: true`. When
all required sim-dump ids are present in HA, `sim_dump_demo: false`.

Snapshot `mode: live`, `view: production`. No giant **DEMO** watermark. Header badge:
tiny `live`.

**Production without token** (`?view=production`, no `HA_TOKEN_FILE`): HTTP 200,
`mode: demo`, plant tiles stay `--` (no fake 400 W MPPT). Sim plugs load from
`demo-snapshot.json` for UI testing. `label` explains that production needs the
gitignored token on the proxy. No HA REST calls.

### Demo view (operator toggle)

Header toggle **Demo**. Browser requests `GET /api/snapshot?view=demo`. Allowed even when
a token exists (compare illustrative vs live). Token stays server-side only.

Full illustrative `web/solar-flow/demo-snapshot.json` including plant numbers (400 W
etc.). Snapshot `mode: demo`, `view: demo`. Giant red **DEMO** watermark on
(`mode === 'demo'` only; live production with `sim_dump_demo: true` does **not** enable
the watermark).

### Offline default fetch (no `view` query, no token)

Same as production-without-token: sim plugs from demo file, plant missing, `mode: demo`.
Keeps backward compatibility for bare `GET /api/snapshot`.

`prefers-reduced-motion: reduce` still disables line animation and fan spin
([MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)).

### Snapshot `view` query parameter

Parsed with [`urllib.parse.parse_qs`](https://docs.python.org/3/library/urllib.parse.html#urllib.parse.parse_qs):

| `view` | Token | Result |
|--------|-------|--------|
| (missing) | yes | Live production |
| (missing) | no | Offline (sim only) |
| `production` | yes | Live production |
| `production` | no | Offline + token label |
| `demo` | either | Full illustrative demo file |
| other | -- | HTTP 400 |

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
**centre**, consumers on the **right**. Sungold **DC** stays off T2/KU.

**KU AC hop (operator 16 Sep evening):** Refoss EM16 lives **in the cargo-trailer
breaker panel**. KU Renogy feeds that panel. **EM16 A3 is the hot leg** in the panel
(B2 is the return -- never add A3+B2). That hot leg feeds **cargo-trailer outlets**.
**Right now only Sungold is plugged in** -- the cord goes into Sungold **UTI /
AC INPUT** ([reprint §4.1](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf);
LCD `AC INPUT V` / `AC INPUT Hz`; setting `[01] UTI` is mains-priority, not a utility
meter). Draw that as one left-to-right flow:

`KU Renogy --> breaker panel (Refoss, A3 hot leg) --> B3 breaker --> trailer outlet --> Sungold UTI (AC INPUT) --> SPH --> Sungold AC out --> dump loads`

Do **not** hang A3 as a fake load on the sim-plug AC riser. Do **not** branch sim dump loads
from KU Renogy (`path-sim-acbus` starts at `node-sg-acout`, not the inverter). Sim dump load
plugs are **not** trailer outlets. Click a node for HA recorder history via proxy `GET /api/history`
(never call HA from the browser).

Plant detail is from [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md). Live `entity_id`s
below are from HA `.storage/core.entity_registry` on `.105` (16 Sep 2026). **Lovelace /
MQTT live ids win** when both a policy canonical and a live row exist (example: Sungold
`sensor.sungold_sph302480a_load_active_power` over a stale `_load_power`). Policy
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
| **T2 MPPT** (charger 1) | Live: `sensor.solar_controller_solar` (W), `sensor.solar_controller_charge_state`; also `battery`, `battery_charging`, `charging_power`, `load`, `load_power`, `yield_today`, `rssi`. Policy canonical `..._solar_power` / `..._battery_state` is filled from these. | Only **reporter** in MQTT. Animate PV flow when solar W is numeric and > 0 (demo or live). BlueSolar fields: [monitoring](https://www.victronenergy.com/media/pg/Manual_BlueSolar_MPPT_75-10_up_to_100-20/en/monitoring.html). |
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
| **KU Renogy 2 kW** | **No inverter entity.** Tile stays **-- W** (unmetered). Do **not** paint EM16 A3 onto this node. | Feeds the **cargo-trailer breaker panel** (ATS / manual TS). |
| **Breaker panel (Refoss)** | A3 on the incoming hot leg: `sensor.em16_a3_power` (+ V/A). Meter strip for A1-C6. | Physical home of the EM16 in the cargo-trailer panel. Label **Cargo trailer panel**. [EM16](https://www.home-assistant.io/integrations/refoss/). |
| **B3 breaker** | `sensor.em16_b3_power` (+ V/A) when present; hop falls back to \|A3\| while Sungold is the only outlet load | Breaker that feeds the outlet Sungold is plugged into. Highlight on the diagram and in the meter bank. |
| **Trailer outlet** | Unmetered node. | Fed by B3. **Operator 16 Sep evening:** only Sungold plugged in. |
| **Sungold UTI** | `sensor.sungold_sph302480a_grid_voltage` / `_grid_current` / `_grid_frequency`; hop W from B3 (or A3 fallback) | LCD **AC INPUT** / UTI ([reprint §4.1](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf)). Not a utility meter. |
| **Sim A/C plugs 1-6** | `switch.sim_ac_plug_*`, `sensor.sim_ac_plug_*_power`, `sensor.sim_dump_load_power` | [SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md). **Not** trailer outlets. Column title **Sim dump loads**. Do **not** show `input_boolean.sim_ac_plug_*_internal`. |
| **Other EM16 channels** | `sensor.em16_{a1-c6}_{power,voltage,current,...}` | Meter bank on the panel. **Never add A3+B2.** B2 = return of A3. C1-C6 unused CTs (~0 W). |

### Sungold cart (AC from KU Renogy outlet; DC separate)

SPH302480A LCD names: [SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md),
[reprint §4.1](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf).
**DC** of the cart (2x 100 Ah) is **not** paralleled onto T2/KU. **AC INPUT** is
mains-side on the hybrid ([reprint §4.1](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf))
and on this site is the **KU Renogy outlet**, not a utility meter.

Put Sungold **on the same Overview as the trailer AC path**. Do not hide it below the
fold as an unrelated island. **Layout (16 Sep evening, readability pass):** one left-to-right AC chain after KU
Renogy -- **panel (A3 hot leg), B3 breaker, trailer outlet, Sungold UTI** -- with hop
watt labels in **gutters** between tiles (not on top of nodes). Sim dump loads are a **separate
column** (`Sim dump loads` banner) fed from **Sungold AC out** (`node-sg-acout`,
`sensor.sungold_sph302480a_load_active_power`); it does **not** share the A3/B3/UTI conductors
and does **not** branch from KU Renogy
([CSS `gap`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/gap);
[grid `minmax`](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Grid_layout/Basic_concepts);
GX Overview three regions). SVG `text` uses **`fill`**, not CSS `color`
([SVG `text`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/text)).
Normal-size labels meet [WCAG 2.2 1.4.3 Contrast (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
(4.5:1 on `#0d1117`). Do **not** copy Victron logos.

`viewBox` **0 0 1480 1020**, `max-width` 1480px. Minimum tile gap **24px**. Primary
watts **20px**; node titles **16px**; details and hop labels **13px**. Dim secondary text
**`#c9d1d9`** on `--bg-deep` (not `#6e7681`).

| Element | Role |
|---------|------|
| `node-panel` | Cargo-trailer breaker panel (Refoss EM16 home) |
| `node-b3` | B3 breaker feeding Sungold outlet (highlighted) |
| `node-trailer-outlet` | Trailer outlet (only Sungold plugged in) |
| `node-sg-uti` | Sungold UTI / AC INPUT (grid V/A/Hz) |
| `plugs-column` | Sim dump load plugs 1-6 (x ~1210+, not on A3/B3 wire) |

**Tile bounding boxes** (SVG user units; horizontal gap = next `x` minus prior `x + width`):

| Element | x | y | width | height | Gap to next |
|---------|---|---|-------|--------|-------------|
| `node-panel` | 565 | 310 | 115 | 90 | 30px to B3 |
| `node-b3` | 710 | 328 | 88 | 64 | 24px to trailer |
| `node-trailer-outlet` | 822 | 342 | 78 | 40 | 24px to UTI |
| `node-sg-uti` | 924 | 308 | 148 | 98 | (end of AC chain) |
| `path-sim-acbus` | 700-1180 | **640** | -- | -- | from `node-sg-acout` right edge to sim riser |
| plug tiles 1-6 | 1210 | 175-435 | 170 | 44 | column; icons at x=1222 (+12 inset); 30px gap from riser |

**Conductors (snap to node edges; hop ids in `app.js`):**

| Path id | Connects | Hop watts |
|---------|----------|-----------|
| `path-ku-renogy-panel` | KU Renogy right edge to panel | \|A3\| (`sensor.em16_a3_power`) |
| `path-panel-b3` | Panel hot leg to B3 breaker | \|B3\| if numeric, else \|A3\| while Sungold is the only outlet load |
| `path-b3-outlet-sg-uti` | B3 to trailer outlet to Sungold UTI | same as B3 hop (or grid V x A fallback on UTI tile) |
| `path-sg-uti-sph` | Sungold UTI down to SPH302480A | same AC-in watts |
| `path-sim-acbus` | Sungold AC out (`node-sg-acout`) to sim dump-load riser | sim plug sum or `--` |
| `path-sim-riser` | Vertical sim dump-load bus (riser to plugs) | sim plug sum or `--` |
| `path-sim-plug-1` … `path-sim-plug-6` | Riser to each sim plug | per-plug W |

Do **not** draw EM16 A3 as a load tile on the sim dump-load AC riser (`node-em16` at the old
x=700 y=70 position is removed). A3 is shown on the **panel incoming hop** and in the meter
bank only.
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
copies it onto `_load_power` for dump load math. If both exist, **active power wins**.

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
| AC INPUT V/A/Hz (+ W hop) | Sungold UTI | Tile V/A/Hz: `..._grid_*`. Hop W: `sensor.em16_b3_power` when present, else `sensor.em16_a3_power`; fallback display W is grid V x A. Click history prefers `sensor.em16_a3_power` (allowlisted). |
| Output mode / fault | SPH tile | `..._inverter_state`, `_fail_code`, `binary_sensor.sungold_sph302480a_fault_active` |
| Refoss A1-C6 | Meter bank | `sensor.em16_*` |

### SVG conductors (snap to node edges)

End-to-end watt path (operator 16 Sep):

```
T2 suitcases (2) --> BlueSolar MPPT --W--> Battery 1 -- --> T2 Renogy RV (idle)
KU suitcases (2+2, unmetered) --> chargers 2-3 --dashed--> Battery 2
KU PWM suitcases (2, unmetered) --> Voyager --dashed--> Battery 2
Battery 2 --> KU Renogy 2 kW --> breaker panel (A3 hot leg) --> B3 --> trailer outlet
   |-- Sungold UTI (AC INPUT) --> SPH302480A
   |       |-- cart 2x 100 Ah (DC, not T2/KU)
   |       |-- Sungold PV panels --> SPH
   |       +-- Sungold AC OUTPUT --> sim dump load column (plugs 1-6; NOT trailer outlets)
```

Hop watt labels sit in gutters on each conductor (live numeric W, or `--` if unmetered).

**Sim dump load hops** (`path-sim-acbus`, `path-sim-riser`, `path-sim-plug-*`): sum of **sim
dump load plug** watts when any plug reports W; otherwise `--` (unmetered). **Do not** drive
these from EM16 A3 or B3.

**Sungold UTI hops** (`path-ku-renogy-panel`, `path-panel-b3`, `path-b3-outlet-sg-uti`,
`path-sg-uti-sph`): panel leg uses \|A3\|; B3 leg uses \|B3\| when numeric else \|A3\|
while Sungold is the only outlet load; UTI tile also shows Sungold `grid_*` and falls
back to grid V x A when both clamps are missing.

| Path id | Connects | Hop watts |
|---------|----------|-----------|
| `path-t2-panels-mppt` | T2 suitcase pair to BlueSolar | T2 MPPT solar W |
| `path-t2-mppt-batt1` | MPPT to Battery 1 | `sensor.solar_controller_charging_power` when present; else `battery_charging` x `battery` V; else solar W |
| `path-t2-batt1-renogy` | Battery 1 to T2 Renogy (idle) | unmetered |
| `path-ku-panels-chargers` | KU Victron suitcase groups to chargers 2-3 (dashed) | unmetered |
| `path-ku-chargers-batt2` | Chargers 2-3 to Battery 2 (dashed) | unmetered |
| `path-ku-pwm-panels` | PWM suitcases to Voyager (dashed) | unmetered |
| `path-ku-pwm-batt2` | PWM to Battery 2 (dashed) | unmetered |
| `path-ku-batt2-inverter` | Battery 2 to KU Renogy | \|Battery 2 W\| when discharging |
| `path-ku-renogy-panel` | KU Renogy to breaker panel | \|A3\| |
| `path-panel-b3` | Panel hot leg to B3 breaker | \|B3\| or \|A3\| fallback |
| `path-b3-outlet-sg-uti` | B3 to outlet to Sungold UTI | B3 hop W |
| `path-sg-uti-sph` | Sungold UTI to SPH | B3 hop W |
| `path-sim-acbus` | Sungold AC out (`node-sg-acout`) to sim dump-load riser | sim plug sum or `--` |
| `path-sim-riser` | Vertical sim dump-load bus (riser to plugs) | sim plug sum or `--` |
| `path-sim-plug-1` … `path-sim-plug-6` | Riser to each sim plug | per-plug W |
| `path-sg-pv-panels` | Sungold PV panels to SPH / cart PV tile | PV W |
| `path-sg-pv-batt` | Sungold PV to cart battery | PV W |
| `path-sg-batt-inv` | Cart battery to SPH | cart batt W |
| `path-sg-inv-acout` | SPH to AC out | load W |

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
| **DEMO watermark** | Large red word, full page, only when snapshot `mode` is `demo` (Demo view or no-token production). Live production (`mode: live`) never shows it, even when `sim_dump_demo: true`. |
| **Mode badge** | Tiny header word only: `live` (HA plant) or `demo` (Demo view / no token). Same green badge styling. |
| **View toggle** | Header **Production \| Demo**; persisted in `localStorage` key `solar-flow-view`. |

GX manuals do **not** publish Overview hex colors; dark charcoal + cyan is operator choice, not a Victron palette. Do **not** copy Victron logos, GX/VRM screenshots, or product bitmaps ([press assets](https://www.victronenergy.com/information/press) are for press, not this UI). Structure only: three columns, dark default, tappable-looking tiles. Title is **Solar flow**, not Cerbo / VRM / Remote Console.

Every node tile shows live numbers where HA provides them. Missing sensors show `--` and grey
state.

---

## ALFa dump loads (deterministic dump-load explainer)

**Dump load** (Morningstar **diversion load** and Blue Sky **dump load** are the same
role; see [Morningstar TriStar §6.0](https://www.morningstarcorp.com/wp-content/uploads/technical-doc-diversion-manual-en.pdf))
is an excess-energy sink: when the battery is full, surplus PV is diverted into extra
loads instead of being wasted. **ALFa dump loads** uses surplus solar (PV W minus
effective load W) to turn simulated AC dump loads on or off. alfa-ai `solar_dump.py`
implements that policy deterministically -- thresholds, charge state, and plug allowlist
-- with **no LLM**. This page's side panel mirrors those rules read-only: surplus,
effective load, shunt V/A, and per-plug ON/OFF/SKIP decisions. The six **Sim dump load**
plugs are the dump loads (simulated until real switches exist); they are not
cargo-trailer outlets.

Read-only mirror of alfa-ai `decide_dump()` -- same defaults as
[HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md).
**No LLM.** No `POST` to HA switch services from this page.

### Inputs (default entity ids)

| Setting key | Default entity | Role |
|-------------|----------------|------|
| `ha_solar_entity` | `sensor.solar_controller_solar_power` | T2 PV W. Live Lovelace is `sensor.solar_controller_solar` -- proxy copies that onto the canonical id. |
| `ha_load_entity` | `sensor.sim_dump_load_power` | Plant AC load W for surplus math (sim-plug aggregate; `0` when all OFF). **16 Sep topology:** EM16 A3 is Sungold SPH AC-in on the KU Renogy trailer outlet, **not** KU trailer house load -- do **not** point dump load at `sensor.em16_a3_power` while A3 is Sungold AC-in. When a real KU house clamp exists, set `ha_load_entity` to that sensor; see [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md). |
| `ha_soc_entity` | `sensor.battery_1_soc` | Display only while unsynced. Live MQTT is `sensor.battery_1_state_of_charge`. |
| `ha_shunt_voltage_entity` | `sensor.battery_1_voltage` | Thinking text (LiTime 28.4-29.2 V nameplate). Not a SoC substitute. |
| `ha_shunt_current_entity` | `sensor.battery_1_current` | Thinking text; +charge / -discharge. |
| `ha_soc_unsynced` | `true` | Skip the 85% SoC gate. Victron publishes **no** voltage-to-% map. |
| `ha_charge_state_entity` | `sensor.solar_controller_battery_state` | Must be in `float` or `absorption` to arm dump-load-on. Live Lovelace is `sensor.solar_controller_charge_state`. |
| `ha_switch_allowlist` | six `switch.sim_ac_plug_*` | Plugs eligible for decisions |
| `ha_switch_watts` | rated W per plug | Rated W per ON switch (fallback when load sensor unavailable; **not** added when `ha_load_entity` is `sensor.sim_dump_load_power`) |

### Surplus math

```
surplus_w = solar_W - effective_load_w
```

- **Default (`ha_load_entity` = `sensor.sim_dump_load_power`):** `effective_load_w` is the
  aggregate sensor only (no double-count with `ha_switch_watts`). If the sensor is
  `unavailable`, fall back to the sum of rated W for ON plugs in `ha_switch_watts`.
- **Real plant clamp configured:** when `ha_load_entity` is a house/trailer EM16 sensor
  (not `sensor.sim_dump_load_power`), `effective_load_w = load_sensor_W + sum(rated_W for
  each ON plug in ha_switch_watts)`.

### Gates (thinking text)

The panel lists why dump-load control is armed or skipped:

1. `ha_solar_dump_enabled` - policy on/off
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
`tests/test_ha_label_victron_refoss.py`); dump-load policy defaults keep `_solar_power`. The proxy aliases
both. Battery SoC is `sensor.battery_*_state_of_charge` (MQTT name "State of charge").
Sungold tiles use the live MQTT ids in the table above (`tests/test_ha_label_sungold_solar.py`).

---

## Security and scope

| Rule | Why |
|------|-----|
| Token in file only | HA [REST API](https://developers.home-assistant.io/docs/api/rest/) Bearer auth |
| No Lovelace scrape | Frontend is not a machine API (alfa-ai policy) |
| Localhost bind default | Dashboard is operator LAN tooling, not a public surface |
| Read-only loads | Dump-load **actuation** stays on alfa-ai `.111` with audit (`solar_dump_actuated`) |
| Victron BLE / Sungold publishers unchanged | Sensor-only; no MQTT publish back to hardware |

---

## Related

- [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md) — buses, EM16 A3 history, formulas
- [SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md) — six sim switches on `.105`
- [ALFA_AI_HOW_TO_USE.md](ALFA_AI_HOW_TO_USE.md) — brain ↔ HA pointer
- [ALFA_CLUSTER_INTEGRATION.md](ALFA_CLUSTER_INTEGRATION.md) — hub / multi-repo layout
- alfa-ai [HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md) — dump load settings (`ha_solar_dump_*`) and token
