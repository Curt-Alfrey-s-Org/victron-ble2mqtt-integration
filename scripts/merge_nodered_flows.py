#!/usr/bin/env python3
"""Merge Node-RED flow JSON arrays (tabs + nodes) for deploy."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: merge_nodered_flows.py out.json in1.json in2.json ...", file=sys.stderr)
        return 2
    out = Path(argv[1])
    merged: list[dict] = []
    seen_ids: set[str] = set()
    for path_str in argv[2:]:
        path = Path(path_str)
        chunk = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(chunk, list):
            raise SystemExit(f"{path} must be a JSON array")
        for node in chunk:
            nid = node.get("id")
            if nid:
                if nid in seen_ids:
                    raise SystemExit(f"duplicate node id {nid} in {path}")
                seen_ids.add(nid)
            merged.append(node)
    out.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"merged {len(merged)} nodes -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
