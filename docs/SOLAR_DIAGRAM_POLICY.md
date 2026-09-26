# Solar diagrams policy (HA data + Node-RED editor)

## Roles

| Tool | Role |
|------|------|
| **Home Assistant (`.105`)** | **Device sensors and Site solar tiles** -- Victron, Sungold, EM16 (live wrappers). Energy sankey, dump helpers. No derived site totals on `/site-solar`. |
| **Node-RED (`.105` `:1880`)** | **Diagram editor** plus the **only derived-math engine** (`scripts/nodered_solar_computed.js`). HTML tiles: `/solar/computed`. Prometheus text of those same numbers: `/solar/metrics`. |
| **Grafana Canvas (`.107` `:3000`)** | **Detailed one-line view** of that exposition, plus H5082 socket tables (`solar_plant_socket`). Not a second calculator. Dashboard uid `solar-plant-oneline`. |

See [SOLAR_HA_NODERED_SPLIT.md](SOLAR_HA_NODERED_SPLIT.md).

Stock Home Assistant cannot place this two-bus plant on operator-drawn wires. Built-in [Energy](https://www.home-assistant.io/docs/energy/) / [power Sankey](https://www.home-assistant.io/dashboards/energy/) is the simple sources-home-devices picture and stays that picture. [Picture elements](https://www.home-assistant.io/dashboards/picture-elements/) only overlays badges on a static image.

[Grafana Canvas](https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/visualizations/canvas/) (this host runs `grafana/grafana:13.0.2`) places metric elements and sets connection **direction** from a numeric field: positive = forward along the wire, negative = reverse, zero = no arrow ([what’s new in 12.2](https://grafana.com/docs/grafana/latest/whatsnew/whats-new-in-v12-2/)). Line style in that manual is solid, dashed, or dotted. The manual does **not** describe particle or speed animation, so this dashboard does not invent one.

Do **not** re-add the retired HA template totals. Do **not** recompute watts in PromQL. `config/packages/solar_ku_estimates.yaml` stays as it is (deprecated, still installed); the one-line does not read it.

## Retired for solar site diagrams

- Mermaid HTML/markdown flowcharts for the plant
- SVG `solar-flow` proxy (`:8765`)
- Using Node-RED as an MQTT bridge **instead of** HA for solar clamps

Architecture mermaid in other repos (alfa-ai ROADMAP, etc.) is unrelated.

## Official references

- [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/)
- [Node-RED Docker](https://nodered.org/docs/getting-started/docker)
- [Node-RED editor workspace](https://nodered.org/docs/user-guide/editor/workspace/)

## Runbook

See [SOLAR_NODERED_OPERATOR.md](SOLAR_NODERED_OPERATOR.md).
