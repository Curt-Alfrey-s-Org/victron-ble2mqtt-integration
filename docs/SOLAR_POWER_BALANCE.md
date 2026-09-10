# 24 V solar -- watt in vs watt out

**Date of log:** 10 Sep 2026 (America/New_York).  
**Meters:** Home Assistant **Solar** (Victron BLE via Pi4 MQTT on `.105`) and **Refoss** EM16.  
**HA host:** alfa-ai [HOMEASSISTANT_105_OPERATOR.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOMEASSISTANT_105_OPERATOR.md).  
**Idle cluster watts:** alfa-ai [CLUSTER_IDLE_POWER.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/CLUSTER_IDLE_POWER.md).

This is the **corrected** record of a live power-balance pass. Early chat inferred a Sungold PV path and added EM16 A3+B2 as two sources. Both were wrong (see [Corrections](#corrections)).

Victron BLE in this repo still lists **one** BlueSolar plus two SmartShunts (`override/victron_ble2mqtt/user_settings_data.py`). The other two MPPTs are in hardware; they are not in MQTT yet. Scale production as **3 times** the reporting MPPT until those keys exist.

## Layout (operator, 2026-09-10)

| Piece | Role |
|-------|------|
| 3 Victron MPPTs | Identical hardware, same panel setup, same location. **One** reports in HA (`Solar-controller`). |
| SmartShunt HQ2239CQYT2 | Battery 1. Tracks the reporting MPPT (same amps). |
| SmartShunt HQ2239JTRKU | Battery 2. Net of the two silent MPPTs minus load on that bank. |
| Renogy 2000 W inverter | AC for alfa-ai `.111`, `.148`, `.229` (pve-i5), Midea dehumidifier, metal fan. **Sungold SPH302480A is not hooked up** on this site ([SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md) stays optional USB docs only). |
| EM16 A3 | Clamp on the **main load leg** -- **total AC used**. |
| EM16 B2 | Clamp on a **wall outlet** on that leg (branch, already inside A3). **Do not add A3+B2.** |

## How to read the meters

SmartShunt current sign ([operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)):

- **Positive** = charge into the battery.
- **Negative** = discharge (load).
- The shunt reports **net** battery current (charge minus load), not each charger by itself.

Wiring ([installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html)):

- Battery negative only on **BATTERY MINUS**.
- All charger and load negatives on **SYSTEM MINUS**.
- Anything on BATTERY MINUS is excluded from SoC.

Charge-state **bulk** on the reporter means it is still pushing current. Battery 2 **SoC 0%** at ~27 V is **unsynced**, not empty. SoC needs a full-charge sync ([operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)).

## Formulas

```
PV_one     = Solar-controller solar power (W)
I_one      = Solar-controller battery current (A)
PV_three   = 3 * PV_one
PV_silent  = 2 * PV_one
Shunt_net  = Battery_1_power + Battery_2_power
DC_leftover = PV_three - Shunt_net
  (positive leftover = watts toward inverter/loads on the 24 V bus)
AC_used    = EM16 A3 power (use magnitude; PF -1.0 is CT orientation)
Batt2_to_inv = PV_silent - Battery_2_power
  (when shunt 2 is charging, this is silent-pair PV minus what stayed in the bank)
```

Expect BLE fields from different advertisements to disagree by a few watts. A3 and B2 can differ by a few watts (calibration / not simultaneous).

## Corrections

| Wrong (early chat) | Correct |
|--------------------|---------|
| ~720-940 W extra PV from a Sungold hybrid MPPT | Operator: Sungold is **not** connected. All PV is **3 times** the Victron reporter. |
| Used = A3 + B2 (~1,380 W) | **A3 is the total.** B2 is a branch of A3. Adding them double-counts the outlet. |
| A3 and B2 "two CTs on the same feed" as the only explanation | They are **main vs outlet**. They read almost equal because that outlet carries essentially the whole main leg. |
| Shunt 2 negative => the two silent MPPTs are fully on BATTERY MINUS | Shunt 2 is **net**. When 2x MPPT < Renogy draw, it goes negative. When sun returned (15:23), shunt 2 went **+13.3 A / +361 W**. Silent pair minus shunt 2 ~ Renogy draw on that bank. |
| "Watts bypassing the shunts" = 2x MPPT as if unseen | Those watts **do not show as extra charge current** because the shunt nets them against the inverter. They are not a second, unmetered PV array. |

Battery 2 **consumed Ah** stuck near **-579 Ah** with SoC **0%** while voltage is mid-pack still means SoC was never synced (and may include a long period of wrong wiring). That is separate from the instantaneous net-current story.

## Snapshot log (10 Sep 2026)

Times are approximate from the chat. Powers in watts. PV three-wide is **3 x reporter**. A3/B2 are EM16 magnitudes.

| Time ET | Notes | PV one | PV x3 | Shunt 1 | Shunt 2 | Shunt net | A3 used | B2 outlet |
|---------|-------|--------|-------|---------|---------|-----------|---------|-----------|
| 11:32 | First tiles; fan/dehum likely on | 250.0 | 750 | +240.9 | -75.3 | +166 | 698.2 | 694.3 |
| 13:46 | Before cluster start; fan/dehum on | 271.0 | 813 | +276.5 | -242.4 | +34 | 687.9 | 692.0 |
| 14:57 | Clouds; fan+dehum **off**; alfa-ai up | 109.0 | 327 | +104.8 | -172.2 | -67 | 417.8 | 402.3 |
| 15:23 | Sun back; B2 cropped out of Refoss | 292.0 | 876 | +295.0 | +360.9 | +656 | 396.3 | -- |
| **15:53** | Sun; loads still shed | **236.0** | **708** | **+230.6** | **+34.6** | **+265** | **400.0** | **405.6** |

Other EM16 channels were **0.0 W** in every Refoss shot.

### 13:46 -> 14:57 (shed fan and dehumidifier)

A3 dropped **~270 W** (688 to 418). Metal fan **1.3 A** at 120 V is **~156 W**; the rest (**~114 W**) is the Midea. B2 dropped with A3, so both appliances were on that outlet circuit. Remaining **~400 W** is `.111` / `.148` / `.229` plus Renogy overhead with alfa-ai started.

### 14:57 -> 15:23 (sun returns)

A3 stayed ~400 W. Shunt 2 flipped from **-172 W** to **+361 W**. Extra PV went into the banks, not into new AC load.

Reporter vs shunt 1 stayed matched all day (example 15:23: **10.6 A** vs **10.9 A**; 15:53: **8.3 A** vs **8.5 A**).

### 15:53 close (best instantaneous fit)

| | W |
|---|---|
| Produced (3 x 236.0) | 708 |
| Used (A3) | 400 |
| Stored (shunt net) | +265 |
| Residual (PV - used - stored) | ~43 (~6%) |
| Silent pair (2 x 236) | 472 |
| Shunt 2 charge | +35 |
| Implied Renogy DC on battery 2 (472 - 35) | ~437 |

A3 **400 W** AC vs **~437 W** DC on the battery-2 path is inverter/wiring loss, not a second PV source. Battery 1 **+231 W** matches the reporting MPPT; that bank is storing, not feeding the Renogy in this shot.

15:23 had a larger residual (sun ramping faster than BLE; shunt net **+656 W** vs leftover after A3). Prefer 15:53 for the closed balance.

## What is still open

1. **MQTT** for the two silent MPPTs (MAC + 32-hex Instant Readout keys in `victron-secrets.env` + `user_settings_data.py`) so HA does not rely on 3x scaling. See [DEVICES.md](DEVICES.md#victron-bluetooth).
2. **Battery 2 SoC sync** after a real full charge (or confirm historical BATTERY MINUS wiring and move negatives to SYSTEM MINUS, then sync).
3. Confirm Renogy DC negatives land on **SYSTEM MINUS** of HQ2239JTRKU (the 15:23/15:53 net-current story assumes they do).

## Related

- [DEVICES.md](DEVICES.md) -- add the two silent MPPTs
- [SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md) -- optional USB sidecar; **not used on this site**
- [ALFA_CLUSTER_INTEGRATION.md](ALFA_CLUSTER_INTEGRATION.md)
- Victron SmartShunt [installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html), [operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)
