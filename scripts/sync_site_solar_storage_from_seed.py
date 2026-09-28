#!/usr/bin/env python3
"""Offline fallback: write the repo seed straight into .storage/lovelace.site_solar.

DESTRUCTIVE and OFFLINE ONLY (2026-09-28). This replaces every card on /site-solar
with the repo seed. It used to run automatically at the end of
scripts/install_solar_plant_ha.sh, while HA was running: HA keeps the dashboard in
memory, so the file change stayed invisible until the NEXT restart and then quietly
replaced the UI edits made in between. That automatic call is gone.

Now it refuses unless:
  * you pass --force, and
  * the `homeassistant` container is stopped (or you also pass --allow-running, in
    which case you must restart HA right away and not edit the dashboard first).
It copies the current file to lovelace.site_solar.bak-sync-seed-<UTC stamp> first.
Prefer scripts/save_solar_plant_storage_dashboard.py (websocket, backs up, refuses
without --force) and scripts/site_solar_settings.py export/restore.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "config" / "dashboards" / "solar-plant.yaml"
STORAGE = Path("/opt/homeassistant/.storage/lovelace.site_solar")


def ha_running(container: str = "homeassistant") -> bool:
    try:
        out = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            check=False,
            capture_output=True,
            text=True,
        ).stdout
    except OSError:
        return False
    return container in out.split()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--force", action="store_true", help="really overwrite the dashboard")
    parser.add_argument(
        "--allow-running", action="store_true", help="write even while HA is running"
    )
    parser.add_argument("--seed", type=Path, default=SEED)
    parser.add_argument("--storage", type=Path, default=STORAGE)
    args = parser.parse_args(argv)

    if not args.force:
        print(
            "REFUSED: this replaces your /site-solar dashboard with the repo seed. "
            "Back up first (scripts/site_solar_settings.py export), stop HA, then rerun "
            "with --force.",
            file=sys.stderr,
        )
        return 3
    if ha_running() and not args.allow_running:
        print(
            "REFUSED: the homeassistant container is running; a .storage write now is "
            "applied at the next restart and lost if you edit the dashboard first. "
            "Use scripts/save_solar_plant_storage_dashboard.py --force instead, or "
            "`docker stop homeassistant` first.",
            file=sys.stderr,
        )
        return 3
    if not args.seed.is_file():
        raise SystemExit(f"missing seed {args.seed}")
    if not args.storage.is_file():
        raise SystemExit(f"missing storage {args.storage}")

    seed = yaml.safe_load(args.seed.read_text(encoding="utf-8"))
    if not isinstance(seed, dict) or not seed.get("views"):
        raise SystemExit("invalid seed yaml")

    raw = json.loads(args.storage.read_text(encoding="utf-8"))
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = args.storage.with_name(args.storage.name + f".bak-sync-seed-{ts}")
    shutil.copy2(args.storage, backup)
    print(f"backup {backup}")

    raw.setdefault("data", {})["config"] = seed
    args.storage.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    print(f"synced {len(seed['views'])} views from seed to {args.storage}")
    print("Start / restart HA now: docker start homeassistant (or docker restart homeassistant)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
