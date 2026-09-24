#!/usr/bin/env python3
"""Wire panel pairs to charger status nodes (T2 MPPT HA + KU/PWM computed)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "flows" / "solar_plant_diagram.json"
TAB = "solar-plant-diagram-tab"
BLUE = "solar-plant-diagram-group"
ORANGE = "solar-panels-8-group"

PANEL_PASS_FUNC = (
    "const p = msg.payload || {};\n"
    "const w = p.est_w == null ? 'n/a' : String(p.est_w) + ' W';\n"
    "const hop = (p.connects || '').split('->').pop();\n"
    "const dest = hop ? hop.trim() : '';\n"
    "const line2 = (p.string || '') + (dest ? ' -> ' + dest : '');\n"
    "node.status({\n"
    "    fill: p.est_w != null && p.est_w > 0 ? 'green' : 'grey',\n"
    "    shape: 'dot',\n"
    "    text: (p.label || 'P') + ' ' + w + '\\n' + line2\n"
    "});\n"
    "return msg;"
)

T2_FMT_FUNC = (
    "const d = flow.get('solarComputedLast') || {};\n"
    "const panels = d.panels || [];\n"
    "const est = [0, 1].map((i) => panels[i]?.est_w).filter((x) => x != null);\n"
    "const estTxt = est.length ? est.join('+') + ' W est' : 'est n/a';\n"
    "let devTxt = 'device n/a';\n"
    "if (msg.payload && msg.payload.state !== undefined) {\n"
    "    const st = msg.payload.state;\n"
    "    const u = msg.payload.attributes && msg.payload.attributes.unit_of_measurement\n"
    "        ? msg.payload.attributes.unit_of_measurement : 'W';\n"
    "    devTxt = 'device ' + st + ' ' + u;\n"
    "    msg.payload = { entity: msg.entity, state: st, unit: u };\n"
    "} else if (d.t2_mppt_w != null) {\n"
    "    devTxt = 'device ' + d.t2_mppt_w + ' W';\n"
    "}\n"
    "node.status({ fill: 'green', shape: 'dot', text: devTxt + ' | ' + estTxt });\n"
    "return msg;"
)

KU_MPPT2_STATUS = (
    "const d = flow.get('solarComputedLast') || {};\n"
    "const v = d.ku_victron_mppt23_est_w;\n"
    "const half = v == null ? null : Math.round((v / 2) * 10) / 10;\n"
    "node.status({ fill: 'green', shape: 'dot', text: 'KU MPPT #2 est ' + (half == null ? 'n/a' : half + ' W') });\n"
    "return null;"
)

KU_MPPT3_STATUS = (
    "const d = flow.get('solarComputedLast') || {};\n"
    "const v = d.ku_victron_mppt23_est_w;\n"
    "const half = v == null ? null : Math.round((v / 2) * 10) / 10;\n"
    "node.status({ fill: 'green', shape: 'dot', text: 'KU MPPT #3 est ' + (half == null ? 'n/a' : half + ' W') });\n"
    "return null;"
)

KU_PWM_STATUS = (
    "const d = flow.get('solarComputedLast') || {};\n"
    "const v = d.ku_pwm_est_w;\n"
    "node.status({ fill: 'green', shape: 'dot', text: 'KU PWM est ' + (v == null ? 'n/a' : v + ' W') });\n"
    "return null;"
)

# panel pair (odd, even), row y, charger status node id, optional ent-0 ids for row 1
ROW_SPECS = (
    (1, 2, 540, "ent-0-fmt", "T2 MPPT solar status", T2_FMT_FUNC, True),
    (3, 4, 635, "charger-ku-mppt2-status", "KU MPPT #2 (est)", KU_MPPT2_STATUS, False),
    (5, 6, 730, "charger-ku-mppt3-status", "KU MPPT #3 (est)", KU_MPPT3_STATUS, False),
    (7, 8, 825, "charger-ku-pwm-status", "KU PWM (est)", KU_PWM_STATUS, False),
)


def by_id(flow: list) -> dict:
    return {n["id"]: n for n in flow if n.get("id")}


def ensure_status_node(flow: list, node_id: str, name: str, func: str, x: int, y: int) -> None:
    ids = by_id(flow)
    if node_id in ids:
        n = ids[node_id]
        n["name"] = name
        n["func"] = func
        n["x"], n["y"] = x, y
        n["outputs"] = 0
        return
    blue = ids[BLUE]
    flow.append(
        {
            "id": node_id,
            "type": "function",
            "z": TAB,
            "g": BLUE,
            "name": name,
            "func": func,
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
    )
    if node_id not in blue["nodes"]:
        blue["nodes"].append(node_id)


def remove_panel_link_nodes(flow: list) -> None:
    ids = by_id(flow)
    group = ids.get(ORANGE)
    drop = [f"panel-lo-{i}" for i in range(1, 9)] + [f"panel-li-{i}" for i in range(1, 9)]
    flow[:] = [n for n in flow if n.get("id") not in drop]
    if group:
        group["nodes"] = [n for n in group["nodes"] if n not in drop]


def main() -> int:
    preserve = "--preserve-positions" in sys.argv
    flow = json.loads(FLOW.read_text(encoding="utf-8"))
    ids = by_id(flow)
    remove_panel_link_nodes(flow)
    ids = by_id(flow)
    calc = ids.get("panel-calc")
    if not calc:
        raise SystemExit("panel-calc missing")

    for p_odd, p_even, y, status_id, status_name, status_func, is_t2 in ROW_SPECS:
        ids = by_id(flow)
        sx = ids[status_id]["x"] if status_id in ids else 1180
        sy = ids[status_id]["y"] if status_id in ids else y
        ensure_status_node(flow, status_id, status_name, status_func, sx, sy)
        ids = by_id(flow)
        b1 = ids[f"panel-{p_odd}-box"]
        b2 = ids[f"panel-{p_even}-box"]
        b1["func"] = b2["func"] = PANEL_PASS_FUNC
        b1["outputs"] = b2["outputs"] = 1
        if not preserve:
            b1["x"], b1["y"] = 660, y
            b2["x"], b2["y"] = 820, y
        b1["wires"] = [[f"panel-{p_even}-box"]]
        b2["wires"] = [[status_id]]

        if is_t2:
            if not preserve:
                ids["ent-0-fn"]["x"], ids["ent-0-fn"]["y"] = 1020, y
                ids["ent-0-http"]["x"], ids["ent-0-http"]["y"] = 1100, y
                ids["ent-0-fmt"]["x"], ids["ent-0-fmt"]["y"] = 1180, y
            ids["ent-0-fmt"]["name"] = status_name
            ids["ent-0-fmt"]["func"] = status_func
            ids["ent-0-fmt"]["outputs"] = 0
            if ids["ent-0-fn"]["wires"] != [["ent-0-http"]]:
                ids["ent-0-fn"]["wires"] = [["ent-0-http"]]
            if ids["ent-0-http"]["wires"] != [["ent-0-fmt"]]:
                ids["ent-0-http"]["wires"] = [["ent-0-fmt"]]
        elif status_id in ids:
            ids[status_id]["func"] = status_func
            ids[status_id]["outputs"] = 0

        calc["wires"][p_odd - 1] = [f"panel-{p_odd}-box"]
        calc["wires"][p_even - 1] = []

    c = ids.get("panel-comment")
    if c:
        c["name"] = (
            "Panel rows wire into charger status at right (T2 = HA + est; KU/PWM = computed). "
            "Blue inject still polls T2 GET."
        )

    FLOW.write_text(json.dumps(flow, indent=2), encoding="utf-8")
    print("panel->charger wires applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
