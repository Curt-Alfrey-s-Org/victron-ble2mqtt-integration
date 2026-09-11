# 24 V solar -- watt in vs watt out

**Dates of log:** 10 Sep 2026 and **11 Sep 2026** (America/New_York).  
**Solar charging window (this site, 11 Sep):** **09:30-16:00 ET only.** Outside that window the arrays are not charging; the two Renogy inverters run from their LiTimes (and the batt jumper, if it is sharing). Do not treat a 16:00+ MPPT watt reading as a full-day average.  
**Meters:** Home Assistant **Solar** (Victron BLE via Pi4 MQTT on `.105`) and **Refoss** EM16.  
**HA host:** alfa-ai [HOMEASSISTANT_105_OPERATOR.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOMEASSISTANT_105_OPERATOR.md).  
**Idle cluster watts:** alfa-ai [CLUSTER_IDLE_POWER.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/CLUSTER_IDLE_POWER.md).

This is the **corrected** record of a live power-balance pass. Early chat inferred a Sungold PV path, added EM16 A3+B2, and treated the site as **one** Renogy. Sungold and A3+B2 were wrong. The one-inverter model was also wrong (see [Layout](#layout-operator-2026-09-11)).

Victron BLE in this repo still lists **one** BlueSolar plus two SmartShunts (`override/victron_ble2mqtt/user_settings_data.py`). Chargers 2 and 3 are not in MQTT yet -- scale KU Victron as **2 times** the reporter. Do **not** count the PWM string in that 2x/3x.

## Layout (operator, 2026-09-11)

Two **separate 24 V buses**. HA only sees **one** Victron MPPT (charger 1 on **T2**). Chargers 2 and 3 are the same hardware and panel setup, so Victron production on KU is still **2 times** the reporter until those keys exist.

```
T2 bus  HQ2239CQYT2 + LiTime 24V 230Ah
  Victron charger 1  (2 suitcase panels in series)  -- HA Solar-controller
  Renogy 2 kW  -->  30A RV outlet
  RV not plugged in (11 Sep). Batt jumper to KU is the workaround.

KU bus  HQ2239JTRKU + LiTime 24V 230Ah
  Victron chargers 2 and 3  (2 suitcase series each)  -- not in MQTT
  Renogy PWM 12/24 (kit controller)  (2 suitcase on the ground, series)  -- not in HA
  Renogy 2 kW  -->  Renogy ATS (operator: primary = generator)
               -->  manual transfer switch
               -->  cargo-trailer breaker box + RV outlet
  Can run trailer outlets and a second RV.

Sungold cart (not on T2 or KU)
  SPH302480A on a dolly + 2x LiTime 24V 100Ah in parallel (emergency).
```

Eight suitcase panels total: **6** on the three Victron chargers, **2** on the PWM into KU.

| Piece | Bus | Role |
|-------|-----|------|
| Victron charger 1 | **T2** | HA `Solar-controller`. 2 suitcase panels in series. Charge window **09:30-16:00 ET** (11 Sep). |
| Victron chargers 2 and 3 | **KU** | Same arrays as charger 1; silent in MQTT. |
| Renogy PWM 12/24 V | **KU** | Kit controller that ships with Renogy suitcase panels ([Voyager 20A 12/24 PWM](https://www.renogy.com/products/new-edition-voyager-20a-pwm-waterproof-solar-charge-controller)). 2 suitcase panels on the ground, in series. Operator: output to the KU shunt/bus. **Not in HA.** For LiFePO4, Voyager needs **manual** 24 V / lithium set (same page). |
| LiTime 24 V 230 Ah | T2 and KU | One pack per bus. Nominal **25.6 V**, **230 Ah**, **5888 Wh**, charge **28.8 V +/- 0.4 V** ([LiTime 24V 230Ah](https://www.litime.com/products/24v-230ah-truck-lithium-battery)). |
| SmartShunt HQ2239CQYT2 | T2 | Battery 1. Tracks charger 1. |
| SmartShunt HQ2239JTRKU | KU | Battery 2. Net of chargers 2+3 + PWM minus KU Renogy. |
| Batt jumper T2-KU | both | Operator: on because the T2 **30A RV is not connected**. Intended to dump T2 charge into KU. Nameplate 2P **460 Ah / ~11.8 kWh** only if voltages match under load. |
| Renogy 2 kW (T2) | T2 | 30A RV outlet. Idle if no RV. |
| Renogy 2 kW (KU) | KU | Cargo trailer + optional RV, via ATS then manual TS. **This is the path for fan, dehumidifier, and alfa-ai hosts** in the 10-11 Sep EM16 shots. |
| EM16 A3 | KU AC (assumed) | Main load clamp -- **do not add B2**. |
| EM16 B2 | branch of A3 | Wall outlet on that leg. |
| EM16 A2 / B4 | unconfirmed | **~73 / 72 W** at 14:10-14:53. Candidate: **T2 Renogy idle** (no RV). Do not add to A3. |
| Sungold SPH302480A | cart | Emergency dolly. **2x 24 V 100 Ah LiTime in parallel.** USB sidecar optional ([SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md)). Not in the T2/KU watt log. |

### Parallel jumper (T2 RV unused)

The jumper is **not** "these two packs were always one bank." It is there so T2's charger can help KU while the T2 RV outlet is empty.

Victron's one-bank diagram is still: all battery negatives on a bus, **one** shunt, chargers/loads on SYSTEM MINUS ([installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html)). Two shunts plus a jumper will not show batt-to-batt amps.

If the jumper were low-R on **both** poles, T2 and KU voltages would stay within tens of millivolts. They did not:

| Shot | T2 V | KU V | Split |
|------|------|------|-------|
| 11 Sep 11:33 | 29.1 | 29.1 | 0.0 V |
| 11 Sep 14:10 | 28.5 | 26.5 | **2.0 V** (KU loaded) |
| 11 Sep 14:53 | 28.5 | 26.6 | **1.9 V** |

Until that split goes away, size the **loaded** overnight bank as **KU 230 Ah / 5.9 kWh**, not 460 Ah. T2 230 Ah is spare charge sitting behind a weak jumper.

Each shunt capacity in VictronConnect: **230 Ah**. 14:53 KU **91.7% / -15.4 Ah** is 15.4 / 230 = **6.7%** used (implied **93.3%**). The ~185 Ah guess is retired.

## How to read the meters

SmartShunt current sign ([operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)):

- **Positive** = charge into the battery.
- **Negative** = discharge (load).
- The shunt reports **net** battery current (charge minus load), not each charger by itself.

Wiring ([installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html)):

- Battery negative only on **BATTERY MINUS**. Nothing else on that stud or on the battery negative post.
- All charger and load negatives on **SYSTEM MINUS** ("after" the shunt). Until 2020 that stud was labelled LOAD MINUS.
- Anything on BATTERY MINUS is excluded from SoC.

**This site (operator, 11 Sep):** each bus has its charger negatives and that bus's shunt on the **same bus bar**. That is Victron **SYSTEM MINUS** for that bus. **Do not move chargers onto BATTERY MINUS** to "see" charger-to-inverter current ([installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html) step 1).

What each SmartShunt shows ([operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)):

- **Only net current of that LiTime.**
- **Not** MPPT-to-Renogy current that stays on that bus (absorb/float: shunt toward **0 A** while solar still feeds that inverter).
- **Not** current in the T2-KU jumper.
- **Not** the PWM string as its own number (it is folded into KU battery net).

Charger-to-inverter watts: **MPPT solar** (T2 = reporter; KU Victron = 2x reporter) and **EM16** on the AC side. PWM is extra on KU and unmetered. `DC_leftover` below is an estimate, not a clamp.

Charge-state **bulk** on the reporter means it is still pushing current. **Absorption** means it has reached the absorb voltage and current is tapering. LiTime 24 V 230 Ah charge is **28.8 V +/- 0.4 V** (recommended **28.4-29.2 V**) -- T2 **29.1 V** then **28.5 V** matches that. KU **SoC 0%** at ~27-29 V was unsynced. 14:53 **91.7% / -15.4 Ah** fits **230 Ah**. T2 **28.5 V** vs KU **26.6 V** is the jumper not equalizing while KU is loaded.

## Formulas

```
PV_T2         = Solar-controller solar power (W)     # charger 1
PV_KU_victron = 2 * PV_T2                            # chargers 2 and 3
PV_KU_pwm     = unmetered                            # 2 ground suitcases + Renogy PWM
PV_victron    = 3 * PV_T2                            # three identical Victron strings only
Shunt_T2      = Battery 1 power (HQ2239CQYT2)
Shunt_KU      = Battery 2 power (HQ2239JTRKU)
AC_trailer    = EM16 A3 magnitude                    # KU Renogy path (assumed)
```

Do not add A3+B2 or A2+A3. PWM is **not** inside `PV_victron`. 10-11 Sep snapshot tables still use `PV x3` for the three Victron strings.

Expect BLE fields from different advertisements to disagree by a few watts. A3 and B2 can differ by a few watts (calibration / not simultaneous).

## Corrections

| Wrong (early chat) | Correct |
|--------------------|---------|
| One Renogy 2000 W for the whole site | **Two** Renogy 2 kW inverters: T2 -> 30A RV (unplugged); KU -> ATS -> trailer. Cluster AC is on **KU**. |
| Parallel jumper = one 460 Ah bank since day one | Jumper is on because **T2 RV is unused**, to share T2 charge into KU. **~2 V** split under KU load means it is not equalizing. |
| All PV = 3 x Victron reporter | Three Victron strings yes; **plus** 2 suitcase panels on **PWM into KU** (not in HA). |
| ~720-940 W extra PV from a Sungold hybrid MPPT | Sungold is the **dolly cart** (2x 24 V 100 Ah), not on T2/KU. |
| Used = A3 + B2 (~1,380 W) | **A3 is the trailer-leg total.** B2 is a branch of A3. |
| A3 and B2 "two CTs on the same feed" as the only explanation | They are **main vs outlet**. They read almost equal because that outlet carries essentially the whole main leg. |
| Shunt 2 negative => the two silent MPPTs are fully on BATTERY MINUS | Shunt 2 is **KU net** (Victron 2+3 + PWM minus KU Renogy). |
| Shunt should show charger-to-inverter amps at float | Battery monitor shows **that LiTime** only. Chargers on the SYSTEM MINUS bus of that shunt is correct. |
| Battery 2 capacity ~185 Ah from 91.7% / 15.4 Ah | **230 Ah** LiTime. 15.4 / 230 = 6.7% used, implied **93.3%**. |

Battery 2 **consumed Ah** was stuck near **-579 to -598 Ah** with SoC **0%** through 11 Sep 11:33. At 14:10 it showed **44.4% / -12.4 Ah** (SoC still wrong vs 230 Ah). At 14:53 it showed **91.7% / -15.4 Ah / 956 min remaining** while still discharging. **15.4 Ah of 230 Ah** is **6.7%** used (**93.3%** implied). Prefer voltage, current, and power when % and Ah disagree.

**Overnight energy (17.5 h dark, 09:30-16:00 charge window):** KU AC at **720 W** is **~12.6 kWh**. KU LiTime is **5.9 kWh**. A working jumper would add T2's **5.9 kWh** (~11.8 kWh nameplate, ~9.4 kWh at 80%). The jumper is **not** doing that while KU is **2 V** below T2. PWM helps KU only while the sun is up.

## Snapshot log (10 Sep 2026)

Times are approximate from the chat. Powers in watts. **PV x3** is the three Victron strings only (no PWM). A3/B2 are EM16 magnitudes on the **KU / cargo-trailer** path unless noted.

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

**A2 72.8 W:** not added to A3. Candidate **T2 Renogy idle** (RV unplugged).

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

Load mix is unchanged vs 14:10 (A3 **713 vs 723**). PV dropped **273 to 256 W**, so shunt net went further negative (**-96 to -132 W**): less solar on the silent pair, same inverter. Reporter vs shunt 1 still tracks (**8.9 A** vs **8.4 A**). Battery 1 stays at absorb **28.5 V**; battery 2 stays **26.6 V** under load -- parallel jumper not equalizing.

**A2 72.8 W / B4 71.9 W:** not added to A3. Candidate is **T2 Renogy idle** (30A RV unplugged). Confirm which clamp is on which inverter.

## What is still open

1. **MQTT** for Victron chargers 2 and 3 (MAC + 32-hex Instant Readout keys) so KU does not rely on 2x scaling. See [DEVICES.md](DEVICES.md#victron-bluetooth).
2. **Battery 2 SoC** -- VictronConnect capacity **230 Ah**. 14:53 **91.7% / -15.4 Ah** fits. 14:10 **44.4%** did not.
3. **Do not** move charger negatives onto BATTERY MINUS. Optional: a SmartShunt as a Victron **DC energy meter** on one circuit ([operation 5.8](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)).
4. **T2-KU jumper** -- both poles, size, lugs. Goal under KU load: T2 and KU **within ~0.05 V**. Victron one-bank layout is a **single** shunt after the packs are truly paralleled.
5. **EM16 map** -- confirm A3/B2 = KU trailer, A2/B4 = T2 30A / idle inverter (or something else).
6. **PWM** -- Voyager lithium **24 V** setting; optional HA/meter so it is not invisible in `PV_victron`.
7. **11:33 shunt BLE** recovered by 14:10.

## Related

- [DEVICES.md](DEVICES.md) -- add the two silent MPPTs
- [SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md) -- emergency **dolly cart** (2x 24 V 100 Ah); not T2/KU
- Renogy [Voyager 20A PWM 12/24](https://www.renogy.com/products/new-edition-voyager-20a-pwm-waterproof-solar-charge-controller) -- lithium voltage is a manual set
- [ALFA_CLUSTER_INTEGRATION.md](ALFA_CLUSTER_INTEGRATION.md)
- Victron SmartShunt [installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html), [operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)
- LiTime [24V 230Ah](https://www.litime.com/products/24v-230ah-truck-lithium-battery) -- 25.6 V, 230 Ah, 5888 Wh, charge 28.8 V +/- 0.4 V
