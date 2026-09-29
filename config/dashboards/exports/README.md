# Dashboard exports (read-only snapshots from the live Home Assistant)

`solar-tab.json` is the sidebar **Solar** dashboard (`/dashboard-solar`). It exists
only in the live HA, so it is exported here so its cards can be compared with Site
solar (`config/dashboards/solar-plant.yaml`):

```bash
HA_TOKEN_FILE=~/.ha_token python3 scripts/site_solar_settings.py export-dashboard
python3 scripts/compare_solar_tab.py config/dashboards/exports/solar-tab.json
```

The export holds card config only (entity ids, headings, card options). Values that look
like tokens (`token=...`, `api_key`, `password` keys) are replaced with `<redacted>`
before the file is written. Check the `redacted ...` lines the export prints.
Nothing here is loaded by Home Assistant.

See [docs/SOLAR_TAB_MERGE_PLAN.md](../../../docs/SOLAR_TAB_MERGE_PLAN.md).
