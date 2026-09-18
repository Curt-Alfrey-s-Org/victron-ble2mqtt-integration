#!/usr/bin/env python3
"""Set Home Assistant numeric display precision to tenths.

Run on .105 with the homeassistant container STOPPED
(https://www.home-assistant.io/common-tasks/container/).

Official:
  MQTT suggested_display_precision:
    https://www.home-assistant.io/integrations/sensor.mqtt/#suggested_display_precision
  Entity registry display_precision (user override, frontend):
    https://developers.home-assistant.io/docs/api/websocket/
  Sensor presentation rounding:
    https://developers.home-assistant.io/blog/2023/02/08/sensor_presentation_rounding/
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

PRECISION = 1
SENSOR_DOMAINS = frozenset({"sensor", "number"})
SKIP_DEVICE_CLASSES = frozenset({"timestamp", "date", "enum"})


def load_store(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_store(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _backup_once(path: Path) -> None:
    bak = path.with_name(path.name + ".bak-display-precision")
    if not bak.exists():
        shutil.copy2(path, bak)


def entity_domain(entity_id: str) -> str:
    if "." not in entity_id:
        return ""
    return entity_id.split(".", 1)[0]


def device_class_of(ent: dict[str, Any]) -> str:
    raw = ent.get("device_class") or ent.get("original_device_class") or ""
    return str(raw)


def should_set_precision(ent: dict[str, Any]) -> bool:
    eid = str(ent.get("entity_id") or "")
    domain = entity_domain(eid)
    if domain not in SENSOR_DOMAINS:
        return False
    if device_class_of(ent) in SKIP_DEVICE_CLASSES:
        return False
    return True


def options_key(domain: str) -> str:
    return "sensor" if domain == "sensor" else "number"


def apply_entity_precision(ent: dict[str, Any], precision: int = PRECISION) -> bool:
    """Merge display_precision into existing domain options. Return True if changed."""
    eid = str(ent.get("entity_id") or "")
    domain = entity_domain(eid)
    key = options_key(domain)
    options = ent.get("options")
    if not isinstance(options, dict):
        options = {}
        ent["options"] = options
    current = options.get(key)
    if not isinstance(current, dict):
        current = {}
    want_suggested = domain == "sensor"
    already = current.get("display_precision") == precision
    if want_suggested:
        already = already and current.get("suggested_display_precision") == precision
    if already:
        return False
    merged = dict(current)
    merged["display_precision"] = precision
    if want_suggested:
        merged["suggested_display_precision"] = precision
    options[key] = merged
    return True


def apply_storage(storage: Path, precision: int = PRECISION) -> dict[str, int]:
    er_path = storage / "core.entity_registry"
    if not er_path.is_file():
        raise FileNotFoundError(f"missing {er_path}")
    _backup_once(er_path)
    payload = load_store(er_path)
    entities = payload.get("data", {}).get("entities")
    if not isinstance(entities, list):
        raise ValueError("core.entity_registry has no data.entities list")
    updated = 0
    skipped = 0
    unchanged = 0
    for ent in entities:
        if not isinstance(ent, dict):
            skipped += 1
            continue
        if not should_set_precision(ent):
            skipped += 1
            continue
        if apply_entity_precision(ent, precision):
            updated += 1
        else:
            unchanged += 1
    write_store(er_path, payload)
    return {
        "updated": updated,
        "unchanged": unchanged,
        "skipped": skipped,
        "total": len(entities),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--storage",
        default="/opt/homeassistant/.storage",
        help="Home Assistant .storage directory",
    )
    parser.add_argument(
        "--precision",
        type=int,
        default=PRECISION,
        help="Decimal places (default 1 = tenths)",
    )
    args = parser.parse_args(argv)
    if args.precision < 0:
        print("FAIL: precision must be >= 0", file=sys.stderr)
        return 1
    storage = Path(args.storage)
    try:
        stats = apply_storage(storage, args.precision)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(
        "OK: display_precision="
        f"{args.precision} updated={stats['updated']} "
        f"unchanged={stats['unchanged']} skipped={stats['skipped']} "
        f"total={stats['total']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
