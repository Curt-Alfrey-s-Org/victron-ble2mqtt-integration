#!/usr/bin/env python3
"""Sync lovelace.site_solar storage from repo seed YAML (no websocket token)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

SEED = Path("/home/ansible/victron-ble2mqtt-integration/config/dashboards/solar-plant.yaml")
STORAGE = Path("/opt/homeassistant/.storage/lovelace.site_solar")


def main() -> int:
    import yaml

    if not SEED.is_file():
        raise SystemExit(f"missing seed {SEED}")
    if not STORAGE.is_file():
        raise SystemExit(f"missing storage {STORAGE}")

    seed = yaml.safe_load(SEED.read_text(encoding="utf-8"))
    if not isinstance(seed, dict) or not seed.get("views"):
        raise SystemExit("invalid seed yaml")

    raw = json.loads(STORAGE.read_text(encoding="utf-8"))
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = STORAGE.with_name(STORAGE.name + f".bak-sync-seed-{ts}")
    shutil.copy2(STORAGE, backup)
    print(f"backup {backup}")

    raw.setdefault("data", {})["config"] = seed
    STORAGE.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    print(f"synced {len(seed['views'])} views from seed to {STORAGE}")
    blob = json.dumps(seed)
    print("ku_est_in_seed", "ku_pwm_mppt_combined_est_power" in blob)
    print("site_em16_in_seed", "site_em16_a3_power" in blob)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
