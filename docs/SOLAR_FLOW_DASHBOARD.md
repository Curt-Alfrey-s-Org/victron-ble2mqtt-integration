# Solar flow dashboard (Victron GX-style)

**Status:** Operator doc for the GX-style energy-flow page. **Production** runs on
**`.105`** next to Home Assistant: one process, one LAN URL, one Tailscale URL
(same port), same data. Implementation: `scripts/solar_flow_server.py` + static
assets. No Lovelace scrape. No HA token in the browser or git.

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
| **Left — sources** | T2 MPPT (live HA reporter, all BlueSolar datapoints). KU **MPPT 1**, **MPPT 2**, and **PWM**: same **card chrome** as T2 (`#art-mppt`, V/A/state rows, **est.** subtitle) — **solid tiles**, not dashed empty bricks. Watts are equal-thirds **est.** only (no live Victron KU clamps; do not print 2× T2 as live). PWM is visually distinct (PWM label / controller type) but same card language. |
| **Centre — storage** | Two LiTime 24 V packs: T2 (`HQ2239CQYT2`) and KU (`HQ2239JTRKU`). Jumper is not a numbered bus. |
| **Right — loads** | KU Renogy **A/C** path through **cargo-trailer breaker panel** (Refoss EM16): **A3 hot leg**, **B3 Sungold-outlet breaker**, trailer outlet, **cargo-trailer vent fan** (sibling load). Battery 2 **load** line uses the same \|A3\| watts as KU Renogy. **Sim dump load** plugs 1-6 sit in a **separate column** fed from Sungold A/C out (not trailer outlets; not a branch from KU Renogy). T2 Renogy 30A RV is a **grey unmetered** dead-end (idle if no RV). |
| **Sungold cart lane** | **UTI / A/C INPUT**, SG panels, PV, cart 2×100 Ah, SPH302480A, **A/C out**, Pi4. **Not** in the KU A/C / breaker lane. **D/C stays off T2/KU.** A/C cord from the KU trailer outlet feeds UTI in this lane. Live MQTT when the sidecar is up. |
| **Weather strip (outside tiles)** | One **weather-channel-style** sun/sky (clear, partly cloudy, cloudy, storm, …) driven by HA weather / Ecobee — **outside** all equipment boxes, not a sun glyph inside the T2 MPPT tile. Entity: **TODO** (grep `.105` registry; see [Weather strip](#weather-strip-outside-equipment-17-sep)). |
| **Meters — Refoss** | All EM16 A1-C6 numeric channels as **meters**, not extra loads. **Do not add A3+B2.** |

Dark theme by default (matches GX). Numbers on every node: **W**, **V**, **A**, **SoC %**, MPPT
**charge state** where available.

Animated SVG power lines show energy direction when data is flowing. Sim plug **fans** spin when
the switch is ON. **Green LED** = on or flowing; **grey** = off or unavailable.

A side **ALFa dump loads** panel is a **deterministic dump-load explainer** — same thresholds
and allowlist policy as alfa-ai `src/ops/solar_dump.py` (brain setting keys
`ha_solar_dump_*`). It is **not** an LLM. It shows thinking text (surplus math, path losses, SoC gate,
charge stage, hysteresis, min on/off dwell) and **planned / held** plug actions. Actuation
stays on alfa-ai; this page is read-only for loads. Combined path losses start at panel
watts and sum metered conversion hops (T2 MPPT, Sungold SPH); dump ON/OFF uses
`surplus_after_path_losses_w` ([SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md)).

---

## Topology

Same dual-address pattern as Home Assistant on this host
([TAILSCALE.md](TAILSCALE.md); HA Linux frontend + ufw:
[installation/linux](https://www.home-assistant.io/installation/linux/);
MagicDNS: [Tailscale MagicDNS](https://tailscale.com/docs/features/magicdns);
connect by name:port:
[Connect to devices](https://tailscale.com/docs/how-to/connect-to-devices)).
Do **not** commit the live MagicDNS or `100.x` address.

| Where | Home Assistant | Solar flow (this page) |
|-------|----------------|------------------------|
| Home LAN | `http://192.168.0.105:8123` | `http://192.168.0.105:8765` |
| Away, Tailscale on | `http://YOUR-TAILSCALE-NAME:8123` | `http://YOUR-TAILSCALE-NAME:8765` |

Both solar-flow URLs hit **one** `solar-flow.service` on `.105`. They are not two sites.

`127.0.0.1` is IPv4 loopback on **whichever machine** is running the proxy. It is **not** a Tailscale address. On `.105` it is the local socket Tailscale Serve may proxy; on a laptop it is only that laptop.

```
Browser  LAN :8765  or  Tailscale MagicDNS :8765  (same process)
    |
    v
systemd solar-flow.service on .105  (--lan = 0.0.0.0:8765)
    |  Authorization: Bearer <token from file on .105>
    |  GET http://127.0.0.1:8123/api/states
    v
Home Assistant Container (.105:8123, host net)
    ^ MQTT / Refoss / Modbus
Pi4 Victron BLE, optional Sungold, Pi5 Theengs, EM16
```

Do **not** call HA from browser JavaScript. Do **not** scrape Lovelace (`/dashboard-solar/0`).
The Python proxy holds the long-lived token server-side only
([REST API](https://developers.home-assistant.io/docs/api/rest/)).

---

## Operator (one path)

**Production** is systemd on **`.105`** (`systemd/solar-flow.service`):
[systemd.service](https://manpages.debian.org/bookworm/systemd/systemd.service.5.html)
`Type=simple`. Bind is `--lan` (`0.0.0.0:8765`) per Python
[http.server](https://docs.python.org/3/library/http.server.html). Firewall matches HA:
LAN subnet + `ufw allow in on tailscale0` ([ufw](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html)).
Do **not** `ufw allow 8765/tcp` from the public internet. Do **not** enable Tailscale Funnel.

**Prerequisites:** victron clone on `.105`. HA up on `127.0.0.1:8123`. Gitignored token at
`/home/ansible/alfa-ai/deploy/secrets/home-assistant/long-lived.token` (unit `HA_TOKEN_FILE`;
never in git, chat, or the unit file body). Token creation: alfa-ai
[HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md).

**Install / refresh the unit** (after `git pull` on `.105`):

```bash
sudo cp /home/ansible/victron-ble2mqtt-integration/systemd/solar-flow.service /etc/systemd/system/solar-flow.service
sudo systemctl daemon-reload
sudo systemctl enable --now solar-flow.service
```

**ufw** (once; same shape as HA `:8123` on this host):

```bash
sudo ufw allow from 192.168.0.0/24 to any port 8765 proto tcp comment 'solar-flow LAN'
sudo ufw allow in on tailscale0 to any port 8765 proto tcp comment 'solar-flow Tailscale'
```

**Open the page** (placeholders only):

```text
http://192.168.0.105:8765/
http://YOUR-TAILSCALE-NAME:8765/
```

Optional HTTPS on the tailnet: this host may already run
[Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) proxying `/` to
`http://127.0.0.1:8765` (Serve only supports that loopback target). That URL is the **same**
dashboard, not a second copy. Leave Serve as-is unless the operator removes it. Never Funnel.

**Ad-hoc / laptop** (not production): Python 3.11+ in this clone; token on disk; bind stays
localhost unless you pass `--lan`:

```bash
cd /path/to/victron-ble2mqtt-integration
export HA_BASE_URL=http://192.168.0.105:8123
export HA_TOKEN_FILE=/path/to/long-lived.token
python scripts/solar_flow_server.py
```

Then `http://127.0.0.1:8765/` on **that** machine only.

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

**Operator end state (17 Sep 2026)** — implement from this doc before changing
`index.html` / `app.js` / `styles.css` / Python.

1. **KU D/C bus matches T2 MPPT card language** — three charger rows (MPPT 1, MPPT 2,
   PWM): panels → charger → Battery 2; six suitcases **2+2+2**; equal-thirds **est.** W
   (`kuEqualShareW`); PWM visually distinct, same `#art-mppt` chrome as T2 (not dashed
   empty bricks).
2. **Weather sun/sky outside equipment** — strip above or beside the diagram, not inside
   `#node-solar`. States: clear, partly cloudy, cloudy, storm, … from HA weather /
   Ecobee climate (entity **TODO** below).
3. **`node-sg-uti` in the Sungold cart lane only** — KU A/C lane stops at trailer outlet +
   vent fan; UTI sits with SG panels, PV, cart battery, SPH, A/C out, Pi4.
4. **Downstream A3 load propagation** — when `sensor.em16_a3_power` shows load W, every
   hop on that path shows that magnitude until the split: panel → B3 → trailer outlet →
   vent vs UTI branch. Vent is a **load**, not a loss. Do **not** use A3 as
   `ha_load_entity`.
5. **UTI passthrough** — if SPH A/C out (~5 W live, Pi4) is non-zero while grid V×A reads
   ~0 W, UTI / A/C-in hop W must still show the power feeding that output (plus inverter
   conversion), not **0 W** on UTI while A/C out flows.
6. **Cart battery tare in UTI/grid mode** — cart **0.1 A** (or similar standby) is inverter
   DC tare while on UTI/mains, **not** “battery supplying Pi4” for dump math; alfa-ai dump
   should ignore cart tare in UTI mode (ledger note only — gate rewrite is out of scope).
7. **Vent fan** — four speeds; live is speed **1** (lowest). Animate `#art-fan` when
   running. HA entity **TODO** below.
8. **Hop W labels on conductors** — midpoint on the wire path (`hop-path-*` on the
   `<path>`), especially Sungold cart hops; not in the lane-title gutter.
9. **Losses sidebar unchanged** — conversion + vdrop W sum to total; loads are not losses.

Follows Victron GX Overview
([Cerbo GX UI](https://www.victronenergy.com/media/pg/Cerbo_GX/en/the-new-user-interface.html)):
energy sources on the **left** (including **suitcase panel** tiles), batteries in the
**centre**, consumers on the **right**. Sungold **DC** stays off T2/KU.

**KU AC hop (operator 16-17 Sep):** Refoss EM16 lives **in the cargo-trailer
breaker panel**. KU Renogy feeds that panel. **EM16 A3 is the hot leg** (B2 is the
return -- never add A3+B2). That outlet circuit feeds a **cargo-trailer vent fan**
(sibling load). **Sungold UTI / A/C INPUT** is **not** drawn in this lane — it lives
in the **Sungold cart lane** below (cord from the same trailer outlet). Do **not** set
A3 equal to SPH A/C in only.

```
KU Renogy --> breaker panel (A3) --> B3 --> trailer outlet
  |-- cargo-trailer vent fan (KU A/C lane)
  |
  +-- (cross-lane) --> Sungold UTI (Sungold cart lane) --> SPH --> A/C out --> Pi4 + sim dump column
```

**Downstream A3 watts (17 Sep):** when \|A3\| ≥ 0.5 W, paint the same magnitude on
`path-ku-renogy-panel`, `path-panel-b3`, and the trailer-outlet segment until the split.
After the split: UTI branch uses `utiHopW` (passthrough rule below); vent branch uses
`vent_fan_W`. Do not leave upstream hops at **0 W** while A3 shows load.

Pi4 is plugged into SPH **A/C OUTPUT**, not the trailer KU outlet. It is not a sim dump
plug. No HA watt entity on Pi4 — tile shows **~5 W** from SPH load active power when
that is the only A/C-out load. Nodes are **illustrated components** (PV grid,
battery pack, fan, Pi board), not Victron GX clones.

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
| **KU MPPT 1 suitcases (2 in series)** | **No entity.** Equal-share **est.** W on the panel tile (same 1/3 as each charger) | Left column, same visual language as T2 suitcases (`#art-pv`). Feeds **KU MPPT 1** charger tile to its right. |
| **KU MPPT 2 suitcases (2 in series)** | **No entity.** Equal-share **est.** on panel tile | Feeds **KU MPPT 2** charger. Six KU suitcase panels total (2+2+2). |
| **KU PWM suitcases (2 in series)** | **No entity.** Equal-share **est.** on panel tile | Feeds **KU PWM** (Voyager) charger tile. PWM likely less than each MPPT ([PWM vs MPPT](https://www.victronenergy.com/upload/documents/Technical-Information-Which-solar-charge-controller-PWM-or-MPPT.pdf)); no site derate. |
| **KU Victron MPPT 1** | **No entity.** Equal-share **est.** of combined KU PV; **est.** subtitle | Solid tile like T2: `#art-mppt`, V/A rows when batt2 V known, charge-state row optional. Combined KU_PV = batt2 − jumper + load. Do not print 2× T2 as live. |
| **KU Victron MPPT 2** | **No entity.** Equal-share **est.**, subtitle **est.** | Same 1/3 as MPPT 1 when sun is equal; same card chrome as MPPT 1. |
| **KU Renogy PWM** | **No entity** (Voyager 20A). Equal-share **est.**; PWM label distinct | Same card chrome as MPPT (`#art-mppt` or dedicated `#art-pwm` symbol); wire reaches Battery 2 (not a stub). |
| **T2 MPPT** (charger 1) | Live: `sensor.solar_controller_solar` (W), `sensor.solar_controller_charge_state`; also `battery`, `battery_charging`, `charging_power`, `load`, `load_power`, `yield_today`, `rssi`. Policy canonical `..._solar_power` / `..._battery_state` is filled from these. | Only **reporter** in MQTT. Animate PV flow when solar W is numeric and > 0 (demo or live). **No decorative sun inside this tile** — weather strip is separate ([Weather strip](#weather-strip-outside-equipment-17-sep)). BlueSolar fields: [monitoring](https://www.victronenergy.com/media/pg/Manual_BlueSolar_MPPT_75-10_up_to_100-20/en/monitoring.html). |
| **KU Victron** (MPPT 1 and 2) | **No entity.** Equal-share **est.** W (and A if batt2 V known) | Same solid card language as T2 MPPT; subtitle **est.** Do **not** display 2× T2 watts as live. Do **not** use dashed empty charger bricks. |

**KU 24 V D/C visual order (matches T2):** left to right **suitcase panels → MPPT/PWM charger → Battery 2**. Three stacked rows (MPPT 1, MPPT 2, PWM); each row is panel \| charger \| bus to Battery 2. **Panel spacing:** each KU suitcase tile is the same **150×100** brick as T2 (`x=40`); **16 px** vertical gutter between the three KU rows; **16 px** between the T2 lane bottom and the KU D/C lane (no empty left-column hole). Panel→charger gap matches T2 (`path-t2-panels-mppt` `190→254`). Panel and charger hops use the same equal-share **est.** W (`kuEqualShareW`). SVG [`use`](https://www.w3.org/TR/SVG11/struct.html#UseElement) + [`text`](https://www.w3.org/TR/SVG11/text.html) follow T2 panel brick layout — **solid** `#node-bg` tiles, not dashed unmetered placeholders.

### Weather strip (outside equipment, 17 Sep)

One **weather-channel-style** sky above the flow diagram (outside all `#node-*` equipment
boxes). Driven by Home Assistant weather and/or Ecobee climate already on `.105`
([REST `GET /api/states`](https://developers.home-assistant.io/docs/api/rest/)).
Map `state` / `condition` / attributes to icons: **clear**, **partly cloudy**,
**cloudy**, **storm**, etc. This replaces the decorative `#sun-icon` inside `#node-solar`.

| Role | Entity id | Status |
|------|-----------|--------|
| Weather condition / forecast | **TODO entity:** search `weather.*` on `.105` registry | Not in this repo clone — confirm via `GET /api/states` or Ask ALFa `ha_get_states` on host `105` |
| Ecobee / climate (optional secondary) | **TODO entity:** search `climate.*` (Ecobee HomeKit Device per [DEVICES.md](DEVICES.md)) | Same |

Implementation ids for other agents: `#node-weather-sky` (group), `#val-weather-condition`
(text), `#pip-weather-sky` (optional). Proxy may add `weather_entity_id` to snapshot when
wired. Do **not** invent entity ids in production view.

### Storage (centre)

| Node | Live HA entities | Notes |
|------|------------------|-------|
| **LiTime T2** | `sensor.battery_1_state_of_charge` (alias of `battery_1_soc`), `voltage`, `current`, `power`, `consumed_ah`, `remaining_minutes`, `rssi`, `auxiliary_mode`, `midpoint_voltage`, `midpoint_shift`, `midpoint_shift_2` | SmartShunt `HQ2239CQYT2` |
| **LiTime KU** | `sensor.battery_2_state_of_charge` (alias of `battery_2_soc`), `voltage`, `current`, `power`, `consumed_ah`, `remaining_minutes`, `rssi`, `auxiliary_mode` | Net of KU chargers + PWM minus KU Renogy |
| **T2-KU jumper** | No jumper shunt. Hop **estimate** `solar_W - T2_Renogy_W - batt1_W` (signed W). T2 Renogy is **0 W** while the RV is idle. | Drawn as `path-t2-ku-jumper` between Battery 1 and Battery 2. Positive = T2 to KU. SmartShunt current is **net pack** only ([operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)); two shunts plus a jumper cannot clamp pack-to-pack amps ([installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html)). |

**Primary numbers (16 Sep 2026):** shunt **V** and signed **A** (and **W**, or V x A if the
power sensor is missing). Charge **+** / discharge **-** per SmartShunt
[operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html).
Battery tiles label shunt A as **shunt net** (signed HA float on the program path;
UI magnitude + color). **In from sources** lists inbound branch amps (**I = |P| / V**
on that bus's shunt V) and **Total in A** — sum of inbound branches only; see
[SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md). Jumper: **T2→KU** (+W est.) adds
inbound on Battery 2 only; **KU→T2** (−W est.) adds inbound on Battery 1 only.
KU MPPT/PWM lines are **est.** from equal-share W. When that share is ≥ 0.5 W, the six KU
suitcase/charger SVG hops get `.flowing` (cyan dash motion) the same as T2 — still **est.**,
not a live Victron clamp. Loads are not inbound. SVG
[`text`](https://www.w3.org/TR/SVG11/text.html) rows use `node-detail` / `est-label`.
Energy sidebar may show **T2 in from sources** / **KU in from sources** totals
(magnitude A, green when &gt; 0).
**SoC % is shown but not used for control or animation** -- the shunts are unsynced
(site history: KU **SoC 0%** at ~27-29 V). Victron displays SoC as `---` when
unsynchronised; this page labels the HA % **SoC unsynced**. Do **not** invent a
software SoC from voltage. LiTime absorb **28.4-29.2 V** is nameplate, not an 85%
substitute. Pips and wires follow numeric V/A/W and switch ON only.

### Loads (right) and Renogy inverters

| Node | Live HA / display | Notes |
|------|-------------------|-------|
| **T2 Renogy 2 kW** | **No inverter entity.** Tile **0 W**. EM16 A2/B4 are **candidate** idle watts on the meter bank, not confirmed inverter W | 30A RV outlet. Idle if no RV. Do not treat A2 as a second site load. |
| **KU Renogy 2 kW** | **No inverter entity.** Tile **0 W** (unmetered). Do **not** paint EM16 A3 onto this node. | Feeds the **cargo-trailer breaker panel** (ATS / manual TS). |
| **Breaker panel (Refoss)** | A3 on the incoming hot leg: `sensor.em16_a3_power` (+ V/A). Meter strip for A1-C6. | Physical home of the EM16 in the cargo-trailer panel. Label **Cargo trailer panel**. [EM16](https://www.home-assistant.io/integrations/refoss/). |
| **B3 breaker** | `sensor.em16_b3_power` (+ V/A) when present; hop falls back to \|A3\| while Sungold is the only outlet load | Breaker that feeds the outlet Sungold is plugged into. Highlight on the diagram and in the meter bank. |
| **Trailer outlet** | Unmetered split node. Hop W = \|B3\| if numeric else \|A3\| (same as upstream when A3 loads). | Fed by B3. Splits to vent fan (KU A/C lane) and UTI (Sungold cart lane). |
| **Trailer vent fan** | Residual `max(0, trailer_outlet_W − utiHopW)` when both metered; else unmetered | **4 speeds**; live is speed **1** (lowest). Animate `#art-fan` when running. HA entity **TODO** (see below). Sibling of Sungold on the KU outlet. **Load**, not a loss. |
| **Sungold UTI** | `sensor.sungold_sph302480a_grid_voltage` / `_grid_current` / `_grid_frequency`; hop W = **`utiHopW`** (see passthrough) | **Sungold cart lane only** — not in KU A/C / breaker lane. LCD **AC INPUT** / UTI ([reprint §4.1](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf)). |
| **Sim A/C plugs 1-6** | `switch.sim_ac_plug_*`, `sensor.sim_ac_plug_*_power`, `sensor.sim_dump_load_power` | [SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md). **Not** trailer outlets. **Not** Pi4. Column title **Sim dump loads**. |
| **Pi4** | No dedicated watt entity. Tile **~5 W** from `sensor.sungold_sph302480a_load_active_power` when Pi4 is the A/C-out load | Always-on on SPH **A/C OUTPUT**. Victron BLE radio. |

**Vent fan HA entity (17 Sep):**

| Role | Entity id | Status |
|------|-----------|--------|
| Cargo-trailer vent fan (4 speeds) | **TODO entity:** search `fan.*` on `.105` registry | Not in this repo — confirm speed **1** = lowest via [REST states](https://developers.home-assistant.io/docs/api/rest/) |

Implementation ids: `#node-vent-fan`, `#val-vent-fan-w`, `#pip-vent-fan`, `#path-outlet-vent-fan`,
`#hop-path-outlet-vent-fan`, `#art-fan` (animate when fan `state` on / speed ≥ 1).

**`utiHopW` passthrough (17 Sep):** primary = SPH grid V × A when both numeric. If grid V×A
is ~0 but `sensor.sungold_sph302480a_load_active_power` ≥ 0.5 W (Pi4 / A/C-out load),
UTI hop W = **max(grid V×A, load_active_power + small conversion allowance)** so UTI never
shows **0 W** while A/C out is feeding ~5 W. Do **not** substitute \|A3\| for UTI hop W.
Cart battery **0.1 A** standby in UTI/grid mode is **inverter tare**, not pack discharge
toward Pi4 — do not paint cart batt W as supplying Pi4 when output mode is UTI/mains.
| **Other EM16 channels** | `sensor.em16_{a1-c6}_{power,voltage,current,...}` | Meter bank on the panel. **Never add A3+B2.** B2 = return of A3. C1-C6 unused CTs (~0 W). |

### Sungold cart lane (AC from KU trailer outlet; DC separate)

SPH302480A LCD names: [SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md),
[reprint §4.1](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf).
**DC** of the cart (2x 100 Ah) is **not** paralleled onto T2/KU. **AC INPUT (UTI)** is
mains-side on the hybrid ([reprint §4.1](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf))
and on this site is fed from the **KU Renogy trailer outlet** via a cross-lane conductor
from `#node-trailer-outlet` — **not** as the next horizontal tile in the KU A/C lane.

**Lane contents (left → right):** `#node-sg-uti` (A/C INPUT) → `#node-sg-panels` / `#node-sg-pv`
→ `#node-sg-batt` → `#node-sg-inv` (SPH) → `#node-sg-acout` → `#node-pi4`. Sim dump loads
stay in the **fifth lane** (`Sim dump loads` banner) fed from `#node-sg-acout` only.

Put Sungold **on the same Overview** as the trailer A/C path. **Layout:** five **separate
SVG lanes** (filled bands, 16px vertical gutter) so T2 D/C, KU D/C, KU A/C, Sungold cart,
and sim dump loads never share a row. **Hop watt labels sit on the conductor** they
annotate (midpoint of the `<path>` or adjacent offset along the wire), **not** in the
lane-title gutter between bands. Sim dump loads are the **fifth lane** on the right
(`Sim dump loads` banner) fed from **Sungold A/C out**
(`node-sg-acout`, `sensor.sungold_sph302480a_load_active_power`); they do **not** share
the A3/B3 conductors and do **not** branch from KU Renogy
([CSS `gap`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/gap);
[grid `minmax`](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Grid_layout/Basic_concepts);
GX Overview three regions). SVG `text` uses **`fill`**, not CSS `color`
([SVG `text`](https://developer.mozilla.org/en-US/docs/Web/SVG/Element/text)).
Normal-size labels meet [WCAG 2.2 1.4.3 Contrast (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
(4.5:1 on `#0d1117`). Do **not** copy Victron logos.

**Watts:** missing or unmetered hop/node watts print **`0 W`**, never `-- W`. Missing
voltage/current may still print `-- V / -- A`. **Display** is **magnitude + color**
(`formatW` uses `Math.abs`; no `+` / `-` prefix on hop watts). **`watt-pos`**
(green, `#3fb950`) is charge / solar production. **`watt-neg`** (red, `#f85149`)
is a **load** or battery discharge. Unsigned load magnitudes (Battery 2 `load 25 W`,
KU Renogy hop, dump plugs, A3, vent fan, Sungold A/C out) always use the load/red
class even when the number is positive. True zero keeps **`watt-zero`** (cyan idle).
Jumper direction is the **text label** (`T2 to KU` / `KU to T2`); the hop watts are
magnitude with signed color (+ into KU green, - out of KU red). Path / conversion /
vdrop **losses** paint red or idle, never green. SVG `text` uses **`fill`**
([SVG `text`](https://www.w3.org/TR/SVG2/text.html)). UI copy is **A/C** and **D/C** plus
**dump load** / **diversion load** (Morningstar). Do not print draft names such as
"soak".

**Program path stays signed.** alfa-ai dump-load, watt ledger, and Ask ALFa
`home_energy_ops` use signed floats from HA REST (`jumper_w`, Battery 2 `stored_w`,
shunt A, surplus). The brain must **not** read this page, hop SVG text, or CSS
color. Green/red is **human-only**. If a future consumer only had a screenshot,
red watts would be negative. Optional UI fallback: `formatW` with a minus on
**load-class** (`opts.load` / `watt-neg`) only -- **not enabled now**
(`formatSignedW` is a no-op stub). Do not put a minus on the SVG for alfa-ai.

`viewBox` **0 0 1560 1420**. CSS `.flow-svg` uses `min-width: 1240px` so the diagram
scrolls instead of shrinking into overlapping tiles. Minimum tile gap **24px**. Primary
watts **20px**; node titles **16px**; details and hop labels **13px**. Dim secondary text
**`#c9d1d9`** on `--bg-deep` (not `#6e7681`).

| Element | Role |
|---------|------|
| `node-panel` | Cargo-trailer breaker panel (Refoss EM16 home) |
| `node-b3` | B3 breaker feeding trailer outlet (highlighted) |
| `node-trailer-outlet` | KU Renogy trailer outlet split (vent fan + cross-lane to UTI) |
| `node-vent-fan` | Cargo-trailer vent fan (KU A/C lane) |
| `node-sg-uti` | Sungold UTI / A/C INPUT — **Sungold cart lane only** |
| `node-weather-sky` | Weather-channel strip (outside equipment boxes) |
| `plugs-column` | Sim dump load plugs 1-6 (dump lane x 1148, not on A3/B3 wire) |

**Lanes** (SVG user units):

| Lane | x | y | width | height |
|------|---|---|-------|--------|
| T2 24 V D/C | 16 | 12 | 1116 | 276 |
| KU 24 V D/C | 16 | 304 | 1116 | 400 |
| KU A/C path | 16 | 816 | 1116 | 252 |
| Sungold cart | 16 | 1084 | 1116 | 316 |
| Sim dump loads | 1148 | 12 | 380 | 756 |

**Tile bounding boxes** (from live `index.html` `rect` / path `d`; no `transform` on these nodes):

| Element | x | y | width | height |
|---------|---|---|-------|--------|
| `node-panel` | 36 | 856 | 190 | 148 |
| `node-b3` | 250 | 856 | 160 | 118 |
| `node-trailer-outlet` | 434 | 856 | 170 | 118 |
| `node-vent-fan` | 434 | 990 | 170 | 58 |
| `node-sg-uti` | 300 | 1088 | 100 | 48 (above DC row; no overlap with cart batt) |
| `node-weather-sky` | 1148 | 12 | 380 | 88 (outside dump plugs **and** the Sim dump loads banner) |
| `sim-dump-banner` | 1338 | 128 | (text) | 15px; SVG `text` **y** is the alphabetic baseline ([SVG 1.1 text](https://www.w3.org/TR/SVG11/text.html#TextElement)), so ink sits in about `[y-15, y]`. Banner ink must start at **y ≥ 100** (weather rect bottom) with a gutter — baseline **128** |
| `path-sim-acbus` | 1086-1140 | 1212 | | |
| plug tiles 1-6 | 1176 | 140-640 | 340 | 76 |

**Conductors (snap to node edges; hop ids in `app.js`):**

| Path id | Connects | Hop watts |
|---------|----------|-----------|
| `path-ku-renogy-panel` | KU Renogy right edge to panel | \|A3\| when A3 ≥ 0.5 W (`sensor.em16_a3_power`) |
| `path-panel-b3` | Panel hot leg to B3 breaker | same \|A3\| magnitude while downstream (do not drop to 0) |
| `path-b3-outlet` | B3 to `#node-trailer-outlet` | \|B3\| if numeric, else \|A3\| |
| `path-outlet-vent-fan` | Trailer outlet to vent fan | `vent_fan_W` (load) |
| `path-outlet-uti` | Trailer outlet cross-lane to `#node-sg-uti` | `utiHopW` (passthrough rule) |
| `path-sg-uti-sph` | Sungold UTI to SPH302480A (cart lane) | same `utiHopW` |
| `path-sg-acout-pi4` | Sungold A/C out to Pi4 | share of `load_active_power` (~5 W live) |
| `path-sim-acbus` | Sungold A/C out (`node-sg-acout`) to sim dump-load riser | sim plug sum or **0 W** |
| `path-sim-riser` | Vertical sim dump-load bus (riser to plugs) | sim plug sum or **0 W** |
| `path-sim-plug-1` … `path-sim-plug-6` | Riser to each sim plug | per-plug W on the plug tile (duplicate hop labels hidden) |

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

If those entities are missing (sidecar off), watt tiles print **0 W**; V/A may stay `-- V / -- A`. Live snapshot lists plant gaps in `missing_entity_ids` (legacy `sim_soak_*` ids are not shown). **No** Renogy PWM / inverter ids are invented.

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
| AC INPUT V/A/Hz (+ W hop) | Sungold UTI (cart lane) | Tile V/A/Hz: `..._grid_*`. Hop W: **`utiHopW`** (passthrough; not A3). Click history prefers `sensor.em16_a3_power` (allowlisted) for outlet total only. |
| Output mode / fault | SPH tile | `..._inverter_state`, `_fail_code`, `binary_sensor.sungold_sph302480a_fault_active` |
| Refoss A1-C6 | Meter bank | `sensor.em16_*` |

### SVG conductors (snap to node edges)

End-to-end watt path (operator 16 Sep):

```
T2 suitcases (2) --> BlueSolar MPPT --W--> Battery 1 --0 W--> T2 Renogy RV (idle)
Battery 1 <--jumper est.--> Battery 2   (T2-KU; no jumper clamp)
KU MPPT1 panels (2) --> KU MPPT 1 --est.--> Battery 2
KU MPPT2 panels (2) --> KU MPPT 2 --est.--> Battery 2
KU PWM panels (2) --> KU PWM --est.--> Battery 2
Battery 2 --> KU Renogy 2 kW --> breaker panel (A3 hot leg) --> B3 --> trailer outlet
   |-- vent fan (KU A/C lane)
   +-- cross-lane --> Sungold UTI (cart lane) --> SPH302480A
           |-- cart 2x 100 Ah (DC, not T2/KU)
           |-- Sungold PV panels --> SPH
           +-- Sungold AC OUTPUT --> Pi4 (~5 W) + sim dump load column (plugs 1-6)
```

Hop watt labels sit **on each conductor** (midpoint along the `<path>`, class
`hop-watt` / id `hop-path-*`). The T2-KU jumper hop is an **estimate** (not a clamp).

**A3 downstream rule:** when \|A3\| shows load, `path-ku-renogy-panel`, `path-panel-b3`,
and `path-b3-outlet` (or equivalent) carry that magnitude until the outlet split.

**Sim dump load hops** (`path-sim-acbus`, `path-sim-riser`, `path-sim-plug-*`): sum of **sim
dump load plug** watts when any plug reports W; otherwise **0 W**. **Do not** drive
these from EM16 A3 or B3.

**Sungold / trailer hops:** panel leg uses \|A3\| on KU Renogy → panel; B3/outlet legs
use \|B3\| or \|A3\| fallback; vent uses `vent_fan_W`; UTI uses **`utiHopW`** (passthrough,
not A3); `path-sg-uti-sph` matches UTI hop.

| Path id | Connects | Hop watts |
|---------|----------|-----------|
| `path-t2-panels-mppt` | T2 suitcase pair to BlueSolar | T2 MPPT solar W |
| `path-t2-mppt-batt1` | MPPT to Battery 1 | `sensor.solar_controller_charging_power` when present; else `battery_charging` x `battery` V; else solar W |
| `path-t2-batt1-renogy` | Battery 1 to T2 Renogy (idle) | **0 W** (no HA inverter) |
| `path-t2-ku-jumper` | Battery 1 to Battery 2 (T2-KU jumper) | **estimate** `solar_W - 0 - batt1_W`; positive T2 to KU. Not a clamp. |
| `path-ku-mppt1-panels` | KU MPPT 1 suitcase pair to MPPT 1 charger | equal-share **est.** |
| `path-ku-mppt1-batt2` | KU MPPT 1 to Battery 2 | equal-share **est.** |
| `path-ku-mppt2-panels` | KU MPPT 2 suitcase pair to MPPT 2 charger | equal-share **est.** |
| `path-ku-mppt2-batt2` | KU MPPT 2 to Battery 2 | equal-share **est.** |
| `path-ku-pwm-panels` | KU PWM suitcase pair to PWM charger | equal-share **est.** |
| `path-ku-pwm-batt2` | KU PWM to Battery 2 | equal-share **est.** |
| `path-ku-batt2-inverter` | Battery 2 to KU Renogy | **A3/trailer A/C est** (same W as Battery 2 **load** line). Not Battery 2 shunt. DC in >= AC out; no inverter efficiency invented. |
| `path-ku-renogy-panel` | KU Renogy to breaker panel | \|A3\| when load present |
| `path-panel-b3` | Panel hot leg to B3 breaker | same \|A3\| magnitude (downstream propagation) |
| `path-b3-outlet` | B3 to trailer outlet | \|B3\| or \|A3\| fallback |
| `path-outlet-vent-fan` | Outlet to vent fan | `vent_fan_W` (load) |
| `path-outlet-uti` | Outlet cross-lane to UTI | `utiHopW` (passthrough) |
| `path-sg-uti-sph` | Sungold UTI to SPH (cart lane) | same `utiHopW` |
| `path-sg-acout-pi4` | Sungold A/C out to Pi4 | ~5 W from load active power when Pi4-only |
| `path-sim-acbus` | Sungold A/C out (`node-sg-acout`) to sim dump-load riser | sim plug sum or **0 W** |
| `path-sim-riser` | Vertical sim dump-load bus (riser to plugs) | sim plug sum or **0 W** |
| `path-sim-plug-1` … `path-sim-plug-6` | Riser to each sim plug | per-plug W on the plug tile (duplicate hop labels hidden) |
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
| **KU MPPT/PWM est. tiles** | Solid cards like T2 (`#art-mppt`); subtitle **est.** — **not** dashed empty bricks. Equal-thirds W only. Do **not** print 2× T2 watts. |
| **KU charger conductors** | Each row is two short hops that **snap to tile edges**: suitcase right `x=190` → charger left `x=254`; charger right `x=474` → Battery 2 left `x=538`. PWM uses the same geometry at `y=614` (not a stub into empty canvas). When equal-share est. W ≥ 0.5, `updateFlows` adds `.flowing` like T2 — **est. motion**, not a live Victron clamp. |
| **Spinning fan** (`#art-fan` on `#node-vent-fan`; plugs 1, 4, 5) | Vent fan when HA fan on / speed ≥ 1; sim plugs when `switch.sim_ac_plug_*` state `on` |
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
| `ha_load_entity` | `sensor.sim_dump_load_power` | Plant AC load W for surplus math (sim-plug aggregate; `0` when all OFF). EM16 A3 is the **KU trailer outlet total** (Sungold A/C in + cargo vent). Do **not** use A3 as `ha_load_entity`. When a real KU house clamp exists, set `ha_load_entity` to that sensor; see [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md). |
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
combined_losses_w = T2_MPPT_loss + SG_loss   # metered conversion hops only
combined_vdrop_loss_w = sum |ΔV × I| on metered hops
combined_path_losses_w = combined_losses_w + combined_vdrop_loss_w
surplus_after_path_losses_w = surplus_w - combined_path_losses_w
```

Dump ON/OFF uses **`surplus_after_path_losses_w`**. Battery charge is storage, not loss.
KU Victron / PWM D/C is unmetered and omitted from the sum. Hop table: Path losses panel.
Formulas: [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md).

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
5. **Surplus after path losses > 200 W** (`ha_min_surplus_watts`) → target **on**; **<= 50 W** (`ha_off_surplus_watts`) → target **off**; between → hysteresis hold
6. **Min on 600 s / min off 300 s** — dwell timers
7. **Max concurrent on 6** — cap simultaneous sim plugs

Two SmartShunts: thinking and the dump-load metrics show **T2 shunt V/A**
(`sensor.battery_1_voltage` / `_current`, HQ2239CQYT2) and **KU shunt V/A**
(`sensor.battery_2_voltage` / `_current`, HQ2239JTRKU; aliases `_battery_voltage` /
`_battery_current`). Do not print unlabeled "Shunt 25.9V". Amp **display** is
magnitude + color (green = charge into the pack, red = discharge / load);
the HA `state` string and alfa-ai floats stay **signed** +charge / -discharge
([operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)).
Missing A prints **0 A**, not `--`. They are **not** a new skip
threshold. T2 LiTime absorb 28.4-29.2 V is nameplate, not a Victron SoC map.

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
| **Surplus** | `surplus_w` and **Surplus after path losses** (`surplus_after_path_losses_w` = surplus − path losses). Not inside Losses. |
| **Losses** | W line items only: **Conversion losses** + **Vdrop loss** = **Total path losses** (`combined_path_losses_w`). Nested **Vdrop D/C** and **Vdrop A/C** are volts (supporting readings); never summed into the W total. Loads (vent fan, KU Renogy A/C est., dump plugs, Pi4, UTI passthrough) are **not** losses. |
| **Loads** | Vent fan, KU Renogy A/C est., plant load, sim dump loads, effective load — red **load** class, magnitude-only W. |
| **Energy** | Panel in, solar, KU PV est., KU charger est., shunts, SoC — not losses. |
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
| Production bind `0.0.0.0:8765` + ufw | Same dual-address pattern as HA `:8123`; not a public surface |
| Read-only loads | Dump-load **actuation** stays on alfa-ai `.111` with audit (`solar_dump_actuated`) |
| Victron BLE / Sungold publishers unchanged | Sensor-only; no MQTT publish back to hardware |

---

## Implementation ids (for UI / proxy agents)

Do not edit ids in this doc unless the operator changes topology. New ids **17 Sep**:

| Id | Purpose |
|----|---------|
| `#node-weather-sky` | Weather-channel strip outside equipment |
| `#val-weather-condition` | Text label from HA weather state |
| `#path-b3-outlet` | B3 → trailer outlet (split A3 downstream) |
| `#path-outlet-uti` | Cross-lane trailer outlet → `#node-sg-uti` |
| `#hop-path-b3-outlet` | Hop W on `path-b3-outlet` |
| `#hop-path-outlet-uti` | Hop W on `path-outlet-uti` |
| `#art-pwm` | Optional PWM-specific symbol (else `#art-mppt` + PWM label) |

**Relocate (not in KU A/C lane):** `#node-sg-uti`, `#path-sg-uti-sph`, `#val-sg-uti-w`,
`#val-sg-uti-va`, `#val-sg-uti-hz`, `#pip-sg-uti`, `#hop-path-sg-uti-sph`.

**Remove / replace:** `#path-b3-outlet-sg-uti`, `#hop-path-b3-outlet-sg-uti` (horizontal UTI
in KU A/C lane); `#sun-icon` inside `#node-solar`.

**Keep:** `#node-ku-mppt-1`, `#node-ku-mppt-2`, `#node-ku-pwm`, `#node-ku-panel-mppt1`,
`#node-ku-panel-mppt2`, `#node-ku-panel-pwm`, `#node-vent-fan`, `#path-outlet-vent-fan`,
`#hop-path-outlet-vent-fan`, `#node-sg-pv`, `#node-sg-batt`, `#node-sg-inv`,
`#node-sg-acout`, `#node-pi4`, `#path-sg-pv-panels`, `#path-sg-pv-batt`, `#path-sg-batt-inv`,
`#path-sg-inv-acout`, `#path-sg-acout-pi4`, `#hop-path-sg-*`.

**JS helpers (names only):** `kuEqualShareW`, `utiHopW`, `ventFanEstimateW`, downstream
`panelA3W` propagation on KU A/C hops.

**Entity TODOs (confirm on `.105` via [REST states](https://developers.home-assistant.io/docs/api/rest/)):**

| TODO | Search |
|------|--------|
| Weather / sky condition | `weather.*` |
| Ecobee climate (optional) | `climate.*` |
| Cargo-trailer vent fan (4 speeds) | `fan.*` |

---

## Related

- [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md) — buses, EM16 A3 history, formulas
- [SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md) — six sim switches on `.105`
- [ALFA_AI_HOW_TO_USE.md](ALFA_AI_HOW_TO_USE.md) — brain ↔ HA pointer
- [ALFA_CLUSTER_INTEGRATION.md](ALFA_CLUSTER_INTEGRATION.md) — hub / multi-repo layout
- alfa-ai [HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md) — dump load settings (`ha_solar_dump_*`) and token
