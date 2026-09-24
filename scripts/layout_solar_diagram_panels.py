#!/usr/bin/env python3
"""Re-layout Solar panels (8x) group in flows/solar_plant_diagram.json (idempotent)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "flows" / "solar_plant_diagram.json"
TAB = "solar-plant-diagram-tab"
GROUP_ID = "solar-panels-8-group"

# Align with Live HA clamps group (x=74); sit fully below y=39+302=341
GROUP = {"x": 74, "y": 370, "w": 1300, "h": 440}

POSITIONS = {
    "panel-comment": (480, 395),
    "panel-inject": (140, 435),
    "panel-prep": (300, 435),
    "panel-http": (460, 435),
    "panel-calc": (640, 435),
}

# Two columns: odd panels left, even right; four string rows
ROW_YS = (530, 620, 710, 800)
COL_ODD = 220
COL_EVEN = 380
COMMENT_X = 520

PANEL_IDS = [f"panel-{i}-box" for i in range(1, 9)]
LINK_COMMENT_IDS = [f"panel-link-{i}" for i in range(1, 5)]


def link_out_node(link_id: str, nid: str, name: str, x: int, y: int) -> dict:
    return {
        "id": nid,
        "type": "link out",
        "z": TAB,
        "g": GROUP_ID,
        "name": name,
        "links": [link_id],
        "x": x,
        "y": y,
        "wires": [],
    }


def link_in_node(link_id: str, nid: str, name: str, x: int, y: int, wires_to: list[str]) -> dict:
    return {
        "id": nid,
        "type": "link in",
        "z": TAB,
        "g": GROUP_ID,
        "name": name,
        "links": [link_id],
        "x": x,
        "y": y,
        "wires": [wires_to],
    }


def panel_xy(panel_num: int) -> tuple[int, int]:
    row = (panel_num - 1) // 2
    y = ROW_YS[row]
    x = COL_ODD if panel_num % 2 == 1 else COL_EVEN
    return x, y


def ensure_link_nodes(flow: list) -> None:
    by_id = {n["id"]: n for n in flow if n.get("id")}
    group = by_id[GROUP_ID]
    new_nodes: list[dict] = []
    lo_ids: list[str] = []
    li_ids: list[str] = []

    for i in range(1, 9):
        link_id = f"panel-wire-{i}"
        lo_id = f"panel-lo-{i}"
        li_id = f"panel-li-{i}"
        px, py = panel_xy(i)
        lo_ids.append(lo_id)
        li_ids.append(li_id)
        if lo_id not in by_id:
            new_nodes.append(
                link_out_node(link_id, lo_id, f"to P{i}", px + 120, py)
            )
        if li_id not in by_id:
            new_nodes.append(
                link_in_node(link_id, li_id, f"P{i} in", px - 40, py, [f"panel-{i}-box"])
            )

    calc = by_id.get("panel-calc")
    if calc:
        calc["wires"] = [[lo_id] for lo_id in lo_ids]

    for n in flow:
        if n.get("id") in PANEL_IDS:
            n["wires"] = []

    for i, lid in enumerate(LINK_COMMENT_IDS):
        if lid in by_id:
            by_id[lid]["x"] = COMMENT_X
            by_id[lid]["y"] = ROW_YS[i] + 8

    extra = lo_ids + li_ids
    for nid in extra:
        if nid not in group["nodes"]:
            group["nodes"].append(nid)

    flow.extend(new_nodes)


def apply_positions(flow: list) -> None:
    by_id = {n["id"]: n for n in flow if n.get("id")}
    group = by_id.get(GROUP_ID)
    if not group:
        raise SystemExit(f"missing {GROUP_ID}")

    group["x"] = GROUP["x"]
    group["y"] = GROUP["y"]
    group["w"] = GROUP["w"]
    group["h"] = GROUP["h"]

    for nid, (x, y) in POSITIONS.items():
        if nid in by_id:
            by_id[nid]["x"] = x
            by_id[nid]["y"] = y

    for i in range(1, 9):
        pid = f"panel-{i}-box"
        if pid in by_id:
            by_id[pid]["x"], by_id[pid]["y"] = panel_xy(i)
            by_id[pid]["func"] = (
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

    for i, lo_id in enumerate([f"panel-lo-{j}" for j in range(1, 9)], start=1):
        if lo_id in by_id:
            px, py = panel_xy(i)
            by_id[lo_id]["x"] = px + 120
            by_id[lo_id]["y"] = py

    for i in range(1, 9):
        li_id = f"panel-li-{i}"
        if li_id in by_id:
            px, py = panel_xy(i)
            by_id[li_id]["x"] = px - 40
            by_id[li_id]["y"] = py


def main() -> int:
    flow = json.loads(FLOW.read_text(encoding="utf-8"))
    if GROUP_ID not in {n.get("id") for n in flow}:
        print("panel group missing; run patch_solar_diagram_panels.py first")
        return 1
    ensure_link_nodes(flow)
    apply_positions(flow)
    FLOW.write_text(json.dumps(flow, indent=2), encoding="utf-8")
    print(f"layout applied to {FLOW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
