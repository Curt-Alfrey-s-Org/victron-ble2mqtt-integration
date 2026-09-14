# New island -- 10 x KB Solar 450 W + Sol-Ark 12K-2P-LL + 1 AES (planning)

**Status:** planning (11 Sep 2026). Not installed. **Off-grid.** Expand later.

**Isolation (hard):** this is a **new 48 V / 120-240 V plant**. It is **not** wired to T2, KU, the Victron MPPTs, the Renogy 2 kW inverters, the PWM string, the batt jumper, or the Sungold cart. Those stay in [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md). **Do not** series the two LiTime 24 V 230 Ah packs onto this bus and **do not** parallel that string with the AES (see below). Do not AC-parallel this LOAD with a Renogy ATS without a designed interlock.

**Starting BOM (operator, 11 Sep evening):** 10 PV + **1** AES + 12K-2P-LL, then expand. The checkout cart in that session showed **qty 2** AES -- follow the **1 AES** start unless you meant to buy the second module now.

| Piece | Day one |
|-------|---------|
| 10 x **KB Solar KBS-450** monofacial, black frame | **4,500 W STC**. Not the earlier 6 x ~440 W bifacial sketch. |
| Sol-Ark **Limitless 12K-2P-LL** | 10 kW AC from batteries, 96 W idle. Off-grid until the operator says otherwise. |
| Discover AES RACKMOUNT **48-48-5120** (900-0062) | **One** 51.2 V / 5.12 kWh module |

Licensed electrician + AHJ. This file is vendor limits and first-array math, not a permit set.

## Official manuals

| Item | Source |
|------|--------|
| Sol-Ark residential SKUs (no "10K") | [Residential hybrids](https://sol-ark.com/residential-energy-solutions/) -- 8K-2P, 12K-2P, **12K-2P-LL**, 15K-2P, 18K-2P |
| **12K-2P-LL** (the "~10K": 10 kW from batteries, 12 kW to grid) | [Product](https://sol-ark.com/residential-energy-solutions/limitless-12k-2p-ll-hybrid-inverter/), [datasheet PS-00045](https://sol-ark.com/wp-content/uploads/2026/05/12K-2P-LL_Datasheet_Rev3_PS-00045_14July2026.pdf) |
| **8K-2P** (8 kW AC, 60 W idle, 2 MPPT) | [Datasheet](https://www.sol-ark.com/wp-content/uploads/2024/06/SK150-0005-002-8K-2P-N-EN-Datasheet.pdf), [manual](https://www.sol-ark.com/wp-content/uploads/2024/06/SK140-0005-002-8K-2P-N-EN-Manual.pdf) |
| 12K-2P family stringing / GEN / 48 V only | [12K-2P install / user manual](https://sol-ark.com/wp-content/uploads/2024/06/SK140-0003-002-12K-2P-N-EN-Manual-1-1.pdf) |
| Sol-Ark + Discover AES closed-loop | [LV Battery Integration Guide](https://sol-ark.com/wp-content/uploads/2024/06/LV_Batt_Integration_Rev7_24March2026.pdf) (AES RACKMOUNT **48-48-5120-H** section), Discover [LYNK II / Sol-Ark](https://docs.discoverenergysys.com/805-0033-lynk-ii-installation-manual/release/sol-ark) (lists **48-48-5120** and **48-48-5120-H**) |
| AES module **900-0062** | [AES RACKMOUNT](https://discoverenergysys.com/products/lithium-batteries/aes-rackmount), [48-48-5120 electrical](https://discoverbattery.com/products/search/48-48-5120) |
| KB Solar **KBS-450** monofacial | [MODULE-KBS-450-MONO datasheet](https://cdn.enfsolar.com/z/pp/2025/1/dv61pm623hc5/module-kbs-450-mono-1.pdf) -- Voc **50.03 V**, Vmp **42.16 V**, Isc **11.29 A**, Voc tempco **-0.26 %/C**. [KB install manual](https://kb-solar.com/wp-content/uploads/2024/06/KB-Solar_Installation_Manual_PV_Module_V.2.1.pdf) |
| LiTime 24 V 230 Ah | [Product](https://www.litime.com/products/24v-230ah-lithium-battery) -- 25.6 V, 230 Ah, 5888 Wh, charge **28.8 V +/- 0.4 V**, max **2S / 4P**, identical packs only |
| Indoor water (gpcd) | Water Research Foundation REU2016 **58.6 gal/person/day** indoor, cited in EPA WaterSense Homes v2 supporting statement ([NEPIS P101E5MX](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P101E5MX.txt)) |
| Example 1.5 HP 230 V 1-ph motor | Franklin [2243009203GS](https://www.franklinwater.com/products/submersible-motors-and-control-boxes/4-inch-submersible-motors/4-inch-induction-motor/4-inch-3-wire-single-phase-models--sku-collection/2243009203gs/) -- FLA **10 A**, SFA **11.5 A**, FL efficiency **69%** (use **your** nameplate) |
| Sol-Ark motor/well surge (class) | [How to size a hybrid for surge](https://sol-ark.com/news/how-to-size-hybrid-inverter-for-surge-power/) -- example well **~1.5 kW run / 3-5 kW surge**; off-grid the inverter supplies inrush |
| 20 gal well tank drawdown | Amtrol Well-X-Trol [brochure](https://www.amtrol.com/wp-content/uploads/2025/08/MC10188-08_25_WXT-brochure.pdf) WX-202 **20.0 gal**: **6.2 / 5.4 / 4.7 gal** at 30/50, **40/60**, 50/70. ESP II = ~**2 min** run for pumps **3/4 hp or larger** |
| 4" motor start rate (Franklin class) | Franklin 4" encapsulated: max **20 starts/hour**, **3 min** between starts ([EU 4" motor manual](https://siurbliai.lt/wp-content/uploads/2024/05/4inch_manual_-std-308018402_rev23_102023.pdf)); confirm in US [2026 AIM](https://www.franklinwater.com/resources/franklin-aim) for this motor |

**SKU call on quotes:** **12K-2P-LL** if you meant 10 kW backup from batteries, or **8K-2P** if you want a smaller idle. Do not order a "Sol-Ark 10K".

**Grid vs this island:** Sol-Ark's [12K-2P-LL page](https://sol-ark.com/residential-energy-solutions/limitless-12k-2p-ll-hybrid-inverter/) calls it a **hybrid**: "On-grid, or Off-Grid". Operator did **not** choose utility. Size PV and AES as **off-grid**.

## Day one: 10 x KBS-450 + 1 AES + 12K-2P-LL (expand later)

That start is sized for the **well**, not for 24/7 servers. Extra panels do not add overnight kWh. One AES is still **5.12 kWh**.

| Day-one load | One AES 5.12 kWh? | 10 x 450 W harvest ~20.5 kWh (6.5 h x 0.70)? |
|--------------|-------------------|-----------------------------------------------|
| Well only (pump off 22:00-07:00) | **Yes** -- worst day ~3.7 kWh | **Yes**, large margin |
| Well + 24/7 servers 279-500 W | **No** -- dark 6.6-10.4 kWh | Day energy would fit; night would not |

**Expand later (order):** (1) **second AES** before any 24/7 cluster on this LOAD, (2) more PV / third AES after that, (3) bigger pressure tank whenever -- it is not delayed by the battery count.

**String ten KBS-450 on 12K-2P-LL** (startup **125 V**, rated **150-425 V**, **do not exceed 500 Voc** -- [datasheet](https://sol-ark.com/wp-content/uploads/2026/05/SA-12K-2P-LL_Datasheet_Rev1.1_PS-00045.pdf), [manual](https://sol-ark.com/wp-content/uploads/2026/05/12K-LL_Installation_Manual_MA-00057_Rev3_16July202.pdf)):

| Config | Voc STC | Verdict |
|--------|---------|---------|
| **10S** | **500.3 V** (10 x 50.03) | **No** -- already over **500 V** at 25 C, before NEC 690.7 cold. Damage risk. |
| 8S + 2S | 400 V + 100 V | **No** -- 2S will not start (under 125 V). |
| 6S + 4S | 300 V + 200 V | **Avoid** -- 4S Vmp can fall under the **150 V** rated window in heat. |
| **5S2P on one MPPT**, or **5S + 5S on two MPPTs** | 5 x 50.03 = **250 V** STC; Vmp **211 V**; 5S2P Isc **~22.6 A** (under 32 A / 60 A) | **Yes** -- parallel strings on one MPPT must share Voc ([quickstart](https://sol-ark.com/wp-content/uploads/2026/05/12K-LL_QuickStart_Rev2_6July2026.pdf)). Two MPPTs if the two rows do not share the same plane. |

Electrician still runs NEC 690.7 on site min temp with **-0.26 %/C**. Shipping address **SC** does not make 10S legal.

**Charge into one AES:** continuous charge **70 A**. At 55.2 V that is **~3.86 kW** into the pack ([48-48-5120](https://discoverbattery.com/products/search/48-48-5120)). 4.5 kW STC can exceed that at noon; closed-loop BMS / **Max A Charge** clips the battery. Surplus feeds the well (and any daytime LOAD). Off-grid, unused PV is curtailed -- that is normal on a full pack, not a reason to skip ten modules.

**Not in that cart (still required for a working closed-loop stack):** Discover **LYNK II 950-0025**, Sol-Ark pin adapter **950-0016-SLRK**, rack/Slimline (module is **IP20**), battery cables, PV/battery disconnects, RSD as the AHJ requires. Confirm the AES line is **48-48-5120 / 900-0062**, not a different Discover rack SKU.

## Do not parallel series LiTimes with the AES

Operator question: series the two existing LiTime 24 V 230 Ah packs (allowed **2S** of **identical** LiTimes -- [LiTime 24V 230Ah](https://www.litime.com/products/24v-230ah-lithium-battery)), then parallel that 51.2 V string with the AES on the Sol-Ark battery port to cover night kWh.

**Nameplate energy if they shared** would be ~11.8 kWh (2S LiTime) + 5.12 kWh AES = **~16.9 kWh**. That number is why it looks like a night fix. The manuals do not allow the mix, so it is **not** the night fix.

| Authority | What it says |
|-----------|----------------|
| Discover AES RACKMOUNT IOM 9.7 | Parallel modules must be the **same model** ([manual](https://discoverenergysys.com/s4x_files/resources/des-aes-rackmount-user-manual.pdf)). |
| Sol-Ark 12K-2P-LL | "Best practice to **not mix** battery banks of different makes, models, ages, or chemistry" -- can be **hazardous** ([install manual](https://sol-ark.com/wp-content/uploads/2026/05/12K-LL_Installation_Manual_MA-00057_Rev3_16July202.pdf)). |
| LiTime | Series/parallel only with **identical** brand, type, voltage, capacity, and BMS. AES is none of those. |
| Charge setpoints | AES bulk/float **55.2 / 53.6 V**, cutoff **48 V**. Two LiTime 24 V in series want **57.6 V +/- 0.8 V** charge. One inverter cannot follow both. Closed-loop LYNK only speaks for the AES; the LiTime bank is invisible. |

Closed-loop **BMS Lithium Batt = 00** would current-limit from the AES (70 A class) while a 200 A LiTime BMS sits on the same bus. Current hogging, AES breaker/BMS open, then the well inrush on the remaining pack.

Those two LiTimes are also **T2 and KU** today. Moving them here empties the 24 V plant. This chapter does **not** change [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md) -- T2/KU stay as documented until a real cutover is chosen.

**Night fix that the manuals allow:** a **second AES 48-48-5120** in parallel with the first (same model, LYNK daisy-chain), **or** the LiTime-only 2S bank below (no AES on this inverter).

## Brainstorm: LiTime 2S only (no AES) on the 12K-2P-LL

Operator (11 Sep): discard the AES to save money; series the two existing 24 V 230 Ah LiTimes as the Sol-Ark 48 V bank. **T2/KU are not edited here** -- this is energy/voltage math only. A real move would leave those 24 V buses without those packs.

LiTime allows **two identical** 24 V units in series ([24V 230Ah](https://www.litime.com/products/24v-230ah-lithium-battery)): **51.2 V**, **230 Ah**, **11.78 kWh** (2 x 5888 Wh). Sol-Ark 12K-2P-LL is a 48 V inverter, **43-59 V** ([install manual](https://sol-ark.com/wp-content/uploads/2026/05/12K-LL_Installation_Manual_MA-00057_Rev3_16July202.pdf)). LiTime is **not** on Sol-Ark's certified closed-loop list ([LV Battery Integration Guide](https://sol-ark.com/wp-content/uploads/2024/06/LV_Batt_Integration_Rev7_24March2026.pdf)) -- program **open-loop**, **Use Batt V**, **BMS Lithium Batt off**. Charge **56.8-58.4 V** (2 x 28.4-29.2 V). Set inverter cutoff **above** the BMS (stay at or above **43 V**; a **48 V** cutoff is a conservative 3.0 V/cell floor). Recommend charge **46 A (0.2C)** or up to **115 A (0.5C)** per LiTime; 10 x 450 W into an empty pack can exceed 46 A -- cap **Max A Charge** in that band, not 220 A.

**Night (17.5 h dark, 96 W idle).** Operator: **500 W is a max**, not a 24/7 floor. **400 gal/day is a max**, not every day. Use the KU cluster logs for typical: **~279 W** (11 Sep 16:11) and **~418 W** (10 Sep 14:57). Pump energy scales with gallons (400 gal ~1.35 kWh; a 293 gal indoor-class day is ~1.0 kWh).

| Night load | Dark kWh | Of 11.78 kWh | 24/7 on this bank? |
|------------|----------|--------------|-------------------|
| Well only (idle) | **1.68** | 14% | **Yes** |
| Typical cluster **279 W** + idle | **6.56** | 56% | **Yes** -- ~5.2 kWh left |
| Heavier day **418 W** + idle | **9.00** | 76% | **Yes** -- ~2.8 kWh left |
| **Max 500 W** all night + idle, pump in sun | **10.43** | 89% | **Yes, tight** -- ~1.35 kWh left |
| Max 500 W all night **and** max 400 gal from the battery after 16:00 | **~11.8** | ~100% | Empty at sunrise -- do not plan that stack every night |

**24/7 answer:** yes for well + servers on 2S LiTime, with 500 W / 400 gal as **peaks**. Typical nights sit near **279 W** and well under 400 gal -- that is about **half** the pack plus idle, not a 100% DoD every morning. A 500 W spike (decode, backup, extra hosts) is fine for minutes to a couple of hours; it is not the overnight average.

**500 W 24/7 fits this pack on a good night** if the well runs in the sun. If the pump's 1.35 kWh also comes from the battery after 16:00 **and** servers sit at 500 W all night, dark is **~11.8 kWh** -- empty at sunrise. Do not stack both maxima.

**Watts / surge:** 200 A continuous per string (series keeps Ah, not 400 A). 200 A x 51.2 V = **~10.2 kW** DC -- in the same class as Sol-Ark's 10 kW from batteries. 5 s peak **400 A**. Well ~1.6 kW run is easy; inrush still needs LRA vs 400 A / 5 s, and the 20 gal tank still cycles ~74 times/day.

**Not free:** no LYNK SoC, two BMS in series (equalize full charge before 2S), fuse/breaker on the 200 A path, LiTime charge **0 C to 50 C** (no heat on this SKU). 10-panel harvest (~20.5 kWh) can refill 11.78 kWh plus daytime loads on a good 6.5 h x 0.70 day.

## Compare: Sungold SPH10048P + 10 x SG550WM vs Sol-Ark 12K-2P-LL + 10 x 450 W

Operator Amazon listings (11 Sep 2026). Official SKUs: inverter **SPH10048P** ([product](https://sungoldpower.com/products/10kw-48v-split-phase-solar-inverter)), panels **SG550WM** ([product](https://sungoldpower.com/products/550-watt-monocrystalline-solar-panel), [datasheet](https://cdn.enfsolar.com/z/z/2025/2/p15lyv5b8r/182Mono550W-SG550WM-20250120.pdf)). Do not order the listing variants that bundle **SG48100P** batteries if the bank is LiTime 2S.

Same island: off-grid, 2S LiTime 11.78 kWh, well 240 V + servers 120 V, 500 W / 400 gal as peaks. Existing cart **SPH302480A** stays a **separate** 24 V / 120 V island -- SPH parallel rules require identical SPH 8/10k units, same battery, one AC source.

| | Sol-Ark 12K-2P-LL + 10 x 450 W | SPH10048P + 10 x SG550WM |
|--|-------------------------------|---------------------------|
| Inverter $ | ~3999 | **1580** |
| 10 panels $ | ~2200 (KBS-450 class) | **2790** (550 W) |
| STC / harvest (6.5 h x 0.70) | 4.5 kW / **~20.5 kWh** | 5.5 kW / **~25.0 kWh** |
| AC | 10 kW from batteries, 120/240 | **10 kW**, 120/240 |
| Surge | **24 kW / 10 s** off-grid (datasheet) | **20 kW** peak, **duration not in the parameter table**; FAQ also says keep motor surges **under 10 kW** |
| Motor | (well example 3-5 kW) | **6 HP** rated |
| Idle | **96 W** documented | **Not published** on the manufacturer parameter table |
| Max batt invert efficiency | **97.6%** | **92%** (product FAQ / parameter table) |
| MPPT | 3 x 32 A, start 125 V, 150-425 V, VOC **500 V** | **2 x 22 A**, 125-425 V, VOC **500 V** |
| Charge limit | Max A Charge to 220 A | Item 07 **0-200 A** (default 60 A) -- can cap LiTime at 46 A / 115 A |
| Enclosure | **IP65 / NEMA 3R** | **IP20 indoor** |
| UL | UL1741 3rd SB + IEEE 1547 (unused with no utility) | ETL **UL1741 for off-grid** -- not SB / 1547 |
| Warranty | **10 years** | Company policy 12/36 months; this SKU page **does not state years** |
| 10S array | **Illegal** (KBS-450 10S Voc 500.3 V at 25 C) | **Illegal** (SG550WM 10 x 49.70 = 497 V STC; Voc tempco **-0.35 %/C** -> ~558 V at -10 C) |
| Legal 10-module string | **5S + 5S** | **5S + 5S** (5S2P on one MPPT: Isc 28 A **> 22 A**) |

**Well + 279 W servers:** both inverters can run the amps. The 1.5 HP pump is not why you pick Sol-Ark.

**Night:** 279 W x 17.5 h = 4.88 kWh AC. At 97.6% that is ~5.0 kWh from the LiTimes plus 96 W idle (1.68 kWh) = **~6.7 kWh**. At 92% the same AC is ~5.3 kWh from the pack **before** idle. SPH idle is unpublished -- that is the wrong unknown on a 17.5 h island. Do not enable SPH energy-save (manual: AC **off** if load < 50 W for 5 min) -- servers are above 50 W, but a cluster reboot dip could still trip it.

**Recommendation for this island:** keep the **12K-2P-LL**. Spend the ~2400 inverter delta on **more LiTime kWh** (official 4P2S) if you want a cheaper path that actually helps night, not on SPH10048P. **Panels are separable:** 10 x SG550WM on Sol-Ark (5S+5S) is extra harvest (~+4.5 kWh/day) if the 62.4 lb / 89.7 x 44.8 in modules fit. Amazon weight 56.9 lb does not match the datasheet.

## Compare: SPH6548P + 10 x SG450WM vs 12K-2P-LL + 10 x KBS-450

Operator (13 Sep 2026): cheaper **6.5 kW 120/240** Sungold + **10 x Sungold 450 W**, ground mount, vs the Sol-Ark + KB 450 W stack. Same island (off-grid, well + servers, not T2/KU). Existing cart **SPH302480A** stays a separate 24 V / 120 V island.

Official SKUs: inverter **SPH6548P** ([product](https://sungoldpower.com/products/6500w-48v-solar-charge-inverter-parallel-wifi-monitor), [user manual data sheet](https://www.manualslib.com/manual/3551057/Sun-Gold-Power-Sph6548p.html)), panels **SG450WM** ([product](https://sungoldpower.com/products/450-watt-monocrystalline-solar-panel), [datasheet 2025-01-20](https://cdn.enfsolar.com/z/z/2025/2/1mvr7y571as4/182Mono450W-SG450WM-20250120.pdf)). Sol-Ark + KB as above.

This is **not** extra harvest. Ten 450 W modules are **4.5 kW STC / ~20.5 kWh** (6.5 h x 0.70) on **both** sides. The invoice win is the inverter (**$1150** list vs **$3999** 12K-2P-LL MSRP). Panel dollars depend on the 10-piece quote: KB cart was **~$2200**; SG450WM SKU page is **$899** with a **2PCS** package (~$4495 for ten if that is a 2-pack) vs pallet **$4950 / 32 = $155/ea** (32-count only).

| | SPH6548P + 10 x SG450WM | 12K-2P-LL + 10 x KBS-450 |
|--|-------------------------|---------------------------|
| Inverter $ | **1150** list | **3999** MSRP |
| STC / harvest | 4.5 kW / **~20.5 kWh** | 4.5 kW / **~20.5 kWh** |
| AC from batteries | **6.5 kW**, peak **13 kVA** | **10 kW**, surge **24 kW / 10 s** |
| 120/240 | Yes (item **68 = 180** on one unit) | Yes |
| Idle | **Not** in the parameter table | **96 W** |
| Max batt invert efficiency | **93%** | **97.6%** |
| Charge | Item 07 **0-140 A** (default 60 A) | Max A Charge to **220 A** |
| MPPT | **2 x 18 A**, 150-450 V, VOC **550 V** | **3 x 32 A**, 150-425 V, VOC **500 V** |
| Enclosure | **IP20 indoor** | **IP65 / NEMA 3R** |
| UL | ETL **UL1741 off-grid** (product page) | UL1741 3rd **SB** + IEEE 1547 |
| AC couple | Not in the SPH6548P manual | GEN, UL 1741 SA/SB source |
| Energy-save | DIS default; ENA kills AC if load **&lt; 50 W** for 5 min | n/a |
| Battery window | **40-60 V** | **43-59 V** |
| Ten-module size / weight | 75.2 x 44.7 in, **24.5 kg** datasheet; ~233 ft2 / **540 lb** | 83.0 x 41.3 in, 51.4 lb; ~238 ft2 / **514 lb** |
| Snow / wind published | Product table **2400 Pa** wind; snow Pa **not** on that table | Front **5400 Pa**, back 2400 Pa |
| Legal 10-module string | **10S** on one MPPT (see below) | **5S + 5S** (never 10S) |

**SG450WM stringing** (Voc **41.72 V**, Vmp **34.2 V**, Isc **13.82 A**, Voc tempco **-0.34 %/C**):

| Config | Verdict |
|--------|---------|
| **10S** one MPPT | **Yes** -- Voc 417 V STC, ~**467 V** at -10 C (still under 550 V and under Sol-Ark 500 V). Vmp 342 V. Isc 13.82 A &lt; 18 A. Power 4.5 kW &lt; 5 kW. |
| 5S + 5S | **Avoid in heat** -- 5 x 34.2 = **171 V** STC; ~70 C cell drops Vmp under the **150 V** MPPT window. |
| 5S2P on one SPH MPPT | **No** -- Isc ~27.6 A **&gt; 18 A**. |

Electrician still runs NEC 690.7 on site min temp. **KBS-450 10S stays illegal** on the 500 V Sol-Ark (500.3 V at 25 C).

**Well + 279 W:** 6.5 kW / 13 kVA can run ~1.6 kW and start a typical 3-5 kW class inrush -- confirm **LRA** on the pump nameplate. Sol-Ark has more surge headroom; the 1.5 HP motor is not why you pay $3999 if LRA fits 13 kVA. Do **not** enable SPH energy-save (servers can dip under 50 W on reboot).

**Night:** 279 W x 17.5 h = 4.88 kWh AC. Sol-Ark pack draw at 97.6% + 96 W idle = **~6.7 kWh** of 11.78 kWh. SPH at 93% is **~5.3 kWh** for that AC **before** idle. SPH no-load watts are official-silent -- that is the same class of risk as SPH10048P, not a reason to assume 80 W from forums.

**Recommendation:** if the **12K-2P-LL is not purchased**, SPH6548P is the cost path for this well + 279 W island; put the **~$2850** inverter delta into **LiTime kWh**, not into SPH10048P. Ground-mount ten SG450WM as **one 10S**. Inverter stays **indoors**. If the 12K-2P-LL is **already bought**, do not swap it -- harvest is identical; you would only lose idle documentation, IP65, 10 yr, and GEN AC-couple. Panels stay separable: SG450WM can hang on the Sol-Ark as **10S**; KBS-450 stays **5S + 5S**.

## Which panels: KBS-450 vs SG550WM (on the 12K-2P-LL)

Same job: **ten** modules, **5S + 5S** on two MPPTs, off-grid, 2S LiTime, SC-class site (low snow). Do not 10S either module.

| | **KB MODULE-KBS-450-MONO** | **Sungold SG550WM** |
|--|---------------------------|---------------------|
| STC (10 modules) | **4.5 kW** | **5.5 kW** |
| Harvest 6.5 h x 0.70 | **~20.5 kWh** | **~25.0 kWh** |
| Cart (10) | **$2200** ($220, $0.49/W) | **$2790** ($279, $0.51/W) |
| Voc / Vmp / Isc (STC) | 50.03 / 42.16 / 11.29 A | 49.70 / 41.00 / **14.03 A** |
| Voc tempco | **-0.26 %/C** | **-0.35 %/C** |
| Size / weight each | 83.0 x 41.3 in, **51.4 lb** | 89.7 x 44.8 in, **62.4 lb** |
| Ten-module area / weight | ~238 ft2, 514 lb | ~280 ft2, 624 lb |
| Snow / wind (published) | Front **5400 Pa**, back 2400 Pa | Product table: wind **2400 Pa**; snow **not listed** on that table |
| Max series fuse | Install manual **25 A** | Datasheet **25 A** |
| UL | 61730-1/-2, CSA | 61730, CEC listed |
| Workmanship / output | 12 yr / **30 yr linear** (sheet) | 12 yr / 95-90-80% at 5/10/25 yr |
| Assembly | KB: USA manufacturing ([kb-solar.com](https://www.kb-solar.com/)) | Sun Gold Power Inc datasheet |

Sources: [KBS-450 sheet](https://cdn.enfsolar.com/z/pp/2025/1/dv61pm623hc5/module-kbs-450-mono-1.pdf), [KB install manual](https://kb-solar.com/wp-content/uploads/2024/06/KB-Solar_Installation_Manual_PV_Module_V.2.1.pdf), [SG550WM product](https://sungoldpower.com/products/550-watt-monocrystalline-solar-panel), [SG550WM datasheet](https://cdn.enfsolar.com/z/z/2025/2/p15lyv5b8r/182Mono550W-SG550WM-20250120.pdf). Cart was **monofacial** KBS-450 -- do not count bifacial rear gain.

**5S on Sol-Ark:** both sit in 150-425 V (KB Vmp ~211 V, SG Vmp ~205 V). Isc 11.3 A vs 14.0 A, both under 32 A. Cold Voc on 5S stays under 500 V on both tempcos.

**Pick:** **SG550WM** if the rack can take **62.4 lb** and the extra ~17% footprint. You pay **~$590** more for **+1000 W STC** and **~+4.5 kWh** on a good day -- almost the same dollars per watt, and that extra sun is the only PV lever on a 17.5 h night. **KBS-450** if you need smaller/lighter modules, documented **5400 Pa** snow, or the USA-assembled line. Do not mix the two models on one MPPT (Voc/Isc would not match).

## Intended load: 1.5 HP well, 400 gal/day, 8 GPM, 240 V

This island's job (operator, 11 Sep 2026): **well pump only**, **240 V**, **~8 GPM**, **400 gal/day**, cycling **on/off through the day**. Operator: **does not run 22:00-07:00**. Not T2/KU, not whole-home HVAC/range/dryer unless added later.

**Water / runtime:** 400 gal / 8 GPM = **50 minutes** of pumping per day (~1.35 kWh at ~1.6 kW input). WRF REU2016 indoor is 58.6 gpcd / 293 gal for five; 400 gal is a thicker day, not a lawn. Stay at 400 gal.

**Run watts (class motor, until you read the pump nameplate):** Franklin 1.5 HP 230 V 1-ph FLA **10 A**, FL efficiency **69%**. Shaft 1.5 HP = 1.12 kW; input ~**1.6 kW** real, **2.3 kVA** apparent. **240 V** on Sol-Ark LOAD matches this class.

**Night (22:00-07:00, 9 h, pump off):** battery sees **inverter idle only** -- 12K-2P-LL **96 W x 9 h = 0.86 kWh**; 8K-2P **0.54 kWh**. That is the easy part of the AES **5.12 kWh**.

**Day (07:00-22:00):** 50 min of 1.6 kW, split into many short cycles. While the array is producing, PV can feed the pump directly (hybrid). Shoulder hours (before sun / after sun, still before 22:00) come from the battery -- worst case the whole **~1.35 kWh** plus idle. Still well under 5.12 kWh. Six 440 W modules (~12 kWh at 6.5 h x 0.70 PR) refill with margin.

| Piece | Energy |
|-------|--------|
| Pump, 50 min at ~1.6 kW | **~1.35 kWh/day** |
| Night idle only (LL / 8K) | **0.86 / 0.54 kWh** |
| Full-day idle if the box stays up (LL / 8K) | **2.3 / 1.4 kWh** |
| Worst day: all pump kWh from battery + LL idle | **~3.7 kWh** of 5.12 |

**Running current vs AES:** ~1.6 kW AC is ~**33 A** at 51.2 V -- under **70 A** continuous.

**Starting current is the remaining limit.** On/off through the day means **many inrush events**, not one long run. Sol-Ark's published well example is **3-5 kW surge**. AES peak is **218 A RMS for 3 s**. Confirm **LRA on the nameplate**. A larger pressure tank cuts cycle count. Soft-start or a second AES if LRA is ugly. Set **Max A Discharge** from LYNK/BMS, not 220 A.

Do **not** add HVAC to this island until those starts are proven.

**Pressure tank (operator: 20 gal at 60 PSI):** treat 60 PSI as **40/60** cut-out unless the switch is 30/50. Amtrol WX-202 class **20 gal** drawdown is **5.4 gal at 40/60** (6.2 at 30/50). Usable water is that drawdown, not 20 gal.

| | 40/60 (likely) | 30/50 |
|--|----------------|--------|
| Drawdown | **5.4 gal** | **6.2 gal** |
| Cycles for 400 gal | **~74/day** | **~65/day** |
| Run per cycle at 8 GPM | **~41 s** | **~47 s** |
| Average over 15 h (07:00-22:00) | **~5 starts/h** | **~4 starts/h** |

Amtrol ESP II for **3/4 hp+** wants ~**2 min** run. At 8 GPM that is **~16 gal** drawdown. This 20 gal tank is about **one-third** of that. Average starts/hour are under Franklin's **20/h** if the 400 gal is spread. A morning bunch (showers) can stack 10-20 starts in one hour and hit the 20/h / 3 min gap. Each start is a Sol-Ark/AES surge. Cheapest fix for the inverter is a **bigger tank** (Amtrol 8 GPM / 40/60 ESP II is in the WX-251 / WX-255 class), not a second battery.

## Adding cluster servers (same Sol-Ark LOAD, still not T2/KU DC)

Operator question: use this **one** AES 48-48-5120 (**5.12 kWh**, 70 A continuous, 218 A peak -- Discover sheet 06/05/2024) and also run `.111` / `.148` / `.229`. Those hosts stay on **120/240 V LOAD**. Do not land this 48 V rack on the 24 V buses.

Measured AC (KU Renogy, fan+Midea off): **~279 W** (11 Sep 16:11) and **~418 W** (10 Sep 14:57). Use **279 W** as the light cluster, **418 W** as the heavier day. Servers run **24/7**. The well does **not** (off 22:00-07:00).

Dark hours for PV on a day like 11 Sep are still **~17.5 h** (charge window ~09:30-16:00). That is longer than the pump-off night.

| Load on this island | 17.5 h dark (battery) | 24 h energy | One 5.12 kWh AES? |
|---------------------|------------------------|-------------|-------------------|
| Well only | idle **0.9-1.7 kWh** (pump off at night) | **~3.7 kWh** worst | **Yes** |
| Servers 279 W | **4.9 kWh** + LL idle **1.7 kWh** = **~6.6 kWh** | **6.7 + 2.3 idle + 1.35 pump = ~10.3 kWh** | **No** -- night is larger than the pack |
| Servers 418 W | **7.3 + 1.7 = ~9.0 kWh** | **~13.7 kWh** | **No** |

Running watts are fine: 279-418 W + 1.6 kW pump is under AES **70 A / ~3.6 kW** continuous (Discover: 70 A Adc, 95 A for 1 h, 5.12 kW 1C). The miss is **kWh through the dark**, not amps while the sun is up. Sol-Ark 12K-2P-LL max efficiency is **97.6%** ([datasheet](https://sol-ark.com/wp-content/uploads/2026/05/SA-12K-2P-LL_Datasheet_Rev1.1_PS-00045.pdf)); applying that to 279 W AC still leaves ~6.7 kWh dark. Official docs do not publish a part-load battery-to-AC CEC number -- do not assume Renogy's ~90% here.

**What you actually buy (do not default to 12 panels + 2 AES):**

The well is **~1.35 kWh/day**. Cluster at **279 W** is **~6.7 kWh/day** -- about **five times** the pump. The second battery is for **server night**, not for 240 V water.

| How this island is used | Panels | AES | Why |
|-------------------------|--------|-----|-----|
| Well only, off-grid | **6** | **1** | Night is idle. Day harvest ~12 kWh vs ~3.7 kWh worst. |
| Well + **279 W** servers, **off-grid 24/7** | **6** | **2** | Night ~6.6 kWh > 5.12. Day ~10.3 kWh **fits** six 440 W on a 6.5 h x 0.70 day. |
| Well + **418 W** servers, **off-grid 24/7** | **6** almost; **12** if you want the day to close | **2** | Night ~9.0 kWh still fits two modules (tight). Day ~13.7 kWh is **~1.7 kWh short** of ~12 kWh harvest -- not 2x energy. Next string is another **6S** because Sol-Ark MPPT startup is **125 V** (3S is too low). |
| Servers **sleep at night** on this island | **6** | **1** | Battery only covers idle + shoulder + pump. Same as well-only plus daytime IT from PV. |

Utility / grid-tie is **not in this BOM**. It would drop night energy onto the meter and let **6 + 1** cover well + servers while the grid is up. That is a later choice, not the starting plan.

**12 panels + 2 AES** is the 418 W off-grid hedge (or winter/cloud margin). It is **not** the well, and it is **not** required for 279 W on a good harvest day.

**Two** AES (**10.24 kWh**) cover ~6.6 kWh dark at 279 W. **418 W** dark ~9.0 kWh still wants two, with little margin. Switching to **8K-2P** (60 W idle) still needs ~5.9 kWh dark at 279 W -- not enough to skip the second module off-grid.

Pump starts (~74/day on the 20 gal tank) still hit while servers are running. Upsize the tank first; second AES is for **server night kWh**, not for tank cycling.

## Start at 8 x ~440 W + 2 AES, 500 W servers, same 20 gal tank (off-grid)

Operator question (11 Sep 2026). Utility is **not** assumed.

**Energy (same 6.5 h x 0.70 PR model as the six-panel harvest):** 8 x 440 W = **3.52 kW STC** -> **~16.0 kWh/day**. Two AES = **10.24 kWh**.

| | 24 h energy | 17.5 h dark (battery) | Two AES 10.24? | Eight-panel harvest ~16.0? |
|--|-------------|------------------------|-----------------|----------------------------|
| 500 W servers | 12.0 kWh | 8.75 kWh | | |
| 12K-2P-LL idle 96 W | 2.30 kWh | 1.68 kWh | | |
| Well (50 min) | 1.35 kWh | 0 if all pumping is in sun | | |
| **Total, 12K-LL, pump in sun** | **~15.7 kWh** | **~10.43 kWh** | **No** -- over by **~0.2 kWh** even at 100% DoD | **Barely** (~0.3 kWh left) |
| Same + Sol-Ark max eff. 97.6% on the 500 W | | **~10.6 kWh** | **No** | |
| **Total, 8K-2P idle 60 W, pump in sun** | **~14.8 kWh** | **~9.80 kWh** | **Close** (~0.4 kWh left) | **Yes** on a good day |
| Any pump kWh after 16:00 / before 09:30 | +up to 1.35 | +up to 1.35 | **No** on 12K or 8K | still a good-day PV fit |

Eight panels fix the **day** at 500 W (16 vs 15.7 on 12K-LL). They do **not** fix the **night**. Two AES still have to hold **17.5 h x 500 W + inverter idle**. On the 12K-2P-LL that is **larger than 10.24 kWh**. You would hit empty **before** the next charge window -- on the order of **20-30 minutes** of 500 W, not hours of margin.

**Watts** are easy: 1.6 kW pump + 0.5 kW servers is **~2.1 kW** AC. Two AES at 70 A each is **~7.2 kW** continuous at 51.2 V. Discover rates peak/current as scaling in parallel ([48-48-5120](https://discoverbattery.com/products/search/48-48-5120)).

**20 gal tank:** unchanged. Still **~74 starts/day**, **~41 s** runs at 40/60. That is a **start-count / surge** problem, not a kWh problem. Two modules give more peak amps for each inrush. They do not make a 5.4 gal drawdown into Amtrol's ~16 gal / 2 min run. Morning showers can still stack toward Franklin **20 starts/h**. Keep the bigger tank on the list even if you buy 8 + 2.

**String eight modules on 12K-2P-LL** ([datasheet](https://sol-ark.com/wp-content/uploads/2026/05/SA-12K-2P-LL_Datasheet_Rev1.1_PS-00045.pdf), [manual](https://sol-ark.com/wp-content/uploads/2026/05/12K-LL_Installation_Manual_MA-00057_Rev3_16July202.pdf)): startup **125 V**, rated **150-425 V**, **do not exceed 500 Voc**, two strings per MPPT must share Voc.

| Config | Why / why not |
|--------|----------------|
| **8S, one MPPT** | Class 144-cell 440 W Voc ~49 V -> ~392 V STC, Vmp ~328 V (under 425 Vmp). Cold Voc (NEC 690.7, module tempco, site min temp) is the electrician's check -- a **-0.26 %/C** class example stays under 500 V at **-40 C**. Use the **purchased** sheet, not this class row. |
| 6S + 2S | **No** -- 2S will not start (under 125 V). |
| 4S2P | Heat can drop Vmp under the **150 V** rated window (already called marginal for 4S). |

Eight is an awkward step vs **6 then 12** (two 6S strings). If you start at eight, plan later growth as another **8S** (or +4 to make two 6S), not a leftover pair.

**Off-grid answer:** **500 W 24/7 + this well + 12K-2P-LL idle + two AES is not a yes.** It is empty-every-morning on a good night, and short on a night that includes pump or clouds. Paths that close the night: cap servers near **~450 W**, **8K-2P** idle (60 W) with pump strictly in sun, or a **third AES**. Eight panels are the right *day* bump; they are not a third battery.

## What this starter actually is

The inverter and the first battery are different sizes. Plan around the **battery and the six modules**, not the 10 kW nameplate.

| Limit | Number | Why it matters |
|-------|--------|----------------|
| PV nameplate | **2.64 kW STC** (front) | First array. Bifacial rear gain is albedo/height -- module sheets often table 5-15%, not a site promise. |
| AES energy | **5.12 kWh**, 100% DoD rated | Same *order* of kWh as one LiTime 24 V 230 Ah -- a new pack, not that pack. |
| AES continuous current | **70 A** charge/discharge (95 A for 1 h; 218 A RMS peak 3 s) | At 51.2 V that is **~3.6 kW DC**. One module cannot feed 10 kW backup. |
| 12K-2P-LL battery port | **220 A**, **10 kW AC from batteries** | Headroom for **more AES modules in parallel**. |
| 12K-2P-LL idle | **96 W** no-load | **~2.3 kWh/day** if it sits up 24 h -- **~45% of one 5.12 kWh module** with no other load. |
| 8K-2P idle | **60 W** | **~1.4 kWh/day**. Still a large slice of 5.12 kWh. |
| AES charge voltage | Bulk/absorb **55.2 V**, float **53.6 V**, suggested cutoff **48 V** | Fits LL **43-59 V**. Program cutoff at Discover **48 V**, not the inverter's 43 V floor. |
| AES charge temperature (900-0062) | **4 C to 52 C** | No internal heater. Cold site: **48-48-5120-H** (900-0067), 50 W BMS heat. |
| Enclosure | Module **IP20** | Needs a rack/enclosure. **UL 9540** is the Slimline **950-0053**, not the open Quick Stack **950-0050**. |

To actually use **10 kW from batteries** you need enough parallel AES current: 10 kW AC is on the order of **~200 A** at 48 V after conversion. At **70 A**/module that is **about three modules** (~15 kWh) before the inverter, not one.

Closed-loop (required for this pairing): **LYNK II 950-0025**, Sol-Ark pin adapter **950-0016-SLRK**, LYNK ACCESS set to the Sol-Ark protocol, inverter **BMS Lithium Batt = 00**. Discover lists 5K-P / 8K-P / 12K-P / 15K-P outdoor. Confirm 12K-2P-LL on the same LYNK profile before buying (official LYNK page names 12K-2P-N / 15K-2P-N manuals; Sol-Ark's AES write-up is under **5120-H**). Do not invent a pinout -- use those two vendor guides.

## First array: 6 x ~440 W bifacial

Use the **purchased** module datasheet for Voc, Vmp, Isc, Voc tempco, and max series fuse. Until a SKU exists, size with the 144-cell 440 W class (Voc ~49-50 V, Vmp ~41 V, Isc ~11.1-11.4 A at STC).

Sol-Ark MPPT will not start below **125 V**. Rated window **150-425 V**, max VOC **500 V** (coldest-day calc, NEC 690.7 on the real tempco).

| Config | Approx Vmp (STC) | Approx Voc (STC) | Verdict |
|--------|------------------|------------------|---------|
| 3S or 3S2P | ~123 V | ~148 V | **No** -- under 125 V start |
| 4S | ~164 V | ~198 V | Marginal in heat vs 150 V MPPT min |
| **6S (one string, one MPPT)** | **~246 V** | **~297 V** | **Yes** -- first array |
| 6S2P later | ~246 V | ~297 V | Second string; watch Isc vs MPPT Imax (LL **32 A**/MPPT, 8K **18 A**) |

One 6S string at ~11 A (plus some bifacial current) is under both MPPT current limits. Leave the other MPPTs empty on day one (LL has **three**).

**Mount:** bifacial wants rear light (height, open rack, light ground). Flat on dirt throws away the bifacial part.

**Charge vs AES 70 A:** 2.64 kW STC is **~52 A** at 51.2 V if it all went into the battery. The first array cannot over-current one AES module. The inverter's **220 A** charger is for later, larger PV.

**Empty-to-full, no load (order of magnitude):** 5.12 kWh / (2.64 kW x 0.70 performance ratio) ~ **2.8 equivalent full-sun hours**. A 6.5 h window like 11 Sep can refill this pack if loads stay small. Weather and tilt move this; it is not a promise.

Overnight: 5.12 kWh minus inverter idle. At 96 W idle alone, **~2.3 kWh** is gone by morning with zero loads. Size loads on **what is left**, not on 5.12 kWh nameplate.

## Growth (still this island, still not T2/KU)

Day-one is **10 x 450 W (5S2P or 5S+5S)** and **one AES**. Then:

1. **Second AES 900-0062** in parallel (combiner **950-0049**, or Slimline) -- this is the 24/7 server gate.
2. More PV: another **5S** pair (20 modules) on a free MPPT, or a third AES, after the second battery exists.
3. Only with **~3 AES** (~15 kWh / ~210 A class) does the **10 kW battery** rating on the 12K-2P-LL become usable.

Do not grow by adding a 10S string.

## Open (close before purchase)

1. Exact module is **KBS-450** (datasheet above). Confirm label Voc 50.03 V before landing 5S.
2. **12K-2P-LL** is in the cart (not 8K-2P).
3. Confirm LYNK II + 12K-2P-LL on Discover/Sol-Ark current docs (or buy 8K-P / 12K-P which those pages name).
4. Indoor vs outdoor: Slimline **950-0053** (UL 9540) vs Quick Stack **950-0050** (Discover: **not** UL 9540).
5. Cold: stay **900-0062** or step to heated **900-0067**.
6. **Off-grid** (default for this chapter). Optional later: utility on GRID, or generator **120/240 V split-phase** + two-wire AGS. Do not enable Grid Sell into a generator ([12K-2P manual](https://sol-ark.com/wp-content/uploads/2024/06/SK140-0003-002-12K-2P-N-EN-Manual-1-1.pdf)).
7. Well nameplate: FLA, **LRA**, 2-wire vs 3-wire + control box. Confirm pressure **switch** 40/60 vs 30/50 (tank is 20 gal / 60 PSI). Volts **240 V**, flow **~8 GPM**, **no run 22:00-07:00** -- confirmed.
8. Stay at **400 gal/day**. If irrigation pushes past that, add PV/AES; do not treat 400 as a lawn budget.
9. Electrician: NEC 690 VOC, RSD, grounding, one-line. Sol-Ark lists integrated RSD control. Consider a larger pressure tank (Amtrol ESP II for 1.5 hp / 8 GPM) before a second AES.

## AES 48-48-5120 vs LiTime 24 V 230 Ah (48 V value)

Brainstorm only (12 Sep 2026). Isolation rules above still apply: do not parallel AES with series LiTime; do not edit [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md) for a T2/KU cutover. Operator quotes: AES **$1600**, LiTime **$1200**. Visual dump: canvas `aes-vs-litime-48v.canvas.tsx` (lead is **2 vs 2**; Sections A/B stay brand-pure dumps).

**Lead (2 vs 2):** see the subsection immediately after Section C. Single-module dumps remain below so A is AES-only and B is LiTime-only.

Format: Section A is AES only. Section B is one LiTime pack only. Section C is winners, with a 48 V **bank** column (1 AES vs 2S LiTime).

### Section A -- Discover AES RACKMOUNT 48-48-5120 / 900-0062 (AES only)

Operator sheet Printed **06 05 2024**, Product Model **900-0062**, **$1600**. Gaps filled from Discover IOM [805-0043 REV K-1](https://discoverenergysys.com/s4x_files/resources/des-aes-rackmount-user-manual.pdf) (also [discoverbattery.com copy](https://discoverbattery.com/s4x_files/resources/des-aes-rackmount-user-manual.pdf)), [AES RACKMOUNT product](https://discoverenergysys.com/products/lithium-batteries/aes-rackmount), [48-48-5120](https://discoverbattery.com/products/search/48-48-5120), module datasheet Printed 22/04/2024, warranty [885-0043 REV H](https://discoverenergysys.com/s4x_files/resources/des-aes-rackmount-warranty.pdf), Sol-Ark [LV Battery Integration Rev7](https://sol-ark.com/wp-content/uploads/2024/06/LV_Batt_Integration_Rev7_24March2026.pdf).

| Field | Published value | Source |
|-------|-----------------|--------|
| Family / SKU | AES RACKMOUNT 48-48-5120, Product Model 900-0062 | Sheet; IOM cover |
| Heated sibling (not this quote) | 48-48-5120-H / 900-0067, 50 W BMS heat | IOM 3.5; product page |
| Chemistry / cells | LiFePO4, 16S1P | Sheet; datasheet |
| Made in | China | Datasheet shipping class |
| OCV / nominal | **51.2 V** | Sheet; IOM 3.1 |
| Energy | **5.12 kWh** (5120 Wh, 1C) | Sheet; datasheet; IOM 3.1 |
| Capacity 1 hr | **100 Ah** | Sheet; IOM 3.1 |
| Usable DoD | 100% | Datasheet |
| Bulk / U1 | **55.2 V** | Sheet; IOM 3.1 |
| Float U2 | **53.6 V** | Sheet; IOM 3.1 |
| Suggested LVD | **48.0 V** | Sheet; IOM 3.1 |
| BMS LVD | 43.2 V (2.7 VPC under load; no-load floor 3.0 VPC) | IOM 3.1 note (b) |
| Charge 1 hr / continuous | **95 A** / **70 A** | Sheet; IOM 3.1 |
| Min finish | **2.5 A** (may be less; lower aids balancing) | Sheet; IOM 3.1 |
| Discharge 1 hr / continuous | **95 A** / **70 A** | Sheet; IOM 3.1 |
| Continuous power | **5.12 kW** | Sheet; datasheet |
| Peak | **218 A RMS / 3 s** (datasheet up to 2.2C; sheet marketing also says 3C peak 3s) | Sheet; datasheet; IOM 3.1 |
| Self-discharge | **<3%/month @ 25 C** | Sheet; datasheet |
| Breaker | Dual 100 A, 2-pole ganged, K-curve | IOM 3.1 |
| Short-circuit IBF | 3.8 kA / 1.9 kA (100 ms) | IOM 3.1 |
| Charge temp (cells) | **4-52 C** (900-0062 has no heater) | Sheet; IOM 3.3 |
| Discharge temp (cells) | **-17-52 C** | Sheet; IOM 3.3 |
| Storage | 1 month **-20-55 C**; 6 months -10-30 C | Sheet; IOM 3.3 |
| Form / size / weight | 19 in **3U**; **19.6 x 17.3 x 5.3 in**; **97 lb** | Sheet; IOM 3.2 |
| IP / case / terminals | **IP20**, galvanized steel, Amphenol SurLok Plus (+ C10-730186-200, - C10-730186-100) | Sheet; IOM 3.2 |
| Install ambient | 4-40 C (ideal 15-20 C); 1U airflow; not face-down; outdoor only in a rated enclosure | IOM 9.2 |
| DC cable | 3 AWG (4 AWG OK), 90 C Cu stranded | IOM 9.3 |
| Certifications | UL 1973, UL 9540a, UN 38.3, IEC 62619, CEC, CE, FCC Class B, EN61000-6-2/6-3 | Sheet; IOM 3.7 |
| UL 9540 / seismic AC156 | Slimline **950-0053** only (Quick Stack **950-0050** is not UL 9540) | Datasheet; IOM 9.2 |
| Sol-Ark closed-loop | Yes -- AES RACKMOUNT on [LV Rev7](https://sol-ark.com/wp-content/uploads/2024/06/LV_Batt_Integration_Rev7_24March2026.pdf) (write-up titled 48-48-5120-H); LYNK II + **950-0016-SLRK** | Sol-Ark; Discover LYNK Sol-Ark notes |
| Series | Forbidden (IOM 1.3) | IOM |
| Parallel | **Same model only**; within 50 mV; 100% SoC first; closed-loop up to 36 modules / **180 kWh** per LYNK; unlimited kWh open-loop | IOM 9.7; datasheet; sheet |
| SoC | Voltage lead-acid meters are wrong; use **LYNK II** | IOM 10.2 |
| Sheet features | 10x life of lead (BCI-06); 1C charge regardless of SoC; 4th-gen BMS; Dynamic Charging / top-balance | Sheet; datasheet; product page |
| Round-trip (marketing) | Up to 98% | Datasheet |
| Workmanship warranty | 5 years base; **10 years** if registered within 30 days of install | [885-0043 REV H](https://discoverenergysys.com/s4x_files/resources/des-aes-rackmount-warranty.pdf) |
| Throughput | **3000 kWh/year** and **30 MWh** total (on-board logger). Product page (12 Sep 2026) also says **38 MWh** -- that conflicts with 885-0043 and the operator sheet (30 MWh). Use the warranty PDF until Discover republishes 885-0043. | 885-0043 vs product page |
| End-of-warranty energy | Official: **79% SOH** or **4.05 kWh** at 100% DoD (10 yr / 30 MWh). Unlimited-cycles floor: **60%** of Rated Wh. Operator sheet **70%** is not the 885-0043 10-year line. | 885-0043; operator sheet |
| Box contents | Module, CAT6 12 in, 4x M6, ground 200 mm, serial labels, spare hardware -- **not** LYNK / rack / cables | IOM Table 2-1 |

**Protections (IOM Table 3-4):** OV >58.24 V / 3 s (cell >3.64 VPC), recover 120 s and <55.2 V; UV <43.2 V / 5 s, no auto recover, OFF after 120 s; over-charge >97 A / 10 s; over-discharge 218 A 3 s class; OT discharge cell >52 C / 5 s recover <50 C; UT discharge <-17 C recover >-15 C; OT charge >52 C recover <40 C; UT charge <4 C with charge current, recover 120 s and >=4 C; load qualification (mixed voltage, short, reverse, input C) re-qualify 120 s, 10 fails then OFF.

**Not in the $1600 module (SKUs only -- Discover/Sol-Ark list prices official silent; do not invent street prices):** LYNK II **950-0025**, Sol-Ark adapter **950-0016-SLRK**, Slimline **950-0053**, Quick Stack **950-0050**, combiner **950-0049**, SurLok kit **950-0054**, cable kit **950-0055**, Slimline fan **950-0064**.

### Section B -- LiTime 24 V 230 Ah, one pack (LiTime only)

Official [24V 230Ah product](https://www.litime.com/products/24v-230ah-lithium-battery) (non-Bluetooth, non-self-heating Group 8D). Manuals index: [LiTime 25.6V 230Ah Battery - User Manual.pdf](https://www.litime.com/pages/user-manuals). This pass used the live product HTML (12 Sep 2026). The PDF filename is official; a stable CDN binary was not extracted here. **No host UART/RS485/CAN map** is published on the product page.

| Field | Published value | Source |
|-------|-----------------|--------|
| Nominal | **25.6 V**, **230 Ah**, **5888 Wh** | Product |
| Internal R | <=40 mOhm | Product |
| Bluetooth / self-heat / low-temp charge cut | None on this SKU | Product table `/` |
| BMS | **200 A** | Product |
| Continuous power | **5120 W** | Product |
| Charge / discharge continuous | **200 A** / **200 A** | Product |
| Peak | **400 A / 5 s**, **800 A / 1 s** | Product |
| Charge method / voltage | CC/CV, **28.8 V +/- 0.4 V** | Product |
| Recommend charge | Table **46 A**; FAQ **46 A (0.2C)** ~5 h to 100%, **115 A (0.5C)** ~2 h to ~97%, 28.4-29.2 V | Product; FAQ |
| Charge / discharge / storage temp | **0-50 C** / **-20-60 C** / **-10-50 C** (store ~50% SoC, cycle every 3 months, 45-75% RH) | Product; FAQ |
| Size / weight / IP / case | Group 8D **20.47 x 10.59 x 8.66 in**, **86.6 lb**, **IP65**, flame-retardant **ABS**, **M8** | Product |
| Expansion | Max **4P2S**. Identical brand, type, voltage, capacity, BMS; purchased within **1 month**. FAQ: 2S, 4P, or 8 series-parallel. | Product; precautions; FAQ |
| Cycles | **4000** at 100% DoD; 6000 at 80%; 15000 at 60% | Product |
| Warranty | **5 years** | Product |
| Certs | FCC, CE, RoHS, UN38.3 -- **no UL 1973 / UL 9540** on this page | Product |
| Starter use | Forbidden | Product / FAQ |
| Operator price | **$1200** | Operator quote |
| LiTime.com list this fetch | $1079.99 (was $1599.99) -- **not** used in the value math | Product 12 Sep 2026 |
| Host protocol | **Official silent.** FAQ: not compatible with Bluetooth module; use a **500 A battery monitor with shunt**. | Product FAQ |
| 500 A LCD monitor | 8-120 V, 0-500 A, LCD on 20 ft shielded wire; no published UART/MQTT | [500A monitor](https://www.litime.com/products/litime-500a-battery-monitor-with-shunt) |

LiTime is **not** on Sol-Ark [LV Batt Integration Rev7](https://sol-ark.com/wp-content/uploads/2024/06/LV_Batt_Integration_Rev7_24March2026.pdf).

### Section C -- winner per data point (48 V banks)

Fair 48 V buy: **1 AES** ($1600, already 51.2 V / 5.12 kWh) vs **2S identical LiTime** ($2400, 51.2 V / 230 Ah / 11.776 kWh). Math: AES $1600/5.12 = **$313/kWh**. One LiTime $1200/5.888 = **$204/kWh**. 2S $2400/11.776 = **$204/kWh**.

| Metric | Winner | Winning published value | 1 AES bank | 2S LiTime bank |
|--------|--------|-------------------------|------------|----------------|
| USD per kWh | **2S LiTime** | **$204/kWh** | $313/kWh | $204/kWh |
| Nameplate energy | **2S LiTime** | **11.776 kWh** | 5.12 kWh | 11.776 kWh |
| Ah at 48 V | **2S LiTime** | **230 Ah** | 100 Ah | 230 Ah (series keeps Ah) |
| Invoice cash (this pair) | AES | $1600 | $1600 module; LYNK/rack extra | $2400 packs; monitor extra |
| Charge voltage | Different -- do not mix | AES 55.2/53.6 vs 2S 57.6 +/- 0.8 | Bulk 55.2, float 53.6, cutoff 48 | 2 x (28.8 +/- 0.4) |
| Continuous current | **2S LiTime** | **200 A** | 70 A (95 A 1 h) | 200 A |
| Continuous watts | **2S LiTime** | ~10.2 kW class (200 A x 51.2 V) | 5.12 kW | ~10.2 kW; each pack 5120 W at 24 V |
| Peak | **2S LiTime** (longer pulse) | 400 A / 5 s, 800 A / 1 s | 218 A RMS / 3 s | 400 A / 5 s, 800 A / 1 s |
| IP / case | **2S LiTime** | IP65 ABS | IP20 steel -- needs enclosure | IP65 each |
| Mass of 48 V bank | AES | 97 lb vs 173.2 lb | 97 lb | 173.2 lb |
| Sol-Ark closed-loop | **AES** | On LV list via LYNK | Yes (950-0025 + 950-0016-SLRK) | Not on list -- open-loop |
| UL 1973 / 9540a | **AES** | Pack UL published | Yes; UL 9540 in 950-0053 | FCC/CE/UN38.3 only on this page |
| Warranty / throughput | **AES** | 10 yr registered + 30 MWh | 885-0043 | 5 yr; 4000 cycles; no MWh clause |
| SoC to inverter | **AES** | LYNK broadcasts SoC | LYNK II not in $1600 | External shunt; no pack BT |
| Charge below freezing | Neither this pair | AES 4 C; LiTime 0 C | Buy 900-0067 for heat | No self-heat on this SKU |
| Mix AES + LiTime | **Nobody -- forbidden** | Discover same-model; Sol-Ark do not mix makes; LiTime identical only | IOM 9.7 | Identical LiTime only |

**Recommendation (1 AES vs 2S, kept for the dump):** 2S LiTime for kWh per dollar on open-loop 48 V. One AES if you need closed-loop on a smaller bank -- then the fair AES night bank is **two AES**, not a LiTime parallel. Do not mix. T2/KU packs staying on 24 V is [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md).

### 2 vs 2: 2S LiTime vs 2P AES (apples-to-apples 48 V)

Operator (12 Sep): two new LiTime 24 V 230 Ah in series versus two AES 48-48-5120 (900-0062) in parallel. Quotes: LiTime **$1200** each (**$2400**), AES **$1600** each (**$3200**) plus LYNK II **950-0025**, Sol-Ark adapter **950-0016-SLRK**, rack/Slimline (street prices official silent -- do not invent). **Do not mix** brands on one bus. T2/KU stay in [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md). Canvas lead: `aes-vs-litime-48v.canvas.tsx`.

| | **2S LiTime** | **2P AES** |
|--|---------------|------------|
| Invoice (packs/modules) | **$2400** | **$3200** + LYNK/rack SKUs |
| Voltage / Ah / kWh | 51.2 V, **230 Ah**, **11.776 kWh** | 51.2 V, **200 Ah**, **10.24 kWh** (IOM Table 3-7 sample **10 kWh**) |
| USD/kWh | **$204** | **$313** (modules only) |
| Charge | **57.6 V +/- 0.8 V**; recommend **46 A** (0.2C), up to 115 A (0.5C), max **200 A** | Bulk/float **55.2 / 53.6 V**; continuous **140 A**, 1 h **190 A** |
| Peak | **400 A / 5 s**, **800 A / 1 s** | **436 A RMS / 3 s** |
| Closed-loop Sol-Ark | **No** (not on LV Rev7) | **Yes** via LYNK |
| UL 1973 | Not on this product page | **Yes** |
| IP / mass | IP65, **173.2 lb** | IP20, **194 lb** |
| Warranty | **5 yr**; 4000 cycles at 100% DoD | **10 yr** if registered; **30 MWh** on 885-0043 vs **5120 Wh** -- PDF does **not** say per module vs per system |

Sources: [LiTime 24V 230Ah](https://www.litime.com/products/24v-230ah-lithium-battery), Discover [IOM](https://discoverenergysys.com/s4x_files/resources/des-aes-rackmount-user-manual.pdf) Table 3-7 / 9.7, [885-0043](https://discoverenergysys.com/s4x_files/resources/des-aes-rackmount-warranty.pdf), Sol-Ark [LV Rev7](https://sol-ark.com/wp-content/uploads/2024/06/LV_Batt_Integration_Rev7_24March2026.pdf).

**Night (17.5 h dark, 96 W idle):** typical **279 W** cluster = **6.56 kWh** -- both cover (LiTime ~5.2 kWh left, AES ~3.7 kWh left). **500 W** all night = **10.43 kWh** -- tight on both (LiTime ~1.3 kWh left; AES ~0.2 kWh over 10.24 nameplate at 100% DoD). 500 W / 400 gal stay **peaks**.

**Lead recommendation (one path):** for **kWh per dollar and night kWh**, buy **2S LiTime** and program Sol-Ark **open-loop** (cap Max A Charge in the 46-115 A band). For **Sol-Ark closed-loop / UL 1973 / LYNK SoC / 10 yr throughput**, buy **2P AES** plus LYNK II / adapter / rack. Do not mix.

**Field reports vs paper warranty (12 Sep 2026):** neither vendor publishes a failure rate. [CPSC.gov](https://www.cpsc.gov/) search found **no recall** for LiTime or Discover AES RACKMOUNT (other lithium recalls exist; not these SKUs).

| Source | LiTime | Discover AES RACKMOUNT |
|--------|--------|------------------------|
| Official failure count | **Silent** | **Silent** |
| CPSC recall | None found | None found |
| BBB ([LiTime Indianapolis file](https://www.bbb.org/us/in/indianapolis/profile/batteries/litime-0382-90060420/complaints)) | **4** complaints in 3 years, **2** closed in 12 months, all **Unanswered**; 3 product / 1 service. None named the 24 V 230 Ah. | No matching Discover Energy Systems battery profile found (do not confuse with similarly named solar installers). |
| Vendor site reviews | [24V 230Ah](https://www.litime.com/products/24v-230ah-lithium-battery): **16** reviews, all 5-star (tiny sample) | Dealer SKU; no Amazon-scale public review pile |
| DIY forums (not official) | Recurring **parallel Full-Charge Protection / uneven discharge** and **12 V-in-series imbalance** threads ([DIY Solar](https://diysolarforum.com/threads/litime-batteries-discharging-at-a-different-rate-update.106027/), [iRV2](https://www.irv2.com/threads/uneven-discharge-in-parallel-litime-lithium-batteries%E2%80%94normal-or-problem.2187404/)). This island's bank is **2S of 24 V** (LiTime-allowed), not 4x 12 V. | Fewer posts (dealer channel). Aug 2026: one owner of **six heated AES** said Discover **denied** a failed module as overcharge after HV faults in LYNK logs; installer would not pull the faceplate ([thread](https://diysolarforum.com/threads/discover-energy-systems-refuses-warranty-on-48v-rackmount-heated-battery-beware.128667/)). Same thread: another six-pack owner got a **BMS faceplate shipped** after a firmware fail. |

Paper warranty still favors AES ([885-0043](https://discoverenergysys.com/s4x_files/resources/des-aes-rackmount-warranty.pdf): 5 yr base, **10 yr** if registered within 30 days, 30 MWh / 79% SOH line) over LiTime **5 yr**. AES claims are **harder to collect**: file within **15 days**, LYNK data logger required. Discover's own Sol-Ark note: LYNK loss >10 s can stop the inverter (**F58**) if `BMS Lithium Batt` and `BMS_Err_Stop` are on ([LYNK II Sol-Ark](https://docs.discoverenergysys.com/805-0033-lynk-ii-installation-manual/release/compatibility-solark)). If warranty is the tie-break, buy **2P AES**, **register**, keep LYNK logs, and program **55.2 / 53.6 V**.

Pi-side supervisor design (not a pack BMS replacement): [PI4_BMS_SOFTWARE.md](PI4_BMS_SOFTWARE.md).

## Related

- [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md) -- **different** plant (24 V T2/KU). Read it so this island is not mixed into that log.
- [PI4_BMS_SOFTWARE.md](PI4_BMS_SOFTWARE.md) -- Pi4 supervisor / MQTT design (observe-only v1). Not a pack BMS replacement.
- Discover [AES RACKMOUNT](https://discoverenergysys.com/products/lithium-batteries/aes-rackmount)
- LiTime [24V 230Ah](https://www.litime.com/products/24v-230ah-lithium-battery)
- Sol-Ark [12K-2P-LL](https://sol-ark.com/residential-energy-solutions/limitless-12k-2p-ll-hybrid-inverter/)
