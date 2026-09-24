#!/usr/bin/env python3
"""Re-layout Solar panels group: shared HA /api/states link + clean grid (idempotent)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "flows" / "solar_plant_diagram.json"
TAB = "solar-plant-diagram-tab"
BLUE_GROUP = "solar-plant-diagram-group"
GROUP_ID = "solar-panels-8-group"
LINK_HA_STATES = "ha-all-states-bus"

PREP_FUNC = (
    "const base = global.get('haBaseUrl') || 'http://127.0.0.1:8123';\n"
    "const token = global.get('haToken') || '';\n"
    "if (!token) {\n"
    "    node.status({ fill: 'red', shape: 'ring', text: 'no HA token' });\n"
    "    return null;\n"
    "}\n"
    "msg.url = base + '/api/states';\n"
    "msg.method = 'GET';\n"
    "msg.headers = { Authorization: 'Bearer ' + token };\n"
    "return msg;"
)

GROUP = {"x": 74, "y": 365, "w": 1320, "h": 480}

# Top of orange: link in + fan-out only (no duplicate poll nodes)
HA_LI_X, CALC_X, TOP_Y = 200, 380, 410
ROW_YS = (540, 635, 730, 825)
LO_X, ROW_LI_X = 520, 580
COL_A, COL_B = 660, 820
COMMENT_X = 980

ROW_HEADERS = (
    (540, "Row 1: panels 1+2  ->  T2 MPPT #1"),
    (635, "Row 2: panels 3+4  ->  KU MPPT #2"),
    (730, "Row 3: panels 5+6  ->  KU MPPT #3"),
    (825, "Row 4: panels 7+8  ->  KU PWM"),
)

PANEL_STATUS_FUNC = (
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
    "return null;"
)

POLL_NODES = ("panel-inject", "panel-prep", "panel-http")


def by_id(flow: list) -> dict:
    return {n["id"]: n for n in flow if n.get("id")}


def panel_xy(panel_num: int) -> tuple[int, int]:
    row = (panel_num - 1) // 2
    y = ROW_YS[row]
    x = COL_A if panel_num % 2 == 1 else COL_B
    return x, y


def ensure_shared_ha_states(flow: list) -> None:
    ids = by_id(flow)
    inject = ids.get("inject-tick")
    blue = ids.get(BLUE_GROUP)
    if not inject or not blue:
        return

    new: list[dict] = []
    if "shared-states-prep" not in ids:
        new.append(
            {
                "id": "shared-states-prep",
                "type": "function",
                "z": TAB,
                "g": BLUE_GROUP,
                "name": "GET all states (panels)",
                "func": PREP_FUNC,
                "outputs": 1,
                "timeout": "",
                "noerr": 0,
                "initialize": "",
                "finalize": "",
                "libs": [],
                "x": 120,
                "y": 280,
                "wires": [["shared-states-http"]],
            }
        )
        blue["nodes"].append("shared-states-prep")

    if "shared-states-http" not in ids:
        new.append(
            {
                "id": "shared-states-http",
                "type": "http request",
                "z": TAB,
                "g": BLUE_GROUP,
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
                "x": 320,
                "y": 280,
                "wires": [["shared-states-lo"]],
            }
        )
        blue["nodes"].append("shared-states-http")

    if "shared-states-lo" not in ids:
        new.append(
            {
                "id": "shared-states-lo",
                "type": "link out",
                "z": TAB,
                "g": BLUE_GROUP,
                "name": "to panel compute",
                "links": [LINK_HA_STATES],
                "x": 500,
                "y": 280,
                "wires": [],
            }
        )
        blue["nodes"].append("shared-states-lo")

    flow.extend(new)
    ids = by_id(flow)
    inject = ids["inject-tick"]
    wires = inject.get("wires") or []
    if not any("shared-states-prep" in (w or []) for w in wires):
        wires.append(["shared-states-prep"])
        inject["wires"] = wires


def ensure_panel_link_in(flow: list) -> None:
    ids = by_id(flow)
    group = ids[GROUP_ID]
    if "panel-states-li" not in ids:
        flow.append(
            {
                "id": "panel-states-li",
                "type": "link in",
                "z": TAB,
                "g": GROUP_ID,
                "name": "HA states",
                "links": [LINK_HA_STATES],
                "x": HA_LI_X,
                "y": TOP_Y,
                "wires": [["panel-calc"]],
            }
        )
        group["nodes"].append("panel-states-li")
    else:
        n = ids["panel-states-li"]
        n["x"], n["y"] = HA_LI_X, TOP_Y
        n["wires"] = [["panel-calc"]]

    calc = ids.get("panel-calc")
    if calc:
        calc["name"] = "fan-out 8 panels"
        calc["x"], calc["y"] = CALC_X, TOP_Y


def remove_orphan_poll_nodes(flow: list) -> None:
    ids = by_id(flow)
    group = ids.get(GROUP_ID)
    if not group:
        return
    for nid in POLL_NODES:
        if nid in group["nodes"]:
            group["nodes"].remove(nid)
    # Remove from flow entirely so they do not clutter the canvas
    flow[:] = [n for n in flow if n.get("id") not in POLL_NODES]


def ensure_row_headers(flow: list) -> None:
    ids = by_id(flow)
    group = ids[GROUP_ID]
    for i, (y, text) in enumerate(ROW_HEADERS, start=1):
        hid = f"panel-row-hdr-{i}"
        if hid not in ids:
            flow.append(
                {
                    "id": hid,
                    "type": "comment",
                    "z": TAB,
                    "g": GROUP_ID,
                    "name": text,
                    "info": "",
                    "x": COMMENT_X,
                    "y": y,
                    "wires": [],
                }
            )
            group["nodes"].append(hid)
        else:
            ids[hid]["x"] = COMMENT_X
            ids[hid]["y"] = y
            ids[hid]["name"] = text


def ensure_link_nodes(flow: list) -> None:
    ids = by_id(flow)
    group = ids[GROUP_ID]
    new: list[dict] = []
    lo_ids: list[str] = []

    for i in range(1, 9):
        link_id = f"panel-wire-{i}"
        lo_id = f"panel-lo-{i}"
        li_id = f"panel-li-{i}"
        px, py = panel_xy(i)
        lo_ids.append(lo_id)
        if lo_id not in ids:
            new.append(
                {
                    "id": lo_id,
                    "type": "link out",
                    "z": TAB,
                    "g": GROUP_ID,
                    "name": str(i),
                    "links": [link_id],
                    "x": LO_X,
                    "y": py,
                    "wires": [],
                }
            )
        if li_id not in ids:
            new.append(
                {
                    "id": li_id,
                    "type": "link in",
                    "z": TAB,
                    "g": GROUP_ID,
                    "name": str(i),
                    "links": [link_id],
                    "x": ROW_LI_X,
                    "y": py,
                    "wires": [[f"panel-{i}-box"]],
                }
            )
    flow.extend(new)
    ids = by_id(flow)
    calc = ids.get("panel-calc")
    if calc:
        calc["wires"] = [[lid] for lid in lo_ids]

    for i in range(1, 9):
        lo_id = f"panel-lo-{i}"
        li_id = f"panel-li-{i}"
        px, py = panel_xy(i)
        if lo_id in ids:
            ids[lo_id]["x"], ids[lo_id]["y"] = LO_X, py
            ids[lo_id]["name"] = str(i)
        if li_id in ids:
            ids[li_id]["x"], ids[li_id]["y"] = ROW_LI_X, py
            ids[li_id]["name"] = str(i)
        pid = f"panel-{i}-box"
        if pid in ids:
            ids[pid]["x"], ids[pid]["y"] = px, py
            ids[pid]["func"] = PANEL_STATUS_FUNC
            ids[pid]["wires"] = []

    for nid in lo_ids + [f"panel-li-{j}" for j in range(1, 9)]:
        if nid not in group["nodes"]:
            group["nodes"].append(nid)

    # Retire old MPPT comment nodes (replaced by row headers)
    for lid in ("panel-link-1", "panel-link-2", "panel-link-3", "panel-link-4"):
        if lid in group["nodes"]:
            group["nodes"].remove(lid)
    flow[:] = [n for n in flow if n.get("id") not in ("panel-link-1", "panel-link-2", "panel-link-3", "panel-link-4")]


def apply_group_frame(flow: list) -> None:
    ids = by_id(flow)
    group = ids[GROUP_ID]
    group["x"] = GROUP["x"]
    group["y"] = GROUP["y"]
    group["w"] = GROUP["w"]
    group["h"] = GROUP["h"]
    if "panel-comment" in ids:
        ids["panel-comment"]["x"] = 420
        ids["panel-comment"]["y"] = 385
        ids["panel-comment"]["name"] = (
            "Panel grid only. HA /api/states comes from blue group (link). Drag Panel 1-8 to match roof."
        )


def main() -> int:
    flow = json.loads(FLOW.read_text(encoding="utf-8"))
    if GROUP_ID not in {n.get("id") for n in flow}:
        print("panel group missing")
        return 1
    ensure_shared_ha_states(flow)
    ensure_panel_link_in(flow)
    remove_orphan_poll_nodes(flow)
    ensure_link_nodes(flow)
    ensure_row_headers(flow)
    apply_group_frame(flow)
    FLOW.write_text(json.dumps(flow, indent=2), encoding="utf-8")
    wire = ROOT / "scripts" / "wire_panels_to_chargers.py"
    if wire.is_file():
        import subprocess
        import sys

        subprocess.run([sys.executable, str(wire)], check=True)
    print(f"layout v4 applied to {FLOW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
