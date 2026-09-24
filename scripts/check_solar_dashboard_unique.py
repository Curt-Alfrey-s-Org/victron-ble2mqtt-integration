#!/usr/bin/env python3
"""Fail if the Now view repeats an entity on tile cards."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "config" / "dashboards" / "solar-plant.yaml"


def tile_entities(now_view: dict) -> list[str]:
    out: list[str] = []
    for section in now_view.get("sections") or []:
        for card in (section.get("cards") or []):
            if card.get("type") == "tile" and card.get("entity"):
                out.append(str(card["entity"]))
    return out


def main() -> int:
    data = yaml.safe_load(DASH.read_text(encoding="utf-8"))
    now = next(v for v in data["views"] if v.get("path") == "now")
    tiles = tile_entities(now)
    seen: dict[str, int] = {}
    for e in tiles:
        seen[e] = seen.get(e, 0) + 1
    dups = {k: v for k, v in seen.items() if v > 1}
    if dups:
        print("duplicate tile entities on Now view:", dups)
        return 1
    print(f"Now view: {len(tiles)} unique tile entities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
