# Solar HA / Node-RED split (operator 2026-09-24)

## Home Assistant (`/site-solar`, packages)

- **Device clamps only** on Site solar: Victron BLE, Sungold Modbus, EM16 (via `site_em16_*` live wrappers when stale/off-path).
- **No** template site totals, KU PWM+MPPT est, jumper tiles, or equal-share sensors in HA packages or Site solar storage.
- Dump automations stay in `sim_dump_control.yaml` (small templates for staging only).

## Node-RED (`http://192.168.0.105:1880/`)

- **Solar plant diagram** tab: editable topology, live device status from HA REST.
- **Solar computed meters** tab + page **`/solar/computed`**: derived watts (jumper, KU PWM+MPPT est, equal share, EM16 A3 live). Logic: `scripts/nodered_solar_computed.js` (mirrors `solar_watt_ledger.py` helpers).

HA remains the **sensor bus**; Node-RED is the **derived display** (and diagram editor).

## Retired in HA (do not re-add to Site solar)

See `SOLAR_DEVICE_SENSORS_ONLY.md` removed list. Use Node-RED computed page or extend `nodered_solar_computed.js`.
