#!/usr/bin/env python3
"""Label Sungold MQTT entities and add a Sungold section on the Solar dashboard.

Run on .105 with the homeassistant container STOPPED
(https://www.home-assistant.io/common-tasks/container/).

Official:
  Labels:  https://www.home-assistant.io/docs/organizing/labels/
  Storage: https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/label_registry.py
  Sections / heading / tile:
    https://www.home-assistant.io/dashboards/sections/
    https://www.home-assistant.io/dashboards/heading/
    https://www.home-assistant.io/dashboards/tile/
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

LABEL_ID = "sungold"
LABEL_NAME = "Sungold"
LABEL_ICON = "mdi:solar-power-variant"
# Hex is valid on config/label_registry/create (cv.color_hex).
LABEL_COLOR = "#FFC107"
LABEL_DESCRIPTION = "SunGoldPower SPH302480A all-in-one solar charge inverter (USB). Not T2/KU."
HEADING = "Sungold"
ENTITY_PREFIX = "sungold_sph302480a"
MQTT_IDENT = ["mqtt", "sungold_sph302480a"]

# SPH302480A does not publish these (one MPPT, illegal 0x023A, transformer-less).
RETIRED_ENTITY_IDS = frozenset(
    {
        "sensor.sungold_sph302480a_pv_total_power",
        "sensor.sungold_sph302480a_grid_power",
        "sensor.sungold_sph302480a_temperature_transformer",
    }
)

# Used when MQTT discovery was hidden after Modbus skips.
FALLBACK_TILES = (
    "sensor.sungold_sph302480a_pv_voltage",
    "sensor.sungold_sph302480a_charge_state",
    "sensor.sungold_sph302480a_ac_output_voltage",
    "sensor.sungold_sph302480a_load_power",
    "sensor.sungold_sph302480a_grid_current",
    "sensor.sungold_sph302480a_temperature_dc_ac",
    "sensor.sungold_sph302480a_inverter_state",
    "sensor.sungold_sph302480a_fail_code",
    "binary_sensor.sungold_sph302480a_fault_active",
)

PREFERRED_ORDER = (
    "sensor.sungold_sph302480a_pv_voltage",
    "sensor.sungold_sph302480a_pv_current",
    "sensor.sungold_sph302480a_pv_power",
    "sensor.sungold_sph302480a_battery_soc",
    "sensor.sungold_sph302480a_battery_voltage",
    "sensor.sungold_sph302480a_battery_current",
    "sensor.sungold_sph302480a_battery_temperature",
    "sensor.sungold_sph302480a_charge_state",
    "sensor.sungold_sph302480a_charging_power",
    "sensor.sungold_sph302480a_ac_output_voltage",
    "sensor.sungold_sph302480a_ac_output_frequency",
    "sensor.sungold_sph302480a_load_current",
    "sensor.sungold_sph302480a_load_power",
    "sensor.sungold_sph302480a_grid_voltage",
    "sensor.sungold_sph302480a_grid_current",
    "sensor.sungold_sph302480a_grid_frequency",
    "sensor.sungold_sph302480a_inverter_state",
    "sensor.sungold_sph302480a_temperature_dc_dc",
    "sensor.sungold_sph302480a_temperature_dc_ac",
    "sensor.sungold_sph302480a_fail_code",
    "sensor.sungold_sph302480a_inverter_error_flags",
    "binary_sensor.sungold_sph302480a_fault_active",
)

STORAGE_VERSION_MAJOR = 1
STORAGE_VERSION_MINOR = 2


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_store(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_store(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def ensure_label(storage: Path) -> None:
    path = storage / "core.label_registry"
    now = utc_now()
    if path.exists():
        payload = load_store(path)
        labels = payload.setdefault("data", {}).setdefault("labels", [])
        by_id = {row.get("label_id"): row for row in labels}
        existing = by_id.get(LABEL_ID)
        if existing is None:
            for row in labels:
                if row.get("name") == LABEL_NAME:
                    existing = row
                    break
        if existing is None:
            labels.append(
                {
                    "color": LABEL_COLOR,
                    "description": LABEL_DESCRIPTION,
                    "icon": LABEL_ICON,
                    "label_id": LABEL_ID,
                    "name": LABEL_NAME,
                    "created_at": now,
                    "modified_at": now,
                }
            )
        else:
            existing["name"] = LABEL_NAME
            existing["icon"] = LABEL_ICON
            existing["color"] = LABEL_COLOR
            existing["description"] = LABEL_DESCRIPTION
            existing["modified_at"] = now
        write_store(path, payload)
        return

    write_store(
        path,
        {
            "version": STORAGE_VERSION_MAJOR,
            "minor_version": STORAGE_VERSION_MINOR,
            "key": "core.label_registry",
            "data": {
                "labels": [
                    {
                        "color": LABEL_COLOR,
                        "description": LABEL_DESCRIPTION,
                        "icon": LABEL_ICON,
                        "label_id": LABEL_ID,
                        "name": LABEL_NAME,
                        "created_at": now,
                        "modified_at": now,
                    }
                ]
            },
        },
    )


def _add_label(labels: list | None) -> list[str]:
    out = list(labels or [])
    if LABEL_ID not in out:
        out.append(LABEL_ID)
    return out


def label_entities_and_device(storage: Path) -> list[str]:
    er_path = storage / "core.entity_registry"
    payload = load_store(er_path)
    entities = payload["data"]["entities"]
    found: list[str] = []
    device_ids: set[str] = set()
    for ent in entities:
        eid = ent.get("entity_id") or ""
        if ENTITY_PREFIX not in eid:
            continue
        if eid in RETIRED_ENTITY_IDS:
            continue
        ent["labels"] = _add_label(ent.get("labels"))
        found.append(eid)
        if ent.get("device_id"):
            device_ids.add(ent["device_id"])
    write_store(er_path, payload)

    dr_path = storage / "core.device_registry"
    dpayload = load_store(dr_path)
    for dev in dpayload["data"]["devices"]:
        ident = dev.get("identifiers") or []
        if MQTT_IDENT in ident or dev.get("id") in device_ids:
            dev["labels"] = _add_label(dev.get("labels"))
    write_store(dr_path, dpayload)
    return found


def ordered_entities(found: list[str]) -> list[str]:
    preferred = [eid for eid in PREFERRED_ORDER if eid in found]
    extra = sorted(eid for eid in found if eid not in preferred)
    return preferred + extra


def sungold_section(entity_ids: list[str]) -> dict:
    cards: list[dict] = [
        {"type": "heading", "heading": HEADING, "icon": LABEL_ICON}
    ]
    cards.extend({"type": "tile", "entity": eid} for eid in entity_ids)
    return {"type": "grid", "cards": cards}


def is_sungold_section(section: dict) -> bool:
    for card in section.get("cards") or []:
        if card.get("type") == "heading" and card.get("heading") == HEADING:
            return True
    return False


def upsert_solar_section(storage: Path, entity_ids: list[str]) -> None:
    path = storage / "lovelace.dashboard_solar"
    if not path.exists():
        raise FileNotFoundError(f"missing {path}")
    bak = path.with_name(
        path.name + ".bak-pre-sungold-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    if not any(path.parent.glob(path.name + ".bak-pre-sungold-*")):
        shutil.copy2(path, bak)

    payload = load_store(path)
    views = payload["data"]["config"]["views"]
    if not views:
        raise ValueError("Solar dashboard has no views")
    view = views[0]
    if view.get("type") != "sections":
        raise ValueError(f"Solar view type is {view.get('type')!r}, expected sections")
    sections = view.setdefault("sections", [])
    section = sungold_section(entity_ids)
    replaced = False
    for idx, existing in enumerate(sections):
        if is_sungold_section(existing):
            sections[idx] = section
            replaced = True
            break
    if not replaced:
        sections.append(section)
    write_store(path, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--storage",
        default="/opt/homeassistant/.storage",
        help="Home Assistant .storage directory",
    )
    args = parser.parse_args()
    storage = Path(args.storage)
    if not storage.is_dir():
        print(f"FAIL: storage dir missing: {storage}", file=sys.stderr)
        return 1

    ensure_label(storage)
    found = label_entities_and_device(storage)
    ordered = ordered_entities(found)
    if not ordered:
        # Lovelace tiles may exist before MQTT rediscovery; keep the cart section.
        ordered = list(FALLBACK_TILES)
        print("WARN: no Sungold entities in registry; Solar section uses fallback ids")
    upsert_solar_section(storage, ordered)
    print(f"OK: label {LABEL_ID} ({LABEL_NAME}); entities={len(ordered)}")
    for eid in ordered:
        print(f"  {eid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
