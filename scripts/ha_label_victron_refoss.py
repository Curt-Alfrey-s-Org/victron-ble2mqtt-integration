#!/usr/bin/env python3
"""Label Victron and Refoss devices and align dashboard headings with official names.

Run on .105 with the homeassistant container STOPPED
(https://www.home-assistant.io/common-tasks/container/).

Official:
  Labels:  https://www.home-assistant.io/docs/organizing/labels/
  Storage: https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/label_registry.py
  Sections / heading / tile:
    https://www.home-assistant.io/dashboards/sections/
    https://www.home-assistant.io/dashboards/heading/
    https://www.home-assistant.io/dashboards/tile/
  Victron SmartShunt readout:
    https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html
  BlueSolar MPPT 75/15 monitoring:
    https://www.victronenergy.com/media/pg/Manual_BlueSolar_MPPT_75-10_up_to_100-20/en/monitoring.html
  Refoss EM16:
    https://refoss.net/collections/smart-energy-monitor/products/refoss-smart-energy-monitor-em16
    https://www.home-assistant.io/integrations/refoss/
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

STORAGE_VERSION_MAJOR = 1
STORAGE_VERSION_MINOR = 2

VICTRON_LABEL = {
    "label_id": "victron",
    "name": "Victron",
    "icon": "mdi:solar-power",
    "color": "#3871C1",
    "description": "Victron Energy SmartShunt / BlueSolar MQTT Instant Readout (Pi4). Not the disabled victron_ble leftovers.",
}

REFOSS_LABEL = {
    "label_id": "refoss",
    "name": "Refoss",
    "icon": "mdi:lightning-bolt",
    "color": "#00897B",
    "description": "Refoss Smart Energy Monitor, EM16 (LAN UDP). Official channels A1-C6.",
}

VICTRON_MANUFACTURER = "Victron Energy"
VICTRON_ENTITY_PREFIXES = (
    "sensor.battery_1_",
    "sensor.battery_2_",
    "sensor.solar_controller_",
)
SKIP_DEVICE_NAMES = frozenset({"FAKE", "victron-ble2mqtt@web-sites"})

# Official VictronConnect / product model, not leftover victron_ble "Mppt charger".
SOLAR_HEADING_RENAMES = {
    "Mppt charger": "BlueSolar MPPT 75/15",
}

# MQTT tiles otherwise show "Solar-contr..." / "Battery 1 A...".
# https://www.home-assistant.io/dashboards/naming/
TILE_ENTITY_NAME = {"type": "entity"}

REFOSS_DEVICE_NAME = "Refoss Smart Energy Monitor, EM16"
REFOSS_IDENT_DOMAIN = "refoss"
# HA core CHANNEL_DISPLAY_NAME for em16 (homeassistant/components/refoss/const.py).
EM16_CHANNELS = tuple(
    f"{bank}{n}" for bank in ("A", "B", "C") for n in range(1, 7)
)
EM16_SENSOR_KEYS = (
    "voltage",
    "current",
    "power",
    "power_factor",
    "this_month_energy",
    "this_month_energy_returned",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_store(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_store(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def ensure_label(storage: Path, spec: dict) -> None:
    path = storage / "core.label_registry"
    now = utc_now()
    label_id = spec["label_id"]
    if path.exists():
        payload = load_store(path)
        labels = payload.setdefault("data", {}).setdefault("labels", [])
        existing = None
        for row in labels:
            if row.get("label_id") == label_id or row.get("name") == spec["name"]:
                existing = row
                break
        if existing is None:
            labels.append(
                {
                    "color": spec["color"],
                    "description": spec["description"],
                    "icon": spec["icon"],
                    "label_id": label_id,
                    "name": spec["name"],
                    "created_at": now,
                    "modified_at": now,
                }
            )
        else:
            existing["label_id"] = label_id
            existing["name"] = spec["name"]
            existing["icon"] = spec["icon"]
            existing["color"] = spec["color"]
            existing["description"] = spec["description"]
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
                        "color": spec["color"],
                        "description": spec["description"],
                        "icon": spec["icon"],
                        "label_id": label_id,
                        "name": spec["name"],
                        "created_at": now,
                        "modified_at": now,
                    }
                ]
            },
        },
    )


def _add_label(labels: list | None, label_id: str) -> list[str]:
    out = list(labels or [])
    if label_id not in out:
        out.append(label_id)
    return out


def _backup_once(path: Path, tag: str) -> None:
    if not path.exists():
        return
    if any(path.parent.glob(path.name + f".bak-{tag}-*")):
        return
    bak = path.with_name(
        path.name + f".bak-{tag}-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    shutil.copy2(path, bak)


def label_victron(storage: Path) -> tuple[list[str], list[str]]:
    dr_path = storage / "core.device_registry"
    dpayload = load_store(dr_path)
    device_ids: set[str] = set()
    named: list[str] = []
    for dev in dpayload["data"]["devices"]:
        if dev.get("disabled_by"):
            continue
        name = dev.get("name_by_user") or dev.get("name") or ""
        if name in SKIP_DEVICE_NAMES:
            continue
        if (dev.get("manufacturer") or "") != VICTRON_MANUFACTURER:
            continue
        dev["labels"] = _add_label(dev.get("labels"), VICTRON_LABEL["label_id"])
        device_ids.add(dev["id"])
        named.append(name)
    write_store(dr_path, dpayload)

    er_path = storage / "core.entity_registry"
    epayload = load_store(er_path)
    found: list[str] = []
    for ent in epayload["data"]["entities"]:
        if ent.get("disabled_by"):
            continue
        eid = ent.get("entity_id") or ""
        if ent.get("device_id") in device_ids or any(eid.startswith(p) for p in VICTRON_ENTITY_PREFIXES):
            ent["labels"] = _add_label(ent.get("labels"), VICTRON_LABEL["label_id"])
            found.append(eid)
    write_store(er_path, epayload)
    return named, found


def label_refoss(storage: Path) -> tuple[list[str], list[str]]:
    dr_path = storage / "core.device_registry"
    dpayload = load_store(dr_path)
    device_ids: set[str] = set()
    named: list[str] = []
    for dev in dpayload["data"]["devices"]:
        if dev.get("disabled_by"):
            continue
        ident = dev.get("identifiers") or []
        if not any(
            isinstance(row, list) and len(row) >= 1 and row[0] == REFOSS_IDENT_DOMAIN
            for row in ident
        ):
            continue
        dev["name_by_user"] = REFOSS_DEVICE_NAME
        dev["labels"] = _add_label(dev.get("labels"), REFOSS_LABEL["label_id"])
        device_ids.add(dev["id"])
        named.append(REFOSS_DEVICE_NAME)
    write_store(dr_path, dpayload)

    er_path = storage / "core.entity_registry"
    epayload = load_store(er_path)
    found: list[str] = []
    for ent in epayload["data"]["entities"]:
        if ent.get("disabled_by"):
            continue
        eid = ent.get("entity_id") or ""
        if ent.get("device_id") in device_ids or eid.startswith("sensor.em16_"):
            ent["labels"] = _add_label(ent.get("labels"), REFOSS_LABEL["label_id"])
            found.append(eid)
    write_store(er_path, epayload)
    return named, found


def rename_solar_headings(storage: Path) -> list[str]:
    path = storage / "lovelace.dashboard_solar"
    if not path.exists():
        raise FileNotFoundError(f"missing {path}")
    _backup_once(path, "pre-victron-headings")
    payload = load_store(path)
    views = payload["data"]["config"]["views"]
    if not views:
        raise ValueError("Solar dashboard has no views")
    changed: list[str] = []
    for view in views:
        for section in view.get("sections") or []:
            for card in section.get("cards") or []:
                if card.get("type") == "heading":
                    old = card.get("heading")
                    new = SOLAR_HEADING_RENAMES.get(old)
                    if new and new != old:
                        card["heading"] = new
                        changed.append(f"{old} -> {new}")
                elif card.get("type") == "tile" and card.get("entity"):
                    card["name"] = dict(TILE_ENTITY_NAME)
    write_store(path, payload)
    return changed


def em16_entity_id(channel: str, key: str) -> str:
    return f"sensor.em16_{channel.lower()}_{key}"


def refoss_sections(found: list[str]) -> list[dict]:
    found_set = set(found)
    sections: list[dict] = []
    for channel in EM16_CHANNELS:
        tiles = [
            {
                "type": "tile",
                "entity": em16_entity_id(channel, key),
                "name": dict(TILE_ENTITY_NAME),
            }
            for key in EM16_SENSOR_KEYS
            if em16_entity_id(channel, key) in found_set
        ]
        if not tiles:
            continue
        cards: list[dict] = [
            {"type": "heading", "heading": channel, "icon": REFOSS_LABEL["icon"]}
        ]
        cards.extend(tiles)
        sections.append({"type": "grid", "cards": cards})
    return sections


def upsert_refoss_dashboard(storage: Path, found: list[str]) -> int:
    path = storage / "lovelace.dashboard_refoss"
    if not path.exists():
        raise FileNotFoundError(f"missing {path}")
    _backup_once(path, "pre-refoss-channels")
    payload = load_store(path)
    views = payload["data"]["config"]["views"]
    if not views:
        raise ValueError("Refoss dashboard has no views")
    sections = refoss_sections(found)
    if not sections:
        raise ValueError("no EM16 channel entities found")
    views[0]["title"] = "Refoss"
    views[0]["type"] = "sections"
    views[0]["sections"] = sections
    write_store(path, payload)
    return len(sections)


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

    ensure_label(storage, VICTRON_LABEL)
    ensure_label(storage, REFOSS_LABEL)
    v_devices, v_ents = label_victron(storage)
    r_devices, r_ents = label_refoss(storage)
    heading_changes = rename_solar_headings(storage)
    n_sections = upsert_refoss_dashboard(storage, r_ents)

    print(
        f"OK: label {VICTRON_LABEL['label_id']} devices={len(v_devices)} "
        f"entities={len(v_ents)}"
    )
    for name in v_devices:
        print(f"  victron-device {name}")
    print(
        f"OK: label {REFOSS_LABEL['label_id']} devices={len(r_devices)} "
        f"entities={len(r_ents)} channel-sections={n_sections}"
    )
    for name in r_devices:
        print(f"  refoss-device {name}")
    if heading_changes:
        print("OK: Solar headings")
        for row in heading_changes:
            print(f"  {row}")
    else:
        print("OK: Solar headings already official")
    return 0


if __name__ == "__main__":
    sys.exit(main())
