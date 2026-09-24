# Solar diagrams policy (HA data + Node-RED editor)

## Roles

| Tool | Role |
|------|------|
| **Home Assistant (`.105`)** | **Data and operator tiles** -- template sensors, Site solar dashboard, Energy, dump helpers. Single source of sensor truth. |
| **Node-RED (`.105` `:1880`)** | **Build/edit/view** the solar topology diagram -- drag nodes, connect wires, live status from HA REST. Does **not** replace HA entities. |

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
