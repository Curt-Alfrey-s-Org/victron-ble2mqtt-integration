# 24 V solar -- watt in vs watt out

**Dates of log:** 10 Sep 2026 and **11 Sep 2026** (America/New_York).  
**Solar charging window (this site, 11 Sep):** **09:30-16:00 ET only.** Outside that window the arrays are not charging; the Renogy runs from the banks. Do not treat a 16:00+ MPPT watt reading as a full-day average.  
**Meters:** Home Assistant **Solar** (Victron BLE via Pi4 MQTT on `.105`) and **Refoss** EM16.  
**HA host:** alfa-ai [HOMEASSISTANT_105_OPERATOR.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOMEASSISTANT_105_OPERATOR.md).  
**Idle cluster watts:** alfa-ai [CLUSTER_IDLE_POWER.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/CLUSTER_IDLE_POWER.md).

This is the **corrected** record of a live power-balance pass. Early chat inferred a Sungold PV path and added EM16 A3+B2 as two sources. Both were wrong (see [Corrections](#corrections)).

Victron BLE in this repo still lists **one** BlueSolar plus two SmartShunts (`override/victron_ble2mqtt/user_settings_data.py`). The other two MPPTs are in hardware; they are not in MQTT yet. Scale production as **3 times** the reporting MPPT until those keys exist.

## Layout (operator, 2026-09-10; charging window confirmed 2026-09-11)

| Piece | Role |
|-------|------|
| 3 Victron MPPTs | Identical hardware, same panel setup, same location. **One** reports in HA (`Solar-controller`). **Charge window 09:30-16:00 ET** on 11 Sep (operator). |
| SmartShunt HQ2239CQYT2 | Battery 1. Tracks the reporting MPPT (same amps). |
| SmartShunt HQ2239JTRKU | Battery 2. Net of the two silent MPPTs minus load on that bank. |
| Renogy 2000 W inverter | AC for alfa-ai `.111`, `.148`, `.229` (pve-i5), Midea dehumidifier, metal fan. **Sungold SPH302480A is not hooked up** on this site ([SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md) stays optional USB docs only). |
| EM16 A3 | Clamp on the **main load leg** -- **total AC used** (Renogy outlet path). |
| EM16 B2 | Clamp on a **wall outlet** on that leg (branch, already inside A3). **Do not add A3+B2.** |
| EM16 A2 | **72.8 W** at 14:10 and 14:53. **Do not add A2+A3.** |
| EM16 B4 | **71.9 W** at 14:53 (A2 **72.8 W**). Same main-vs-outlet pattern as A3/B2. **Do not add A2+B4.** |

## How to read the meters

SmartShunt current sign ([operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)):

- **Positive** = charge into the battery.
- **Negative** = discharge (load).
- The shunt reports **net** battery current (charge minus load), not each charger by itself.

Wiring ([installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html)):

- Battery negative only on **BATTERY MINUS**.
- All charger and load negatives on **SYSTEM MINUS**.
- Anything on BATTERY MINUS is excluded from SoC.

Charge-state **bulk** on the reporter means it is still pushing current. **Absorption** means it has reached the absorb voltage and current is tapering. Around **29 V** on a 24 V bank is absorption-range. Battery 2 **SoC 0%** at ~27-29 V was **unsynced**, not empty. After the 11:33 high-voltage point, 14:10 shows SoC **44.4%** and consumed **-12.4 Ah** (was **-598 Ah**) -- a sync or reset happened; voltage and current are still the live story ([operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)). The two banks are **not** at the same voltage when bank 2 is under inverter load (14:10: bank 1 **28.5 V**, bank 2 **26.5 V**).

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

Battery 2 **consumed Ah** was stuck near **-579 to -598 Ah** with SoC **0%** through 11 Sep 11:33. At 14:10 it showed **44.4% / -12.4 Ah** (SoC still wrong vs Ah). At 14:53 it showed **91.7% / -15.4 Ah / 956 min remaining** while still discharging. **91.7% with 15.4 Ah used** is consistent with about **185 Ah** capacity (8.3% used). The 14:10 **44.4%** tile was not. Prefer voltage, current, and power; treat % as usable only when it matches consumed Ah.

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

15:23 had a larger residual (sun ramping faster than BLE; shunt net **+656 W** vs leftover after A3). Prefer 15:53 for the closed balance on that day.

## Snapshot log (11 Sep 2026)

| Time ET | Notes | PV one | PV x3 | Shunt 1 | Shunt 2 | Shunt net | A3 used | B2 outlet |
|---------|-------|--------|-------|---------|---------|-----------|---------|-----------|
| **11:21** | Fan + dehumidifier only (cluster off this inverter) | **273.0** | **819** | **+268.5** | **+80.3** | **+349** | **385.3** | **384.7** |
| 11:33 | Same loads; **shunt BLE incomplete** -- do not close the balance | 271.0 | 813 | 0.0* | -- | -- | 420.0 | 419.9 |
| **14:10** | Fan + dehum + **servers on**; shunts recovered | **273.0** | **819** | **+267.2** | **-363.4** | **-96** | **723** | **708.4** |
| **14:53** | Same loads; still inside **09:30-16:00** window | **256.0** | **768** | **+239.2** | **-371.6** | **-132** | **713.0** | **707.1** |

Other EM16 channels were **0.0 W** through 11:33. At 11:21: reporter **bulk**, 9.6 A at 27.4 V (I x V 263 W vs 273 W PV). Shunt 1 **9.8 A** at 27.5 V. Shunt 2 **2.9 A** at 27.3 V, SoC still **0%**, consumed Ah **-597.9** (was about **-579** on 10 Sep). Yield today **400 Wh**.

At 11:33: reporter still **bulk**, **9.1 A** at **29.1 V**, solar **271.0 W**, yield **450 Wh** (+50 Wh in ~12 min, ~250 W average -- MPPT is live). Pack voltage **29.1 V** on the MPPT and **both** shunts. A3 **420.0 W** (3.6 A, PF -1.0); B2 **419.9 W**. A3 this month **32,160 Wh**, B2 **32,150 Wh** (same order; the 11:21 "327 kWh" reading was a misread extra digit).

`*` Shunt 1 **Power 0.0 W** is on the tile, but **Battery 1 Current** shows **-70** -- the same number as **RSSI -70**, and **I x V** would be ~2 kW discharge, which contradicts 0.0 W. Battery 2 **Current Unknown**, remaining Unknown. Do not treat shunt watts as real for this shot. Prefer **11:21** for the fan+dehum-only close. **14:10** recovered.

At 14:10: reporter **absorption**, **9.1 A** at **28.5 V**, solar **273.0 W**, yield **1,160 Wh**. Shunt 1 **+267.2 W** at **28.5 V / 100%** (P/V ~9.4 A; matches the reporter). Shunt 2 **-363.4 W** at **26.5 V**, SoC **44.4%**, consumed **-12.4 Ah**, remaining **1,290 min**. EM16 A3 **6.1 A** at **118.5 V** (power tile not in the crop; **6.1 x 118.5 = 723 W**), PF -1.0, this month **33,573 Wh**. B2 **708.4 W** / **6.0 A** / **33,642 Wh**. **A2 is 72.8 W** (0.6 A, 2,650 Wh this month) -- first non-zero other channel in this log; not added to A3.

### 11:21 close (fan and dehumidifier only)

| | W |
|---|---|
| Produced (3 x 273.0) | 819 |
| Used (A3) | 385 |
| Stored (shunt net) | +349 |
| Residual (PV - used - stored) | ~85 (~10%) |
| Silent pair (2 x 273) | 546 |
| Shunt 2 charge | +80 |
| Implied Renogy DC on battery 2 (546 - 80) | ~466 |

Reporter vs shunt 1 still matched (**9.6 A** vs **9.8 A** / **+269 W**). Battery 1 is storing the reporting MPPT. Silent-pair leftover vs A3 is the same inverter-loss story as 15:53, with a wider gap (BLE + 3x scale + conversion).

### Same sun, lower AC: 10 Sep 13:46 vs 11 Sep 11:21

Reporter PV was **271 W** then and **273 W** now (three-wide **813** vs **819**). Fan and dehumidifier were on in both shots.

| | 13:46 (fan/dehum; cluster still on the inverter) | 11:21 (fan/dehum only) |
|---|---|---|
| A3 | 688 | 385 |
| Shunt 2 | **-242** (net discharge) | **+80** (net charge) |
| Shunt net | +34 | +349 |

A3 dropped **~303 W** with the cluster hosts off that leg. That is why shunt 2 flipped: silent-pair PV (~546 W) was less than Renogy draw at 688 W AC, and greater than draw at 385 W AC. Not a wiring change.

10 Sep attributed **~270 W** of the 688-to-418 shed to fan + dehumidifier. 11:21 A3 **385 W** with those two still on leaves **~115 W** for Renogy idle and any always-on on that outlet (not a second PV source).

### 11:21 -> 11:33 (A3 up; shunts not usable)

A3 rose **385 to 420 W** (~35 W). B2 tracked A3, so the extra draw stayed on that outlet (dehumidifier cycling is the likely cause; too small to be a host coming back). Reporter PV stayed ~271-273 W. Pack climbed **27.4 V to 29.1 V** (absorption-range on 24 V; MPPT still says bulk).

Shunt 1 going **+269 W to 0.0 W** while the MPPT is still **9.1 A / 271 W** is **not** a sudden zero load on that bank. Battery 1 current equals RSSI; battery 2 current is Unknown. Incomplete Instant Readout -- skip the 11:33 shunt column. **14:10** advertisements are complete again.

### 14:10 close (fan, dehumidifier, servers on)

| | W |
|---|---|
| Produced (3 x 273.0) | 819 |
| Used (A3 I x V) | 723 |
| Used (B2 outlet) | 708 |
| Stored (shunt net) | -96 |
| Residual (PV - B2 - stored) | ~207 (~25%) |
| Silent pair (2 x 273) | 546 |
| Shunt 2 | -363 (discharge) |
| Implied Renogy DC on battery 2 (546 - (-363)) | ~909 |

Shunts recovered. Reporter vs shunt 1 still matched (**9.1 A / 273 W** vs **+267 W** at 28.5 V). Battery 1 is storing at **absorption**; it is not feeding the Renogy. Battery 2 is **net discharging** at **26.5 V** -- silent-pair PV (~546 W) is less than inverter draw with servers up, same pattern as 10 Sep 13:46.

A3 **723 W** vs 11:21 **385 W** is **+338 W** (B2 **708 vs 385 = +323 W**). That is the cluster hosts back on the Renogy, next to yesterday's **~303 W** delta. 14:10 **708-723 W** vs 10 Sep 13:46 **688 W** (fan+dehum+cluster) is the same load mix within ~30 W.

**A2 72.8 W:** not added. If that clamp is a branch of A3 it is already inside 723 W. If it is a separate (grid) feed it is outside the 24 V / Renogy balance.

Bank 1 **28.5 V** vs bank 2 **26.5 V** means the banks are separate; they only looked like one pack at 11:33 when both sat at 29.1 V with almost no inverter current on bank 2.

### 14:53 close (same loads, sun easing)

Still inside the **09:30-16:00 ET** charge window (~67 min left). Reporter **absorption**, **8.9 A** at **28.6 V**, solar **256.0 W**, yield **1,340 Wh** (+180 Wh since 14:10, ~251 W average). Shunt 1 **8.4 A / +239.2 W** at **28.5 V / 100%**. Shunt 2 **-371.6 W** at **26.6 V** (P/V ~**-14.0 A**), SoC **91.7%**, consumed **-15.4 Ah**, remaining **956 min**. A3 **713.0 W** (6.0 A, PF -1.0, 34,179 Wh this month). B2 **707.1 W** / 6.0 A / 34,166 Wh. A2 **72.8 W**; **B4 71.9 W** (0.6 A) -- do not add A2+B4 or A2+A3.

| | W |
|---|---|
| Produced (3 x 256.0) | 768 |
| Used (A3) | 713 |
| Used (B2 outlet) | 707 |
| Stored (shunt net) | -132 |
| Residual (PV - A3 - stored) | ~187 (~24%) |
| Silent pair (2 x 256) | 512 |
| Shunt 2 | -372 (discharge) |
| Implied Renogy DC on battery 2 (512 - (-372)) | ~884 |

Load mix is unchanged vs 14:10 (A3 **713 vs 723**). PV dropped **273 to 256 W**, so shunt net went further negative (**-96 to -132 W**): less solar on the silent pair, same inverter. Reporter vs shunt 1 still tracks (**8.9 A** vs **8.4 A**). Bank 1 stays at absorb **28.5 V**; bank 2 stays **26.6 V** under load.

A2/B4 at **~73/72 W** is the same paired-clamp pattern as A3/B2. Not part of the Renogy 24 V balance unless the operator says those clamps sit on that inverter.

## What is still open

1. **MQTT** for the two silent MPPTs (MAC + 32-hex Instant Readout keys in `victron-secrets.env` + `user_settings_data.py`) so HA does not rely on 3x scaling. See [DEVICES.md](DEVICES.md#victron-bluetooth).
2. **Battery 2 SoC** -- 14:53 **91.7% / -15.4 Ah** matches ~185 Ah capacity. 14:10 **44.4%** did not. Confirm the shunt capacity setting.
3. Confirm Renogy DC negatives land on **SYSTEM MINUS** of HQ2239JTRKU (14:53 **-372 W** at 26.6 V with servers on matches that story).
4. **EM16 A2 / B4** -- 72.8 W / 71.9 W at 14:53. Looks like another main-vs-outlet pair. Operator: grid/utility, a specific server, or a branch of A3?
5. **11:33 shunt BLE** recovered by 14:10. Leave as a known Instant Readout gap if it repeats.

## Related

- [DEVICES.md](DEVICES.md) -- add the two silent MPPTs
- [SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md) -- optional USB sidecar; **not used on this site**
- [ALFA_CLUSTER_INTEGRATION.md](ALFA_CLUSTER_INTEGRATION.md)
- Victron SmartShunt [installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html), [operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)
