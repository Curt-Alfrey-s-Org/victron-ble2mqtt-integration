# 24 V solar -- watt in vs watt out

**Dates of log:** 10 Sep 2026, **11 Sep 2026**, and **15 Sep 2026** (America/New_York).  
**Solar charging window (this site, 11 Sep):** **09:30-16:00 ET only.** Outside that window the arrays are not charging; the two Renogy inverters run from their LiTimes (and the batt jumper, if it is sharing). Do not treat a 16:00+ MPPT watt reading as a full-day average.  
**Meters:** Home Assistant **Solar** (Victron BLE + Sungold USB Modbus via Pi4 MQTT on `.105`) and **Refoss** EM16.  
**HA host:** alfa-ai [HOMEASSISTANT_105_OPERATOR.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOMEASSISTANT_105_OPERATOR.md).  
**Idle cluster watts:** alfa-ai [CLUSTER_IDLE_POWER.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/CLUSTER_IDLE_POWER.md).

This is the **corrected** record of a live power-balance pass. Early chat inferred a Sungold PV path, added EM16 A3+B2, and treated the site as **one** Renogy. Adding A3+B2 is still wrong. The one-inverter model is still wrong (see [Layout](#layout-operator-2026-09-11)). **15 Sep:** Sungold Modbus is live on Solar. EM16 A3/B2 match Sungold **AC input** (not KU Renogy). That is the path that closes conversion loss. T2/KU Victron math stays on the shunts + MPPT; do not reuse 10-11 Sep A3 as trailer load in a 15 Sep shot.

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

**Solar-flow Overview (operator 17 Sep 2026):** the local GX-style page
([SOLAR_FLOW_DASHBOARD.md](SOLAR_FLOW_DASHBOARD.md)) shows **data tiles** for
Sungold, KU MPPT 1 / MPPT 2 / PWM, and both Renogy inverters. Physics is unchanged on **D/C**: Sungold stays
off T2/KU battery negatives. **A/C:** Sungold **UTI / A/C INPUT** is in the **Sungold cart lane**
(cord from the KU trailer outlet), **not** in the KU A/C / breaker lane. KU A/C lane:
panel → B3 → outlet → vent fan. PWM and Renogy
inverters stay **unmetered** in HA (registry has Sungold MQTT; **no** Renogy/PWM entities).
Do not merge Sungold D/C into T2/KU. Do not print 2× T2 watts as live KU Victron.
Dashboard hop policy: KU Renogy tile shows **0 W** (no HA inverter entity; never `-- W`).
**T2-KU jumper** on the Overview is an **estimate** (`solar_W - T2_Renogy_W - batt1_W`,
signed; T2 Renogy **0 W** while idle). Negative Battery 1 W with idle T2 Renogy means
current is leaving T2 through the jumper toward the KU bus (KU Renogy / trailer A/C),
not into the T2 RV outlet. The SmartShunt still does **not** measure jumper amps
([operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)).
**A3** = panel **hot leg** (`path-ku-renogy-panel`, \|A3\|). When A3 shows load, **every
downstream hop** on that path carries the same magnitude until the outlet split (panel →
B3 → outlet). **B3** = breaker feeding the trailer outlet (`path-panel-b3` / `path-b3-outlet`).
**UTI hop** (`path-outlet-uti`, `path-sg-uti-sph`) uses **`utiHopW`** (passthrough — not A3).
**Vent fan** = residual on the outlet split; **load**, not loss. **Dump loads** (Morningstar diversion; not "soak"): fed from
**Sungold A/C out** (SPH INV OUTPUT / `node-sg-acout`,
`sensor.sungold_sph302480a_load_active_power` per
[reprint §4.1](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf)), not
from KU Renogy. Sim dump loads use `path-sim-*` only (sim-plug sum or **0 W**) -- branch
starts at Sungold A/C out, never A3/B3/UTI. Do **not** add A3+B2. Do **not** use A3 as
`ha_load_entity`. See [SOLAR_FLOW_DASHBOARD.md](SOLAR_FLOW_DASHBOARD.md).

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
| EM16 A3 | **Panel hot leg** (16 Sep evening) | Feeds cargo-trailer outlets through the panel. **15 Sep:** same 10.40 A as Sungold `AC INPUT` (~1190 W). **Do not add B2** (B2 is the return of A3). 10-11 Sep shots used A3 as KU trailer AC -- do not mix those tables with 15 Sep. |
| EM16 B3 | **Sungold-outlet breaker** (16 Sep evening) | Breaker the Sungold cord is plugged into. Hop W on `path-panel-b3` when numeric; else fall back to \|A3\| while Sungold is the only outlet load. |
| EM16 B2 | return of A3 (opposite sign) | **15 Sep:** -1189.9 W vs A3 1190.2 W. Branch/return on that leg, not a second load. |
| EM16 A2 / B4 | unconfirmed | **~73 / 72 W** at 14:10-14:53; **0.0 W** at 16:11 and **15 Sep 15:53**. Candidate: **T2 Renogy idle** (no RV). Do not add to A3. |
| EM16 C1-C6 | unused CTs | **15 Sep:** ~2.0 V / 0 A / 0 W. Empty channels, not loads. |
| Sungold SPH302480A | cart | Emergency dolly. **2x 24 V 100 Ah LiTime in parallel.** USB sidecar on ([SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md)). Not on T2/KU DC. **15 Sep** AC-in vs battery-in vs AC-out is the loss close. |

### Parallel jumper (T2 RV unused)

The jumper is **not** "these two packs were always one bank." It is there so T2's charger can help KU while the T2 RV outlet is empty.

Victron's one-bank diagram is still: all battery negatives on a bus, **one** shunt, chargers/loads on SYSTEM MINUS ([installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html)). Two shunts plus a jumper will not show batt-to-batt amps.

If the jumper were low-R on **both** poles, T2 and KU voltages would stay within tens of millivolts. They did not:

| Shot | T2 V | KU V | Split |
|------|------|------|-------|
| 11 Sep 11:33 | 29.1 | 29.1 | 0.0 V |
| 11 Sep 14:10 | 28.5 | 26.5 | **2.0 V** (KU HVAC+cluster) |
| 11 Sep 14:53 | 28.5 | 26.6 | **1.9 V** (KU HVAC+cluster) |
| 11 Sep 16:11 | 27.2 | 27.0 | **0.2 V** (cluster only; sun done) |
| 15 Sep 15:53 | 26.0 | 25.6 | **0.4 V** (KU DC ~803 W; A3 is Sungold AC-in, not KU AC) |

Split depends on KU load. Under **HVAC+cluster (~720 W)** size overnight as **KU 230 Ah / 5.9 kWh** -- T2 sits behind a weak jumper. Under **cluster only (~279 W)** the buses were within **0.2 V**; T2 at 100% can share if that holds. Nameplate 2P **460 Ah / ~11.8 kWh** only if voltages stay matched under the load you run all night.

Each shunt capacity in VictronConnect: **230 Ah**. 14:53 KU **91.7% / -15.4 Ah** is 15.4 / 230 = **6.7%** used (implied **93.3%**). 16:11 **85.4% / -33.7 Ah** is 33.7 / 230 = **14.6%** used (implied **85.4%**). The ~185 Ah guess is retired.

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

Charge-state **bulk** on the reporter means it is still pushing current. **Absorption** means it has reached the absorb voltage and current is tapering. LiTime 24 V 230 Ah charge is **28.8 V +/- 0.4 V** (recommended **28.4-29.2 V**) -- T2 **29.1 V** then **28.5 V** matches that. KU **SoC 0%** at ~27-29 V was unsynced. 14:53 **91.7% / -15.4 Ah** and 16:11 **85.4% / -33.7 Ah** fit **230 Ah**. T2 **28.5 V** vs KU **26.6 V** at 14:53 is the jumper not equalizing under HVAC+cluster. At 16:11 (cluster only) T2 **27.2 V** vs KU **27.0 V**.

**16 Sep 2026 -- SoC still unsynced:** do not use HA `state_of_charge` for dump-load or
dashboard control. Prefer shunt **V / A / W** and MPPT charge state. Victron
does not publish a voltage-to-SoC formula; unsynchronised SoC is `---` until
the monitor is synchronised when the battery is full
([operation 5.7](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)).
Operator: VictronConnect → Settings → Battery settings → **Synchronise** (or wait
for automatic sync at charged voltage + tail current + charged time). This repo
does not write SoC over MQTT/HA. Dashboard procedure:
[SOLAR_FLOW_DASHBOARD.md](SOLAR_FLOW_DASHBOARD.md#operator-synchronise-smartshunt-soc-victronconnect-only).

## Formulas

```
PV_T2         = Solar-controller solar power (W)     # charger 1
PV_KU_victron = 2 * PV_T2                            # paper close only (10-11 Sep tables)
PV_KU_pwm     = unmetered                            # 2 ground suitcases + Renogy PWM
PV_victron    = 3 * PV_T2                            # three identical Victron strings; not live tiles
Shunt_T2      = Battery 1 power (HQ2239CQYT2)
Shunt_KU      = Battery 2 power (HQ2239JTRKU)
AC_trailer    = EM16 A3 magnitude                    # 10-11 Sep only: KU Renogy path
```

`PV x3` / `2 * PV_T2` is a **historical paper close**, not live telemetry. Do **not** print 2x T2 as a KU Victron reading on Solar flow.

### KU Victron + PWM residual (not a live tile)

SmartShunt Battery 2 is **net** of KU chargers 2+3 + PWM + jumper minus KU Renogy DC
([operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html):
+charge / -discharge):

```
batt2_W ≈ KU_PV_DC + jumper_into_KU − KU_Renogy_DC
KU_PV_DC ≈ batt2_W − jumper_into_KU + KU_Renogy_DC
jumper_into_KU ≈ solar_W − T2_Renogy_W − batt1_W   # + = T2 to KU; T2 Renogy 0 W while idle
```

**Live HA cannot clamp `KU_Renogy_DC`.** There is no inverter DC entity. EM16 A3 is trailer
**A/C** (Sungold + vent). That A/C is still the KU Renogy **load**: if A3 is 25 W, Battery 2
shows **load 25 W** and the Battery 2 to KU Renogy hop is **25 W**, not the SmartShunt
net (charge +276 W is storage, not inverter draw).
Inverter **DC in >= AC out**; do not invent efficiency. Ledger
`ku_renogy_ac_est_w` = |A3| (or |B3| when that breaker is the outlet path).
`ku_unmetered_pv_est_w` = `batt2_W − jumper_W + ku_renogy_ac_est_w` is a **combined
lower bound** only (`kind=ac_lower_bound`). Example: batt2 **276 W**, jumper
**−75 W** (KU→T2), load **25 W** → KU_PV est **376 W**, not
`(276+25)/3`. Equal **1/3 by suitcase count** (`ku_charger_equal_share_w`) is the
display split for two Victron MPPTs and one PWM when all six panels see the same
sun. Do **not** use it as dump-load `ha_solar_entity`. If A3 is missing, the
residual stays **None** (do not substitute 0 for the inverter).

**Dashboard:** KU MPPT 1, KU MPPT 2, and KU PWM tiles show that equal-share
**est.** (solid T2-style cards; subtitle **est.**). Combined KU PV est stays in the sidebar. KU Renogy
tile and Battery 2 **load** use the A3 A/C estimate. Shunt watts stay on
the Battery 2 node. **Do not** use dashed empty charger bricks.

**Split** into two MPPT vs PWM is not measured. Panel counts (2+2+2 suitcases)
are the equal-share assumption. Victron: PWM pulls the array near Vbat
while MPPT holds MPP
([Which solar charge controller: PWM or MPPT?](https://www.victronenergy.com/upload/documents/Technical-Information-Which-solar-charge-controller-PWM-or-MPPT.pdf)).
A 25 C worked example is **81 W PWM vs 100 W MPPT** (19% less). SmartSolar manuals
say **up to 30% more** harvest vs PWM in changing cloud
([features](https://www.victronenergy.com/media/pg/Manual_SmartSolar_MPPT_100-30__100-50/en/features.html)).
The same PWM/MPPT paper shows the MPPT advantage **vanishes at 75 C cell temperature**.
There is **no** single site derate to apply. Do not invent one.

**Dashboard / dump-load:** charger tiles are **est.** (unmetered), not live HA.
Combined A/C lower bound is **not** `ha_solar_entity`.
Ledger `ku_unmetered_pv_est_w` is **None** without A3; with A3 it is the combined
lower bound above.

**Sungold cart (15 Sep, AC charge, PV = 0)** -- LCD names from the SPH302480A manual ([reprint](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf) §4.1). `INPUT BATT` is battery **input** power; `INV OUTPUT LOAD KW` is AC load; `AC INPUT` is mains. HA **Output mode** `4` is not in the sidecar lookup (0-3 only) -- leave it as the raw integer ([SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md)).

```
SG_AC_in   = utiHopW(SG_grid V×A, SG_load_active_power)   # passthrough; do NOT use A3
SG_batt_in = Sungold battery input power       # LCD INPUT BATT KW (Boost charge = charging)
SG_AC_out  = Sungold load active power         # LCD INV OUTPUT LOAD KW (includes Pi4 ~5 W live)
SG_PV      = Sungold PV output power
trailer_outlet_W = |EM16 B3| if B3 >= 0.5 W else |EM16 A3|
vent_fan_W = max(0, trailer_outlet_W - utiHopW)   # sibling on KU trailer outlet; load not loss
SG_loss    = (SG_AC_in + SG_PV) - SG_batt_in - SG_AC_out
```

**`utiHopW` (17 Sep):** let `grid_w = SG_grid V × A`. If `grid_w` ≥ 0.5 W, use `grid_w`.
Else if `SG_AC_out` ≥ 0.5 W (Pi4 on A/C out), UTI must show at least the power feeding
that load (use `SG_AC_out` plus a small conversion allowance — do not show **0 W** on UTI
while A/C out is ~5 W). Never substitute \|A3\| for UTI hop W.

**A3 downstream (17 Sep):** when \|A3\| ≥ 0.5 W, KU Renogy → panel → B3 → outlet hops
display that magnitude until the split; vent and UTI branches split from `trailer_outlet_W`.

**Cart tare (17 Sep):** cart battery **0.1 A** (or similar) while SPH is on **UTI/grid**
is inverter DC standby, **not** pack discharge supplying Pi4. Do not treat as bus discharge
for dump-load math (alfa-ai `solar_dump.py` should ignore cart tare in UTI mode — gate
rewrite out of scope for this doc pass).

**Vent fan (17 Sep):** four speeds; live speed **1** (lowest). HA entity **TODO:**
search `fan.*` on `.105` ([REST states](https://developers.home-assistant.io/docs/api/rest/)).
Weather strip: **TODO** `weather.*` / `climate.*` ecobee — see
[SOLAR_FLOW_DASHBOARD.md](SOLAR_FLOW_DASHBOARD.md#weather-strip-outside-equipment-17-sep).

**Operator 17 Sep 2026:** Pi4 stays on SPH **A/C OUTPUT** (always-on Victron BLE radio; ~5 W
via `sensor.sungold_sph302480a_load_active_power`). Cargo-trailer **vent fan** shares the
**KU Renogy trailer outlet** with Sungold UTI (UTI tile in **Sungold cart lane**). EM16 A3
is that hot-leg **total** — **not** Sungold-only. Do not force A3 = SPH A/C in. Do not
use A3 as `ha_load_entity`.

When `SG_PV` is 0 this matches the 15 Sep LCD split on the hybrid itself. With PV present, add PV to the input side (reprint §4.1). Do not subtract `SG_PV` from the right-hand side.

## End-to-end path losses

Follow watts **in** and **out** of each hop starting at panel current/power (`P = V * I` when HA has no power entity). **Battery charge is storage, not conversion loss** (SmartShunt [+charge / -discharge](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)). Combined path loss is the sum of **metered conversion** hops only:

```
combined_losses_w = T2_MPPT_loss + SG_loss     # skip a hop when either end is missing
combined_path_losses_w = combined_losses_w + combined_vdrop_loss_w
surplus_after_path_losses_w = surplus_w - combined_path_losses_w
```

- **T2 MPPT:** `solar_W - charging_power - load_power` when charging_power is present. If charging_power is 0/missing while the T2-KU jumper estimate is flowing, skip MPPT conversion loss (the bus is carrying watts the charge sensor did not report).
- **T2-KU jumper:** `solar_W - batt1_W` (signed estimate; no clamp). Not a conversion hop.
- **KU Victron + PWM D/C:** tiles show equal-share **est.** of the combined
  lower bound (batt2 − jumper + |A3|); that estimate is **not** in `combined_losses_w`.
- Dump-load ON/OFF in alfa-ai and this dashboard uses `surplus_after_path_losses_w` ([Morningstar diversion §6.0](https://www.morningstarcorp.com/wp-content/uploads/technical-doc-diversion-manual-en.pdf) -- divert excess source energy after the battery is full).

Keep ledger code in `scripts/solar_watt_ledger.py` in sync with `alfa-ai/src/ops/solar_watt_ledger.py`.

### KU Victron + PWM residual (not a live watt)

Battery 2 is **net** of KU Victron 2+3 + PWM + jumper minus KU Renogy DC
([SmartShunt operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html):
+charge / -discharge; not each charger).

```
batt2_W    ≈ KU_PV_DC + jumper_into_KU − KU_Renogy_DC
KU_PV_DC   ≈ batt2_W − jumper_into_KU + KU_Renogy_DC
jumper_est ≈ T2_solar − T2_Renogy − batt1_W     # T2 Renogy 0 W while idle; + = T2 to KU
```

That combined residual is the only KU PV estimate, and **live HA has no KU Renogy DC
clamp.** EM16 A3 is trailer **A/C** (Sungold + vent) and is still the KU Renogy **load**:
Battery 2 **load** = hop Battery 2 to Renogy = |A3| (DC in >= AC out; no invented
efficiency). Do **not** paint SmartShunt net (e.g. +276 W charge) on that hop.
`ku_unmetered_pv_est_w` = batt2 − jumper + |A3| is a **combined lower bound** only.
If A3 is missing, residual stays **None** (do not substitute 0).
`(batt2 + load) / 3` **drops the jumper** (276+25 → 100.3 W each vs 376/3 ≈ 125 W).

**Split** of residual into two Victron MPPTs vs one PWM is **not measured**. Suitcase
counts (2+2+2) are the equal-share **est.** on the dashboard. Victron: PWM connects the array to
the battery so panel voltage sits near Vbat; MPPT holds the maximum power point
([Which solar charge controller: PWM or MPPT?](https://www.victronenergy.com/upload/documents/Technical-Information-Which-solar-charge-controller-PWM-or-MPPT.pdf)).
That paper's 25 °C worked example is **81 W PWM vs 100 W MPPT** (19% less). SmartSolar
manuals say **up to 30% more** harvest vs PWM in changing cloud
([SmartSolar MPPT 100/30 features](https://www.victronenergy.com/media/pg/Manual_SmartSolar_MPPT_100-30__100-50/en/features.html)).
The same PWM-vs-MPPT paper shows the advantage **vanishes at 75 °C cell temperature**.
There is **no** single site derate to apply. Do not invent one.

**Dashboard / dump-load:** KU MPPT 1 / MPPT 2 / PWM tiles show equal-share **est.**
(solid cards, not live HA). Do **not** print 2× T2 as a KU Victron reading. Do **not** paint residual
watts as live HA W. `ha_solar_entity` stays the T2 reporter only. The watt-ledger hop
`ku_victron_pwm` stays unmetered and is **not** in `combined_losses_w`. Vent fan and UTI
passthrough are **loads**, not conversion losses. Historical
10-11 Sep tables still use `PV x3` as a paper close, not live telemetry.

Voltage drop (D/C vs A/C kept separate; never 24 V minus 120 V):
[Victron Wiring Unlimited §2.7](https://www.victronenergy.com/media/pg/The_Wiring_Unlimited_book/en/theory.html)
V = I×R, cable loss P = I²R. With both-end voltages, ΔV = V_up − V_down and
P_drop ≈ |ΔV × I|. No AWG/length guesses. Jumper has ΔV when both shunts report
voltage but **no jumper current clamp**, so vdrop watts stay incomplete on that hop.

```
combined_vdrop_v     = sum |ΔV| on metered D/C hops
combined_vdrop_ac_v  = sum |ΔV| on metered A/C hops
combined_vdrop_loss_w = sum |ΔV × I| when I is metered
combined_path_losses_w = combined_losses_w + combined_vdrop_loss_w
```

**Dashboard sidebar (Losses block):** only the **W** rows in that block sum to **Total path losses**.
Conversion + vdrop loss = path losses (example: 3 W + 3 W = 6 W). **Vdrop D/C** and
**Vdrop A/C** are nested volt readings under vdrop; do not add 0.1 V + 1.8 V into the W
total. Vent fan, KU Renogy A/C est., UTI passthrough, dump plugs, Pi4, and surplus lines
live outside Losses ([SOLAR_FLOW_DASHBOARD.md](SOLAR_FLOW_DASHBOARD.md)).

### Inbound amps per battery (display-only)

Each SmartShunt reports **net** pack current (+charge / −discharge per
[operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)).
The dashboard also shows **in from sources**: a sum of **inbound** branch
currents derived from hop watts already on the diagram, **not** a replacement
for shunt A.

Electrical identity (DC steady state): **P = V × I** (SI brochure; same relation
in Victron [Wiring Unlimited §2.7](https://www.victronenergy.com/media/pg/The_Wiring_Unlimited_book/en/theory.html)).
For each inbound branch into a pack:

```
I_in = |P_in| / V_shunt     when P_in > 0 and V_shunt > 0
```

| Battery | Inbound branches (W source) | Notes |
|---------|----------------------------|-------|
| **T2 (Battery 1)** | T2 BlueSolar MPPT → pack (`mpptToBattHopW`); jumper when **KU→T2** | Jumper est. signed: **positive = T2→KU** counts on **KU only**; **negative = KU→T2** counts on **T2 only**. |
| **KU (Battery 2)** | Equal-share **est.** W for MPPT 1, MPPT 2, PWM (`kuEqualShareW` each); jumper when **T2→KU** | KU charger A = est. W / KU shunt V, labeled **est.** Loads (Renogy A/C, vent, dump) are **outbound**, never in the inbound sum. |

**Total in A** = sum of listed inbound branch amps (one source → total equals that
branch). Idle or discharge-only → **0 A** inbound (do not treat negative shunt A
as inbound). Shunt line stays **“… shunt net”**; **Total in** is separate.

Do not add A3+B2 or A2+A3. PWM is **not** inside `PV_victron`. 10-11 Sep snapshot tables still use `PV x3` for the three Victron strings and A3 as trailer AC.

Expect BLE fields from different advertisements to disagree by a few watts. A3 and B2 can differ by a few watts (calibration / not simultaneous). Sungold I x V vs the power tile can differ a few percent (poll vs tile refresh).

## Corrections

| Wrong (early chat) | Correct |
|--------------------|---------|
| One Renogy 2000 W for the whole site | **Two** Renogy 2 kW inverters: T2 -> 30A RV (unplugged); KU -> ATS -> trailer. Cluster AC is on **KU**. |
| Parallel jumper = one 460 Ah bank since day one | Jumper is on because **T2 RV is unused**. **~2 V** split under HVAC+cluster; **0.2 V** at cluster-only (16:11). Count T2 only when voltages stay matched under that night's load. |
| All PV = 3 x Victron reporter | Three Victron strings yes; **plus** 2 suitcase panels on **PWM into KU** (not in HA). |
| ~720-940 W extra PV from a Sungold hybrid MPPT | Sungold is the **dolly cart** (2x 24 V 100 Ah), not on T2/KU. |
| Used = A3 + B2 (~1,380 W) | **Never add A3+B2.** 10-11 Sep: A3 trailer total, B2 branch. **15 Sep:** A3/B2 are the Sungold AC-input feed (same amps as `AC INPUT`). |
| A3 and B2 "two CTs on the same feed" as the only explanation | They read almost equal because they are on the **same leg**. Sign can flip (15 Sep B2 negative). |
| A3 is always KU Renogy / cluster idle | **15 Sep 15:53** A3 **10.4 A / 1190 W** matched Sungold AC in that day. **17 Sep:** A3 is trailer-outlet hot leg = SPH A/C in **plus** cargo-trailer vent fan. |
| Shunt 2 negative => the two silent MPPTs are fully on BATTERY MINUS | Shunt 2 is **KU net** (Victron 2+3 + PWM minus KU Renogy). |
| Shunt should show charger-to-inverter amps at float | Battery monitor shows **that LiTime** only. Chargers on the SYSTEM MINUS bus of that shunt is correct. |
| Battery 2 capacity ~185 Ah from 91.7% / 15.4 Ah | **230 Ah** LiTime. 15.4 / 230 = 6.7% used, implied **93.3%**. |

Battery 2 **consumed Ah** was stuck near **-579 to -598 Ah** with SoC **0%** through 11 Sep 11:33. At 14:10 it showed **44.4% / -12.4 Ah** (SoC still wrong vs 230 Ah). At 14:53 it showed **91.7% / -15.4 Ah / 956 min remaining** while still discharging. **15.4 Ah of 230 Ah** is **6.7%** used (**93.3%** implied). At 16:11 **85.4% / -33.7 Ah** is **14.6%** of 230. Prefer voltage, current, and power when % and Ah disagree.

**Overnight energy (17.5 h dark, 09:30-16:00 charge window):** two KU AC operating points from **10-11 Sep A3** (trailer). PWM helps KU only while the sun is up. **Do not** use 15 Sep A3 (~1190 W Sungold AC-in) in this table.

| Mix | A3 | Dark-hours energy | KU 5.9 kWh pack | Jumper under that load |
|-----|----|-------------------|-----------------|------------------------|
| HVAC + cluster (14:53) | ~720 W | **~12.6 kWh** | about half a night | **~2 V** split -- T2 not sharing |
| Cluster only (16:11, fan+Midea off) | **~279 W** | **~4.9 kWh** | covers tonight (KU was **~5.0 kWh** left at 85%) | **0.2 V** -- can share if it holds |

A working jumper adds T2's **5.9 kWh** (~11.8 kWh nameplate, ~9.4 kWh at 80%). That still misses **12.6 kWh** at a sane DoD. It is spare at **4.9 kWh**. See [Now vs double load](#now-vs-double-load).

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
| **16:11** | Fan+Midea **off**; cluster up; **past 16:00** window | **35.0** | **105** | **+187.3** | **-129.6** | **+58** | **278.7** | **277.8** |

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

### 16:11 close (fan and Midea off; sun done)

Operator shed the fan and Midea. **Past the 09:30-16:00 window.** Reporter **bulk**, **1.5 A** at **27.0 V**, solar **35.0 W**, yield **1,445 Wh** (+105 Wh since 14:53, ~81 W average as the array died). Do **not** treat 35 W or `PV x3 = 105` as a daytime average, and do **not** close a 3x DC balance at dusk (chargers 2/3 and PWM will not track charger 1).

Shunt 1 **+187.3 W / 6.9 A** at **27.2 V / 100%** -- internally consistent (6.9 x 27.2), but **does not track** the MPPT (**1.5 A / 35 W**). All afternoon they matched. Same class of warning as 11:33: do not treat shunt 1 vs MPPT as a closed charger-track. Remaining Unknown.

Shunt 2 **-129.6 W / -4.8 A** at **27.0 V**, SoC **85.4%**, consumed **-33.7 Ah**, remaining **3,223 min**. **-33.7 / 230 = 14.6%** used (implied **85.4%**). A3 **278.7 W** (2.4 A, PF -1.0, 34,668 Wh this month). B2 **277.8 W** / 2.4 A / 35,044 Wh. **A2 0.0 W**, **B4 0.0 W** (month totals still ~2,229 / 2,113 Wh).

A3 dropped **713 to 279 W** (**-434 W**). That is more than the 10 Sep fan+dehum shed (**688 to 418 = ~270 W**). Compressor likely on hard, or something else went with them. Remaining **279 W** is cluster + KU Renogy. 10 Sep 14:57 same mix was **~418 W**.

Jumper split **0.2 V** (27.2 vs 27.0) vs **~2 V** at 14:53. Light KU load, buses close.

Do not use shunt 1 **+187 W** as T2 solar (MPPT was **35 W**). The 11:33 `*` footnote above is a different BLE bug.

## Snapshot log (15 Sep 2026)

**~15:53 ET.** Still inside the **09:30-16:00** charge window. Sungold USB Modbus is live on Solar. **Do not** close T2/KU with A3 in this shot -- A3/B2 amps match Sungold **AC input**, not KU Renogy.

Govee **Thermo-Hygrometer-CAAF6F** tiles **Unknown** is expected (dead cells). It is not Instant Readout or Pi4 Theengs failure ([DEVICES.md](DEVICES.md)).

### Sungold cart (AC charge, PV = 0)

HA names = LCD fields ([SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md), [SPH reprint §4.1](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf)).

| Tile | Value |
|------|-------|
| PV input / PV output / PV output power | **0 V / 0.0 A / 0 W** |
| Remaining battery | **68%** |
| Battery input / Input battery current / Battery input power | **27.3 V / 39.4 A / 1,042 W** |
| Charge state | **Boost charge** |
| AC input V / A / Hz | **115 V / 10.40 A / 60 Hz** |
| Load active / AC output load / Output load V | **10 W / 0.10 A / 118 V** |
| AC output frequency | **50 Hz** (tile as published; AC input is 60 Hz -- do not invent a mode from that) |
| Output mode | **4** (raw; sidecar lookup is 0-3 only) |
| Fault | off / no reported error |

Refoss ([EM16](https://www.home-assistant.io/integrations/refoss/)): **A3 1,190.2 W / 10.4 A / 118.3 V**, PF **-1.0**, this month **58,526 Wh**. **B2 -1,189.9 W / 10.3 A / 118.6 V**, this month **58,684 Wh**. A3 current = Sungold **10.40 A**. **Do not add B2.** Other A/B channels **0.0 W** (A2 / B4 month totals still ~3,360 / 3,487 Wh). **C1-C6 ~2.0 V / 0 A / 0 W** (unused CTs).

Sungold has no HA **grid power** tile (holding `0x023A` rejected). Use **|A3|** as `SG_AC_in`. Check: 10.40 A x 115 V = **1,196 W** vs A3 **1,190 W**. Battery I x V: 39.4 x 27.3 = **1,076 W** vs tile **1,042 W**. Load I x V: 0.10 x 118 = **12 W** vs tile **10 W**.

| | W |
|---|---|
| SG_AC_in (\|A3\|) | 1190 |
| SG_batt_in (INPUT BATT KW) | 1042 |
| SG_AC_out (INV OUTPUT LOAD KW) | 10 |
| SG_PV | 0 |
| **SG_loss** (AC_in - batt_in - AC_out - PV) | **138 (~12% of AC_in)** |

That 138 W is Sungold conversion / wiring on the **cart** (mains to battery charge plus a 10 W AC load). It is **not** T2/KU inverter loss and **not** cluster idle. KU DC was still **~803 W** discharge with **no** other EM16 channel carrying that AC -- trailer/cluster AC is unmetered in this shot.

### T2 / KU Victron (same timestamp; A3 is not trailer AC)

| Piece | Value |
|-------|-------|
| BlueSolar (T2 charger 1) | **250.0 W** PV, **9.6 A**, **25.6 V**, **bulk**, yield **1,440 Wh**, load output **0.0 A** |
| Battery 1 HQ2239CQYT2 | **+26.6 W / 1.3 A / 26.0 V / 100% / 0.0 Ah**, remaining 14,400 min |
| Battery 2 HQ2239JTRKU | **-803.4 W / -31.4 A / 25.6 V / 91.9% / -17.9 Ah**, remaining **343 min** |

HA Battery 2 **Power** tile may show **803.4 W** without a minus; current is **-31.4 A**, so this is **discharge**. 31.4 x 25.6 = **804 W**. **-17.9 / 230 Ah** = **7.8%** used (implied **92.2%** vs tile **91.9%**).

T2 MPPT **250 W** vs shunt 1 **+27 W**: about **223 W** is leaving the T2 pack path (jumper / other). Do **not** 3x-close against A3. Chargers 2/3 still silent; PWM still unmetered.

Jumper split **0.4 V** (26.0 vs 25.6) under ~803 W KU DC -- still not a true parallel bank.

## Now vs double load

Bottleneck is **KU overnight kWh**, not inverter watts (KU Renogy is 2 kW). Charge window **09:30-16:00** (~6.5 h sun, **17.5 h** dark). Extra panels on **T2** do not feed the trailer overnight unless the jumper equalizes **under that night's load**.

**Cluster only (this shot, ~279 W):** dark hours **~4.9 kWh**. KU had **~5.0 kWh** left at 85%. **Tonight fits on KU alone.** Doubling *this* load (~560 W) is **~9.8 kWh** dark -- more than one 5.9 kWh pack, about even with a working jumper at 80% (~9.4 kWh). Needs the jumper to hold at 560 W (unproven; it failed at 720 W) or more **KU** storage. KU PV still helps only in the 6.5 h window.

**HVAC + cluster (~720 W, 14:53):** dark hours **~12.6 kWh**. KU **5.9 kWh** is about half a night. Jumper was **~2 V** -- do not count T2. Doubling *that* mix (~1.4 kW AC) is **~25 kWh** dark. Inverter still OK (~1.4 kW on 2 kW). Need **~2x PV and ~2x battery on KU**, not on T2. Generator on the ATS is the overnight backup until storage matches.

**Short:** fan+Midea off changes tonight from "KU cannot finish the night" to "KU can." It does not change the 720 W HVAC+cluster math if those loads come back. Doubling cluster-only is a jumper-or-more-KU-Ah problem. Doubling HVAC+cluster is still 2x KU solar and 2x KU storage.

## What is still open

1. **MQTT** for Victron chargers 2 and 3 (MAC + 32-hex Instant Readout keys) so KU does not rely on 2x scaling. See [DEVICES.md](DEVICES.md#victron-bluetooth).
2. **Battery 2 SoC** -- VictronConnect capacity **230 Ah**. 14:53 **91.7% / -15.4 Ah**, 16:11 **85.4% / -33.7 Ah**, and 15 Sep **91.9% / -17.9 Ah** fit. 14:10 **44.4%** did not.
3. **Do not** move charger negatives onto BATTERY MINUS. Optional: a SmartShunt as a Victron **DC energy meter** on one circuit ([operation 5.8](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)).
4. **T2-KU jumper** -- both poles, size, lugs. Goal under the load you run overnight: T2 and KU **within ~0.05 V**. 16:11 was **0.2 V** at 279 W AC; 14:53 was **~2 V** at 720 W AC; 15 Sep was **0.4 V** at ~803 W KU DC. Victron one-bank layout is a **single** shunt after the packs are truly paralleled.
5. **EM16 map** -- **15 Sep:** A3/B2 = Sungold AC-in (10.40 A match). KU trailer AC has **no** live EM16 channel in that shot (KU DC ~803 W). A2/B4 **0 W** at 15:53 (month totals still ~3,360 / 3,487 Wh). C1-C6 unused. Re-clamp KU AC to close trailer loss the same way as the cart. 10-11 Sep tables still treat A3 as KU trailer -- do not mix.
6. **PWM** -- Voyager lithium **24 V** setting; optional HA/meter so it is not invisible in `PV_victron`.
7. **11:33 shunt BLE** recovered by 14:10. **16:11 shunt 1 vs MPPT** still mismatched -- do not close that pair.

## Related

- [SOLAR_ARRAY_SOLARK.md](SOLAR_ARRAY_SOLARK.md) -- **separate** planned 48 V island (6 x ~440 W + Sol-Ark + Discover AES 900-0062). Not this T2/KU plant.
- [PI4_BMS_SOFTWARE.md](PI4_BMS_SOFTWARE.md) -- planned Pi4 battery **supervisor** (shunt / MQTT). Does not replace pack BMS and does not mix this 24 V plant with the 48 V island.
- [DEVICES.md](DEVICES.md) -- add the two silent MPPTs
- [SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md) -- emergency **dolly cart** (2x 24 V 100 Ah); not T2/KU; 15 Sep AC-in vs battery-in vs AC-out loss ~12%
- Renogy [Voyager 20A PWM 12/24](https://www.renogy.com/products/new-edition-voyager-20a-pwm-waterproof-solar-charge-controller) -- lithium voltage is a manual set
- [ALFA_CLUSTER_INTEGRATION.md](ALFA_CLUSTER_INTEGRATION.md)
- Victron SmartShunt [installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html), [operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)
- LiTime [24V 230Ah](https://www.litime.com/products/24v-230ah-truck-lithium-battery) -- 25.6 V, 230 Ah, 5888 Wh, charge 28.8 V +/- 0.4 V
