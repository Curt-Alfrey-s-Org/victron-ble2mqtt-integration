# Dashboard exports (read-only snapshots from the live Home Assistant)

`solar-tab.json` is the sidebar **Solar** dashboard (`/dashboard-solar`). It exists
only in the live HA, so it is exported here so its cards can be compared with Site
solar (`config/dashboards/solar-plant.yaml`):

```bash
bash scripts/site_solar_session.sh solar-compare      # token, wait for HA, backup, export, compare
# or by hand:
HA_TOKEN_FILE=~/.ha_token python3 scripts/site_solar_settings.py export-dashboard
python3 scripts/compare_solar_tab.py                  # default: config/dashboards/exports/solar-tab.json
```

**Do not commit exports.** `config/dashboards/exports/*.json` is gitignored: a live export
can name a Tailscale host (the Solar tab's "Animated solar flow" link does), and those stay
out of git (`docs/TAILSCALE.md`). `site_solar_session.sh` deletes an export it created at
the end of the run unless you pass `--keep-export`. The comparison result that matters is
recorded in [docs/SOLAR_TAB_MERGE_PLAN.md](../../../docs/SOLAR_TAB_MERGE_PLAN.md), and a
trimmed, host-faked copy for tests is `tests/fixtures/solar_tab_export_trimmed.json`.

The export holds card config only (entity ids, headings, card options). Values that look
like tokens (`token=...`, `api_key`, `password` keys) are replaced with `<redacted>`
before the file is written. Check the `redacted ...` lines the export prints.
Nothing here is loaded by Home Assistant.
