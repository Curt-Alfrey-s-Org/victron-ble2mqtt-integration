# Plan: move the Solar tab cards onto Site solar

Request (2026-09-28): "add all the cards from solar tab and add them to the site solar
tab, only add the ones that aren't already there."

## What the two tabs are

| Tab | Where it lives | In git? |
|---|---|---|
| **Site solar** (`/site-solar`) | Storage dashboard seeded from `config/dashboards/solar-plant.yaml` by `scripts/save_solar_plant_storage_dashboard.py`. It has two views: **Now** (22 sections, 39 tiles, 4 badges) and **History** (graphs). | Yes (the seed) |
| **Solar** (sidebar, `/dashboard-solar`, storage key `lovelace.dashboard_solar`) | Storage dashboard that exists **only in the live HA**. It was built in the UI from MQTT discovery (Victron / Sungold / shunt tiles, see `docs/SOLAR_HA_DASHBOARD.md`), then edited by `scripts/ha_label_sungold_solar.py` (adds a **Sungold** section) and `scripts/ha_label_victron_refoss.py` (renames headings such as `Mppt charger` to `BlueSolar MPPT 75/15`, and sets tile names to the entity name). | **No** |

The repo only knows fragments of the Solar tab. It has one sections view, device headings,
a Sungold section built from registry `unique_id`s, and tiles named by entity name. It does
not know the full card list. The live `entity_id`s also differ from the `unique_id`s: for
example, Site solar uses `sensor.sungold_sph302480a_pv_voltage` where the unique id is
`sungold_sph302480a-pv1-voltage`. A comparison built from the repo alone would be a guess.
So the card-by-card table below is filled in from a **read-only export** of the live Solar
tab. That export is Phase 1 of the host steps.

## Tools (from PR #13)

- `python3 scripts/site_solar_settings.py export-dashboard [--url-path dashboard-solar] [--out FILE]`
  (read-only). It calls only `lovelace/dashboards/list` and `lovelace/config`, and writes
  `config/dashboards/exports/solar-tab.json`. Token-like values (`token=...`, `api_key`,
  `password` keys) are replaced with `<redacted>` and listed. If the url_path is wrong,
  it lists every dashboard so you can pick the right one.
- `python3 scripts/compare_solar_tab.py [EXPORT] [--markdown FILE] [--apply]`
  (EXPORT defaults to `config/dashboards/exports/solar-tab.json`)
  - It compares cards by **what they show**: their entity ids from `entity`, from
    `entities`, and from ids named in templates, markdown and auto-entities filters
    (globs such as `switch.ihoment_h5082_*`; excluded globs do not count).
  - It opens stacks, grids and conditional cards, and includes view badges.
  - Without `--apply` it only prints the table.

  | Status | Meaning | Decision |
  |---|---|---|
  | `on-site-solar` | every entity already has a live card or badge on Site solar | keep as is; the table says where |
  | `same-content` | no entities, but an identical card is already on Site solar | keep as is |
  | `history-only` | on Site solar only inside a History graph | add a live card |
  | `partly` | some entities on Site solar, some not | add the card with only the missing entities |
  | `missing` | none of its entities are on Site solar | add |
  | `no-entities` | markdown, sankey and similar, with no identical card | added for review; delete if not wanted |
  | `needs-decision` | shows H5082 plugs or dump helpers | **not copied** (see rules) |
  | `skipped-private` | names a Tailscale host (`*.ts.net`) or a 100.64/10 IP | **not copied** (`docs/TAILSCALE.md`) |
  | `duplicate` | same card as an earlier Solar card (another view repeats it) | compared once, not copied twice |

- `--apply` appends **one new view**, **Solar tab** (`path: solar-tab`), at the end of the
  seed. Its cards are grouped under the Solar tab's own headings, starting with a short
  note.
  - Now and History are **not touched**: the script reloads the seed and refuses if any
    existing view or top-level key changed.
  - Re-running `--apply` replaces only that generated view (it is found by its marker
    comment). A hand-made view with the same path is refused.
  - Copied cards keep their options. For example, a tile with `name: {type: entity}`
    still shows the entity name.

## Rules the merge keeps

- **Layout unchanged.** Now and History stay exactly as they are, and the new cards go in
  a new view. `scripts/check_solar_dashboard_unique.py` (no repeated tile entity on Now)
  still passes, because Now does not change.
- **No hard-coded plug loads or locations.** Plug names come from the Where / Load
  helpers. Any Solar card that shows H5082 plugs or dump helpers is `needs-decision` and
  is not copied. Such a box on Site solar would also need a help card and its own doc in
  `docs/site-solar/` (test `test_every_dump_box_has_a_help_card_with_its_own_doc`). The
  plugs are already on Site solar through the Plugs / Socket boxes.
- **No `initial:`.** `--apply` refuses if a copied card contains it.
- No HA YAML package changes and no `.github/workflows` changes.
- This plan lives in `docs/`, not `docs/site-solar/`. Every `.md` file in `docs/site-solar/`
  must be linked from a dump box help card (same test).

## Card-by-card comparison (real export, 2026-09-29)

Phase 1 ran on `.105` on 2026-09-29 (`exported_at` 09:01): `export-dashboard` wrote the live Solar tab
(77 cards in 2 views). **View 1** has a markdown link card ("Animated solar flow"), then
the headings Thermo-Hygrometer-CAAF6F (3 tiles), BlueSolar MPPT 75/15 (7), SmartShunt
HQ2239CQYT2 (8), SmartShunt HQ2239JTRKU (8) and Sungold (22). **View 2** ("Sungold")
repeats the Sungold section. The export itself is not committed (it names a Tailscale
host; `config/dashboards/exports/*.json` is gitignored). A trimmed copy with the host
faked is the test fixture `tests/fixtures/solar_tab_export_trimmed.json`.

`python3 scripts/compare_solar_tab.py <export> --apply` gave (71 cards, the 6 headings
not counted):

| Result | Cards | What happened |
|---|---|---|
| **Already on Site solar** (`on-site-solar`) | **39** | kept as is; the table says where each one is on Now |
| **Added** to the new **Solar tab** view | **9** | 5 `history-only` (only in a History graph) + 4 `missing` |
| **Skipped** | **23** | 22 `duplicate` (view 2 repeats view 1's Sungold tiles) + 1 `skipped-private` (the animated-flow link) |

**Added, by heading** (each tile keeps `name: {type: entity}` from the Solar tab):

- **BlueSolar MPPT 75/15:** `sensor.solar_controller_battery_charging` (battery A),
  `sensor.solar_controller_battery` (battery V), `sensor.solar_controller_load`,
  `sensor.solar_controller_rssi` (diagnostic)
- **SmartShunt HQ2239CQYT2:** `sensor.battery_1_auxiliary_mode` (diagnostic)
- **SmartShunt HQ2239JTRKU:** `sensor.battery_2_auxiliary_mode` (diagnostic)
- **Sungold:** `sensor.sungold_sph302480a_battery_temperature`,
  `sensor.sungold_sph302480a_temperature_dc_dc`, `sensor.sungold_sph302480a_temperature_dc_ac`

**Decisions on the cards the tool did not copy:**

- **"Animated solar flow" markdown link** (`skipped-private`): it is not on Site solar,
  but its link is a Tailscale host name, and Tailscale names and IPs stay out of git
  (`docs/TAILSCALE.md`). It is **not copied**. Options, your call: keep the old Solar tab
  for that link, or add the card to Site solar by hand in the UI (a later `--force`
  re-seed would replace that UI edit), or a follow-up that reads the URL from a helper.
- **View 2 "Sungold"** (`duplicate`): the same 22 tiles as view 1 > Sungold, so they are
  compared once. 19 of them are already on Now > Sungold / KU outlet to Sungold, and the
  3 temperature tiles are added once.
- No card showed H5082 plugs or dump helpers (`needs-decision`: 0), and there were no
  other `no-entities` cards.

Full table (as printed by the tool):

| # | Solar tab (view > heading) | Card | Entities | Status | On Site solar / decision |
|---|---|---|---|---|---|
| 1 | view 1 > section 1 | markdown | - | skipped-private | not copied: names a Tailscale host / IP, which stays out of git (docs/TAILSCALE.md) |
| 2 | view 1 > Thermo-Hygrometer-CAAF6F | tile | `sensor.thermo_hygrometer_caaf6f_h5072_75_batt` | on-site-solar | Now > House (tile); History > SoC / % (history-graph) - keep as is (already on Site solar) |
| 3 | view 1 > Thermo-Hygrometer-CAAF6F | tile | `sensor.thermo_hygrometer_caaf6f_h5072_75_hum` | on-site-solar | Now > House (tile); History > SoC / % (history-graph) - keep as is (already on Site solar) |
| 4 | view 1 > Thermo-Hygrometer-CAAF6F | tile | `sensor.thermo_hygrometer_caaf6f_h5072_75_tempc` | on-site-solar | Now > House (tile); History > Temperature (history-graph) - keep as is (already on Site solar) |
| 5 | view 1 > BlueSolar MPPT 75/15 | tile | `sensor.solar_controller_battery_charging` | history-only | History > Amps (history-graph) - add live card to Solar tab view |
| 6 | view 1 > BlueSolar MPPT 75/15 | tile | `sensor.solar_controller_battery` | history-only | History > Volts (history-graph) - add live card to Solar tab view |
| 7 | view 1 > BlueSolar MPPT 75/15 | tile | `sensor.solar_controller_charge_state` | on-site-solar | Now > T2 24 V (tile) - keep as is (already on Site solar) |
| 8 | view 1 > BlueSolar MPPT 75/15 | tile | `sensor.solar_controller_load` | missing | add to Solar tab view |
| 9 | view 1 > BlueSolar MPPT 75/15 | tile | `sensor.solar_controller_rssi` | missing | add to Solar tab view |
| 10 | view 1 > BlueSolar MPPT 75/15 | tile | `sensor.solar_controller_solar` | on-site-solar | Now > T2 24 V (tile); Now > Dump status (why / why not) (entities); History > Watts (history-graph) - keep as is (already on Site solar) |
| 11 | view 1 > BlueSolar MPPT 75/15 | tile | `sensor.solar_controller_yield_today` | on-site-solar | Now > T2 24 V (tile) - keep as is (already on Site solar) |
| 12 | view 1 > SmartShunt HQ2239CQYT2 | tile | `sensor.battery_1_auxiliary_mode` | missing | add to Solar tab view |
| 13 | view 1 > SmartShunt HQ2239CQYT2 | tile | `sensor.battery_1_state_of_charge` | on-site-solar | Now > (badges) (entity); History > SoC / % (history-graph) - keep as is (already on Site solar) |
| 14 | view 1 > SmartShunt HQ2239CQYT2 | tile | `sensor.battery_1_consumed_ah` | on-site-solar | Now > T2 24 V (tile) - keep as is (already on Site solar) |
| 15 | view 1 > SmartShunt HQ2239CQYT2 | tile | `sensor.battery_1_current` | on-site-solar | Now > T2 24 V (tile); History > Amps (history-graph) - keep as is (already on Site solar) |
| 16 | view 1 > SmartShunt HQ2239CQYT2 | tile | `sensor.battery_1_remaining_minutes` | on-site-solar | Now > T2 24 V (tile) - keep as is (already on Site solar) |
| 17 | view 1 > SmartShunt HQ2239CQYT2 | tile | `sensor.battery_1_rssi` | on-site-solar | Now > T2 24 V (tile) - keep as is (already on Site solar) |
| 18 | view 1 > SmartShunt HQ2239CQYT2 | tile | `sensor.battery_1_power` | on-site-solar | Now > T2 24 V (tile); History > Watts (history-graph) - keep as is (already on Site solar) |
| 19 | view 1 > SmartShunt HQ2239CQYT2 | tile | `sensor.battery_1_voltage` | on-site-solar | Now > T2 24 V (tile); History > Volts (history-graph) - keep as is (already on Site solar) |
| 20 | view 1 > SmartShunt HQ2239JTRKU | tile | `sensor.battery_2_auxiliary_mode` | missing | add to Solar tab view |
| 21 | view 1 > SmartShunt HQ2239JTRKU | tile | `sensor.battery_2_state_of_charge` | on-site-solar | Now > (badges) (entity); History > SoC / % (history-graph) - keep as is (already on Site solar) |
| 22 | view 1 > SmartShunt HQ2239JTRKU | tile | `sensor.battery_2_consumed_ah` | on-site-solar | Now > KU 24 V (tile) - keep as is (already on Site solar) |
| 23 | view 1 > SmartShunt HQ2239JTRKU | tile | `sensor.battery_2_current` | on-site-solar | Now > KU 24 V (tile); History > Amps (history-graph) - keep as is (already on Site solar) |
| 24 | view 1 > SmartShunt HQ2239JTRKU | tile | `sensor.battery_2_power` | on-site-solar | Now > KU 24 V (tile); History > Watts (history-graph) - keep as is (already on Site solar) |
| 25 | view 1 > SmartShunt HQ2239JTRKU | tile | `sensor.battery_2_remaining_minutes` | on-site-solar | Now > KU 24 V (tile) - keep as is (already on Site solar) |
| 26 | view 1 > SmartShunt HQ2239JTRKU | tile | `sensor.battery_2_rssi` | on-site-solar | Now > KU 24 V (tile) - keep as is (already on Site solar) |
| 27 | view 1 > SmartShunt HQ2239JTRKU | tile | `sensor.battery_2_voltage` | on-site-solar | Now > KU 24 V (tile); History > Volts (history-graph) - keep as is (already on Site solar) |
| 28 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_pv_voltage` | on-site-solar | Now > Sungold (tile); History > Volts (history-graph) - keep as is (already on Site solar) |
| 29 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_pv_current` | on-site-solar | Now > Sungold (tile); History > Amps (history-graph) - keep as is (already on Site solar) |
| 30 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_pv_power` | on-site-solar | Now > Sungold (tile); History > Watts (history-graph) - keep as is (already on Site solar) |
| 31 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_battery_soc` | on-site-solar | Now > (badges) (entity); History > SoC / % (history-graph) - keep as is (already on Site solar) |
| 32 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_battery_voltage` | on-site-solar | Now > Sungold (tile); History > Volts (history-graph) - keep as is (already on Site solar) |
| 33 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_battery_current` | on-site-solar | Now > Sungold (tile); History > Amps (history-graph) - keep as is (already on Site solar) |
| 34 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_battery_temperature` | history-only | History > Temperature (history-graph) - add live card to Solar tab view |
| 35 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_charge_state` | on-site-solar | Now > Sungold (tile) - keep as is (already on Site solar) |
| 36 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_charging_power` | on-site-solar | Now > Sungold (tile); History > Watts (chargers) (history-graph) - keep as is (already on Site solar) |
| 37 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_ac_output_voltage` | on-site-solar | Now > Sungold (tile); History > Volts (history-graph) - keep as is (already on Site solar) |
| 38 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_ac_output_frequency` | on-site-solar | Now > Sungold (tile); History > Hz (history-graph) - keep as is (already on Site solar) |
| 39 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_load_current` | on-site-solar | Now > Sungold (tile); History > Amps (history-graph) - keep as is (already on Site solar) |
| 40 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_load_power` | on-site-solar | Now > Sungold (tile); History > Watts (history-graph) - keep as is (already on Site solar) |
| 41 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_grid_voltage` | on-site-solar | Now > KU outlet to Sungold (tile); History > Volts (history-graph) - keep as is (already on Site solar) |
| 42 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_grid_current` | on-site-solar | Now > KU outlet to Sungold (tile); History > Amps (history-graph) - keep as is (already on Site solar) |
| 43 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_grid_frequency` | on-site-solar | Now > Sungold (tile); History > Hz (history-graph) - keep as is (already on Site solar) |
| 44 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_inverter_state` | on-site-solar | Now > Sungold (tile) - keep as is (already on Site solar) |
| 45 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_temperature_dc_dc` | history-only | History > Temperature (history-graph) - add live card to Solar tab view |
| 46 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_temperature_dc_ac` | history-only | History > Temperature (history-graph) - add live card to Solar tab view |
| 47 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_fail_code` | on-site-solar | Now > Sungold (tile) - keep as is (already on Site solar) |
| 48 | view 1 > Sungold | tile | `sensor.sungold_sph302480a_inverter_error_flags` | on-site-solar | Now > Sungold (tile) - keep as is (already on Site solar) |
| 49 | view 1 > Sungold | tile | `binary_sensor.sungold_sph302480a_fault_active` | on-site-solar | Now > Sungold (tile) - keep as is (already on Site solar) |
| 50 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_pv_voltage` | duplicate | same card as #28 - not copied again (repeat of an earlier Solar card) |
| 51 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_pv_current` | duplicate | same card as #29 - not copied again (repeat of an earlier Solar card) |
| 52 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_pv_power` | duplicate | same card as #30 - not copied again (repeat of an earlier Solar card) |
| 53 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_battery_soc` | duplicate | same card as #31 - not copied again (repeat of an earlier Solar card) |
| 54 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_battery_voltage` | duplicate | same card as #32 - not copied again (repeat of an earlier Solar card) |
| 55 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_battery_current` | duplicate | same card as #33 - not copied again (repeat of an earlier Solar card) |
| 56 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_battery_temperature` | duplicate | same card as #34 - not copied again (repeat of an earlier Solar card) |
| 57 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_charge_state` | duplicate | same card as #35 - not copied again (repeat of an earlier Solar card) |
| 58 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_charging_power` | duplicate | same card as #36 - not copied again (repeat of an earlier Solar card) |
| 59 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_ac_output_voltage` | duplicate | same card as #37 - not copied again (repeat of an earlier Solar card) |
| 60 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_ac_output_frequency` | duplicate | same card as #38 - not copied again (repeat of an earlier Solar card) |
| 61 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_load_current` | duplicate | same card as #39 - not copied again (repeat of an earlier Solar card) |
| 62 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_load_power` | duplicate | same card as #40 - not copied again (repeat of an earlier Solar card) |
| 63 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_grid_voltage` | duplicate | same card as #41 - not copied again (repeat of an earlier Solar card) |
| 64 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_grid_current` | duplicate | same card as #42 - not copied again (repeat of an earlier Solar card) |
| 65 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_grid_frequency` | duplicate | same card as #43 - not copied again (repeat of an earlier Solar card) |
| 66 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_inverter_state` | duplicate | same card as #44 - not copied again (repeat of an earlier Solar card) |
| 67 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_temperature_dc_dc` | duplicate | same card as #45 - not copied again (repeat of an earlier Solar card) |
| 68 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_temperature_dc_ac` | duplicate | same card as #46 - not copied again (repeat of an earlier Solar card) |
| 69 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_fail_code` | duplicate | same card as #47 - not copied again (repeat of an earlier Solar card) |
| 70 | Sungold > Sungold | tile | `sensor.sungold_sph302480a_inverter_error_flags` | duplicate | same card as #48 - not copied again (repeat of an earlier Solar card) |
| 71 | Sungold > Sungold | tile | `binary_sensor.sungold_sph302480a_fault_active` | duplicate | same card as #49 - not copied again (repeat of an earlier Solar card) |

Totals: on-site-solar 39, history-only 5, missing 4, skipped-private 1, duplicate 22

## Order of work

1. ~~PR #13: plan, export tool, compare / apply tool, tests.~~ Merged.
2. ~~Phase 1 on `.105`: export the Solar tab.~~ Done 2026-09-29.
3. ~~Next session: `compare_solar_tab.py ... --apply`, review, fill in the table.~~ This PR.
4. **Phase 2 on `.105`:** re-seed Site solar and check the new **Solar tab** view. The
   steps are in `NEXT_STEPS.md`; `scripts/site_solar_session.sh` runs them
   (see `docs/SOLAR_HA_DASHBOARD.md`, "One session on `.105`").
5. **Your call, later:** keep, hide or remove the old Solar tab. Removing it needs a
   follow-up to `ha_label_sungold_solar.py` / `ha_label_victron_refoss.py`, which write
   into it (`lovelace.dashboard_solar`).

Re-running `--apply` with the same export gives the same seed (the generated view is
compared against Site solar **without** it, then replaced). If a newer export is taken,
`bash scripts/site_solar_session.sh --keep-export solar-compare` prints the new table.
