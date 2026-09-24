#!/usr/bin/env python3
"""Add 8-panel group + computed poll chain to flows/solar_plant_diagram.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "flows" / "solar_plant_diagram.json"

PANEL_CALC_FUNC = r"""const lib = global.get('solarComputed');
if (!lib || !lib.computeSolarDerived) {
    node.status({ fill: 'red', shape: 'ring', text: 'no solarComputed lib' });
    return null;
}
if (!Array.isArray(msg.payload)) {
    node.status({ fill: 'red', shape: 'ring', text: 'bad /api/states' });
    return null;
}
const d = lib.computeSolarDerived(msg.payload);
flow.set('solarComputedLast', d);
node.status({ fill: 'green', shape: 'dot', text: 'derived ok' });
const panels = d.panels || [];
while (panels.length < 8) panels.push({ label: '?', est_w: null, connects: '' });
return panels.map((p) => [{ payload: p }]);"""

PANEL_BOX_FUNC = r"""const p = msg.payload || {};
const w = p.est_w == null ? 'n/a' : String(p.est_w) + ' W';
const dest = (p.connects || '').split('->').pop();
const tail = dest ? dest.trim() : '';
node.status({
    fill: p.est_w != null && p.est_w > 0 ? 'green' : 'grey',
    shape: 'dot',
    text: (p.label || 'P') + ' ' + w + '\n' + tail
});
return null;"""

PREP_FUNC = r"""const base = global.get('haBaseUrl') || 'http://127.0.0.1:8123';
const token = global.get('haToken') || '';
if (!token) {
    node.status({ fill: 'red', shape: 'ring', text: 'no HA token' });
    return null;
}
msg.url = base + '/api/states';
msg.method = 'GET';
msg.headers = { Authorization: 'Bearer ' + token };
return msg;"""


def panel_box_node(pid: int, x: int, y: int) -> dict:
    return {
        "id": f"panel-{pid}-box",
        "type": "function",
        "z": "solar-plant-diagram-tab",
        "g": "solar-panels-8-group",
        "name": f"Panel {pid}",
        "func": PANEL_BOX_FUNC,
        "outputs": 0,
        "timeout": "",
        "noerr": 0,
        "initialize": "",
        "finalize": "",
        "libs": [],
        "x": x,
        "y": y,
        "wires": [],
    }


def main() -> int:
    flow = json.loads(FLOW.read_text(encoding="utf-8"))
    ids = {n.get("id") for n in flow if n.get("id")}
    if "solar-panels-8-group" in ids:
        print("panel group already present")
        return 0

    panel_ids = [f"panel-{i}-box" for i in range(1, 9)]
    group = {
        "id": "solar-panels-8-group",
        "type": "group",
        "z": "solar-plant-diagram-tab",
        "name": "Solar panels (8x 2s strings)",
        "style": {"label": True, "fill": "#fff3e0", "color": "#000000"},
        "nodes": [
            "panel-comment",
            "panel-inject",
            "panel-prep",
            "panel-http",
            "panel-calc",
            *panel_ids,
        ],
        "x": 54,
        "y": 340,
        "w": 980,
        "h": 320,
    }

    positions = [
        (820, 440),
        (980, 440),
        (820, 500),
        (980, 500),
        (820, 560),
        (980, 560),
        (820, 620),
        (980, 620),
    ]
    new_nodes = [
        group,
        {
            "id": "panel-comment",
            "type": "comment",
            "z": "solar-plant-diagram-tab",
            "g": "solar-panels-8-group",
            "name": "Est W per panel = half string W (T2 MPPT | 2x T2 est on KU MPPT2/3 | PWM est). Drag boxes to match roof layout.",
            "info": "",
            "x": 420,
            "y": 380,
            "wires": [],
        },
        {
            "id": "panel-inject",
            "type": "inject",
            "z": "solar-plant-diagram-tab",
            "g": "solar-panels-8-group",
            "name": "Poll panels 5s",
            "props": [{"p": "payload"}],
            "repeat": "5",
            "crontab": "",
            "once": True,
            "onceDelay": "2",
            "topic": "",
            "payload": "",
            "payloadType": "date",
            "x": 130,
            "y": 420,
            "wires": [["panel-prep"]],
        },
        {
            "id": "panel-prep",
            "type": "function",
            "z": "solar-plant-diagram-tab",
            "g": "solar-panels-8-group",
            "name": "GET all HA states",
            "func": PREP_FUNC,
            "outputs": 1,
            "timeout": "",
            "noerr": 0,
            "initialize": "",
            "finalize": "",
            "libs": [],
            "x": 320,
            "y": 420,
            "wires": [["panel-http"]],
        },
        {
            "id": "panel-http",
            "type": "http request",
            "z": "solar-plant-diagram-tab",
            "g": "solar-panels-8-group",
            "name": "HA /api/states",
            "method": "use",
            "ret": "obj",
            "paytoqs": "ignore",
            "url": "",
            "tls": "",
            "persist": False,
            "proxy": "",
            "insecureHTTPParser": False,
            "authType": "",
            "senderr": False,
            "headers": [],
            "x": 500,
            "y": 420,
            "wires": [["panel-calc"]],
        },
        {
            "id": "panel-calc",
            "type": "function",
            "z": "solar-plant-diagram-tab",
            "g": "solar-panels-8-group",
            "name": "compute + fan-out 8",
            "func": PANEL_CALC_FUNC,
            "outputs": 8,
            "timeout": "",
            "noerr": 0,
            "initialize": "",
            "finalize": "",
            "libs": [],
            "x": 700,
            "y": 420,
            "wires": [[f"panel-{i}-box"] for i in range(1, 9)],
        },
    ]
    for i, (x, y) in enumerate(positions, start=1):
        new_nodes.append(panel_box_node(i, x, y))

    # connection labels (link nodes) between strings and buses
    links = [
        (760, 470, "-> T2 MPPT #1"),
        (760, 530, "-> KU MPPT #2"),
        (760, 590, "-> KU MPPT #3"),
        (760, 650, "-> KU PWM"),
    ]
    for idx, (x, y, label) in enumerate(links):
        nid = f"panel-link-{idx + 1}"
        new_nodes.append(
            {
                "id": nid,
                "type": "comment",
                "z": "solar-plant-diagram-tab",
                "g": "solar-panels-8-group",
                "name": label,
                "info": "",
                "x": x,
                "y": y,
                "wires": [],
            }
        )
        group["nodes"].append(nid)

    flow.extend(new_nodes)
    FLOW.write_text(json.dumps(flow, indent=2), encoding="utf-8")
    print(f"added solar-panels-8-group with {len(panel_ids)} panel boxes to {FLOW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
