#!/usr/bin/env python3
"""Ensure full HA data paths are wired (preserve node x/y)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "flows" / "solar_plant_diagram.json"
BLUE = "solar-plant-diagram-group"
TAB = "solar-plant-diagram-tab"


def by_id(flow: list) -> dict:
    return {n["id"]: n for n in flow if n.get("id")}


def dedupe_group_nodes(flow: list) -> None:
    ids = by_id(flow)
    blue = ids.get(BLUE)
    if not blue:
        return
    seen: set[str] = set()
    clean: list[str] = []
    for nid in blue.get("nodes", []):
        if nid in seen:
            continue
        seen.add(nid)
        clean.append(nid)
    blue["nodes"] = clean


def ensure_inject_bus(flow: list) -> None:
    ids = by_id(flow)
    inj = ids.get("inject-tick")
    if not inj:
        return
    targets = [f"ent-{i}-fn" for i in range(11)] + ["shared-states-prep"]
    inj["wires"] = [[t] for t in targets if t in ids]


def ensure_ent_chains(flow: list) -> None:
    ids = by_id(flow)
    for i in range(11):
        fn_id = f"ent-{i}-fn"
        http_id = f"ent-{i}-http"
        fmt_id = f"ent-{i}-fmt"
        if fn_id not in ids:
            continue
        if http_id in ids:
            ids[fn_id]["wires"] = [[http_id]]
        if http_id in ids and fmt_id in ids:
            ids[http_id]["wires"] = [[fmt_id]]


def ensure_states_to_panels(flow: list) -> None:
    ids = by_id(flow)
    chain = [
        ("shared-states-prep", "shared-states-http"),
        ("shared-states-http", "shared-states-lo"),
    ]
    for src, dst in chain:
        if src in ids and dst in ids:
            ids[src]["wires"] = [[dst]]
    li = ids.get("panel-states-li")
    calc = ids.get("panel-calc")
    if li and calc:
        li["wires"] = [[calc]]


def update_guides(flow: list) -> None:
    ids = by_id(flow)
    inj_c = ids.get("comment-topology")
    if inj_c:
        inj_c["name"] = (
            "Poll HA every 5s fans to each clamp (fn->GET->status) plus GET /api/states "
            "(dashed link) for panel math."
        )
    pc = ids.get("panel-comment")
    if pc:
        pc["name"] = (
            "HA states (link) -> fan-out -> Panel rows -> charger status. "
            "Keep your layout; wires carry live data every 5s."
        )


def main() -> int:
    flow = json.loads(FLOW.read_text(encoding="utf-8"))
    positions = {n["id"]: (n.get("x"), n.get("y")) for n in flow if n.get("id")}

    dedupe_group_nodes(flow)
    ensure_inject_bus(flow)
    ensure_ent_chains(flow)
    ensure_states_to_panels(flow)
    update_guides(flow)

    wire = ROOT / "scripts" / "wire_panels_to_chargers.py"
    FLOW.write_text(json.dumps(flow, indent=2), encoding="utf-8")
    if wire.is_file():
        subprocess.run([sys.executable, str(wire), "--preserve-positions"], check=True)

    flow2 = json.loads(FLOW.read_text(encoding="utf-8"))
    ids2 = by_id(flow2)
    for nid, (x, y) in positions.items():
        if nid in ids2 and x is not None and y is not None:
            ids2[nid]["x"] = x
            ids2[nid]["y"] = y
    FLOW.write_text(json.dumps(flow2, indent=2), encoding="utf-8")
    print("connect_solar_diagram_flow: all HA + panel paths wired (positions kept)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
