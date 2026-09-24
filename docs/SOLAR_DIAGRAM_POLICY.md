# Solar diagrams policy (HA data + Node-RED editor)

## Roles

| Tool | Role |
|------|------|
| **Home Assistant (`.105`)** | **Device sensors and Site solar tiles** -- Victron, Sungold, EM16 (live wrappers). Energy, dump helpers. No derived site totals on `/site-solar`. |
| **Node-RED (`.105` `:1880`)** | **Diagram editor** plus **computed meters** (`/solar/computed`) -- reads HA REST, shows jumper / KU est / share tiles removed from HA. |

See [SOLAR_HA_NODERED_SPLIT.md](SOLAR_HA_NODERED_SPLIT.md).

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
