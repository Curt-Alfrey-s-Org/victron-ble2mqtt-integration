#!/usr/bin/env python3
"""Copy Solar plant diagram tab from runtime flows.json into flows/solar_plant_diagram.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "nodered-data" / "flows.json"
OUT = ROOT / "flows" / "solar_plant_diagram.json"
TAB = "solar-plant-diagram-tab"


def main() -> int:
    if not RUNTIME.is_file():
        raise SystemExit(f"missing {RUNTIME}")
    flow = json.loads(RUNTIME.read_text(encoding="utf-8"))
    chunk = [n for n in flow if n.get("z") == TAB or (n.get("type") == "tab" and n.get("id") == TAB)]
    if not chunk:
        raise SystemExit(f"no nodes for tab {TAB}")
    OUT.write_text(json.dumps(chunk, indent=2), encoding="utf-8")
    print(f"wrote {len(chunk)} nodes to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
