# Solar HA / Node-RED split (operator 2026-09-24)

## Home Assistant (`/site-solar`, packages)

- **Device clamps only** on Site solar: Victron BLE, Sungold Modbus, EM16 (via `site_em16_*` live wrappers when stale/off-path).
- **No** template site totals, jumper tiles, or equal-share sensors in HA packages or Site solar storage. Legacy 8-panel / PWM / `/3` math in Node-RED is **retired** until `scripts/nodered_solar_computed.js` is updated for three strings (T2 2s3p, KU 2p, KU 2s) and new BLE keys.
- Dump automations stay in `dump_control.yaml` (H5082 dump sockets; small templates for staging only).

## Node-RED (`http://192.168.0.105:1880/`)

- **Solar plant diagram** tab: editable topology, live device status from HA REST.
- **Solar computed meters** tab + page **`/solar/computed`**: derived watts (jumper, EM16 A3 live; KU per-string est pending BLE keys). Logic: `scripts/nodered_solar_computed.js` (mirrors `solar_watt_ledger.py` helpers). PWM and equal-share `/3` retired 2026-10-02.

HA remains the **sensor bus**; Node-RED is the **derived display** (and diagram editor).

## Retired in HA (do not re-add to Site solar)

See `SOLAR_DEVICE_SENSORS_ONLY.md` removed list. Use Node-RED computed page or extend `nodered_solar_computed.js`.
