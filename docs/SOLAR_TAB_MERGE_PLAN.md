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

## Tools in this PR (no dashboard change yet)

- `python3 scripts/site_solar_settings.py export-dashboard [--url-path dashboard-solar] [--out FILE]`
  (read-only). It calls only `lovelace/dashboards/list` and `lovelace/config`, and writes
  `config/dashboards/exports/solar-tab.json`. Token-like values (`token=...`, `api_key`,
  `password` keys) are replaced with `<redacted>` and listed. If the url_path is wrong,
  it lists every dashboard so you can pick the right one.
- `python3 scripts/compare_solar_tab.py EXPORT [--markdown FILE] [--apply]`
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

## Card-by-card comparison

**To be filled in from the export (Phase 1).** Paste the output of
`python3 scripts/compare_solar_tab.py config/dashboards/exports/solar-tab.json` here,
then add a decision for each `no-entities` / `needs-decision` row.

| # | Solar tab (view > heading) | Card | Entities | Status | On Site solar / decision |
|---|---|---|---|---|---|
| - | *(export pending)* | | | | |

What to expect, based on the repo only (confirm with the export):
- **Probably already there** (`on-site-solar`): the Victron T2 / KU shunt and MPPT main
  readings (Now > **T2 24 V** / **KU 24 V**), and the Sungold PV, battery, load, AC-out
  and fault tiles (Now > **Sungold**).
- **Probably `history-only`**: the Sungold battery and DC-DC / DC-AC temperatures, and the
  MPPT battery V / A (History > Temperature / Volts / Amps).
- **Probably `missing`**: diagnostic MQTT sensors that only the discovery list shows, such
  as extra Victron fields and device-level entities.

## Order of work

1. **Tonight (this PR):** plan, export tool, compare / apply tool, tests. It is safe to
   merge because nothing live changes.
2. **Phase 1 on `.105`:** export the Solar tab (steps below) and bring
   `solar-tab.json` into the next session.
3. **Next session:**
   - Commit the export under `config/dashboards/exports/`.
   - Run `compare_solar_tab.py ... --apply`.
   - Review `no-entities` / `needs-decision`, and paste the table above with decisions.
   - Run the tests and `check_solar_dashboard_unique.py`, then open or update the PR.
4. **Phase 2 on `.105`:** re-seed Site solar (`--dry-run`, then `--force`), and check the
   new **Solar tab** view.
5. **Your call, later:** keep, hide or remove the old Solar tab. Removing it needs a
   follow-up to `ha_label_sungold_solar.py` / `ha_label_victron_refoss.py`, which write
   into it.

## Host steps

Only `.105` (Home Assistant) is involved: Pi 4 `.223` and Pi 5 `.240` have nothing to do. Merging this PR changes nothing live, because the Site solar seed is untouched. HA must be up for every step that uses the token, so each phase waits for it first.

**Phase 1: export the Solar tab (after this PR is merged), on `.105`, in this order**

- [ ] **a.** `cd /home/ansible/victron-ble2mqtt-integration && git pull --ff-only origin main`
- [ ] **b.** Token file for the scripts (never commit it):
  `install -m 600 /dev/null ~/.ha_token && nano ~/.ha_token` (paste a long-lived HA token), then
  `export HA_TOKEN_FILE=~/.ha_token HA_URL=http://127.0.0.1:8123`
- [ ] **c.** Wait for HA: `until curl -s -o /dev/null http://127.0.0.1:8123; do sleep 5; done`
- [ ] **d.** Backup first: `python3 scripts/site_solar_settings.py export` (helper values + live Site solar, under `.backups/site-solar/`).
- [ ] **e.** Export the Solar tab (read-only; writes only `config/dashboards/exports/solar-tab.json`): `python3 scripts/site_solar_settings.py export-dashboard`.
  - If it prints `no dashboard with url_path 'dashboard-solar'`, it lists every dashboard. Rerun with the one titled Solar: `--url-path <that url_path>`.
  - Check any `redacted a token-like value at ...` lines. Values like that are replaced with `<redacted>`.
- [ ] **f.** Look at the comparison (read-only): `python3 scripts/compare_solar_tab.py config/dashboards/exports/solar-tab.json --markdown /tmp/solar-tab-table.md`
- [ ] **g.** Bring the export to the next session. It holds only card config: entity ids and headings, with no secrets. Either:
  - commit it on a branch from `.105`, if `.105` can push: `git checkout -b solar-tab-export && git add config/dashboards/exports/solar-tab.json && git commit -m "Solar tab export" && git push -u origin solar-tab-export && git checkout main`; or
  - `cat config/dashboards/exports/solar-tab.json` and paste it into the session.
  Then delete the local copy, so a later `git pull` that adds the same file does not stop on an untracked file: `rm config/dashboards/exports/solar-tab.json`.
- [ ] **h.** `rm ~/.ha_token && unset HA_TOKEN_FILE`

**Phase 2: add the missing cards (next session), then on `.105`**

In the session: `python3 scripts/compare_solar_tab.py config/dashboards/exports/solar-tab.json --apply` appends one new view, **Solar tab** (`/site-solar/solar-tab`), with only the missing cards. Then review each `no-entities` / `needs-decision` row, update the table in `docs/SOLAR_TAB_MERGE_PLAN.md`, run the tests, and update the PR. After it is merged:

- [ ] **a.** `cd /home/ansible/victron-ble2mqtt-integration && git pull --ff-only origin main` (if it stops on `config/dashboards/exports/solar-tab.json`, run `rm config/dashboards/exports/solar-tab.json` and pull again)
- [ ] **b.** `install -m 600 /dev/null ~/.ha_token && nano ~/.ha_token`, then `export HA_TOKEN_FILE=~/.ha_token HA_URL=http://127.0.0.1:8123`
- [ ] **c.** `until curl -s -o /dev/null http://127.0.0.1:8123; do sleep 5; done`
- [ ] **d.** `python3 scripts/site_solar_settings.py export` (backup of helpers + live Site solar)
- [ ] **e.** `python3 scripts/save_solar_plant_storage_dashboard.py --dry-run`, then `python3 scripts/save_solar_plant_storage_dashboard.py --force`. `--force` backs up the live dashboard first, then replaces it with the seed. Any Site solar UI edits made since the last seed are replaced too. Undo: `python3 scripts/site_solar_settings.py restore --from <folder> --dashboard`.
- [ ] **f.** `rm ~/.ha_token && unset HA_TOKEN_FILE`
- [ ] **g.** Check Site solar > **Solar tab**: every card from the old Solar tab is now either there or already elsewhere on Site solar (see the table). Now and History are unchanged.
- [ ] **h.** Your decision, no rush: **keep, hide or remove the old Solar tab.**
  - **Keep:** nothing to do.
  - **Hide:** Settings > Dashboards > Solar, turn off **Show in sidebar**.
  - **Remove:** Settings > Dashboards > Solar > Delete. Only do this after the Phase 1 export is committed. Also, `scripts/ha_label_sungold_solar.py` and `scripts/ha_label_victron_refoss.py` still write sections into that dashboard (`lovelace.dashboard_solar`) and fail if it is gone, so removing it needs a small follow-up change to those scripts first.
