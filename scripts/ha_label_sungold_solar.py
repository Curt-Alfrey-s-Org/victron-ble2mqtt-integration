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
import os
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
UNIQUE_ID_PREFIX = "sungold_sph302480a-"
MQTT_IDENT = ["mqtt", "sungold_sph302480a"]

# MQTT discovery sets has_entity_name, so friendly names are
# "Sungold SPH302480A PV input voltage" and tiles truncate to "Sungold S...".
# Show the entity name only: https://www.home-assistant.io/dashboards/naming/
TILE_ENTITY_NAME = {"type": "entity"}

# SPH302480A does not publish these (one MPPT, illegal 0x023A, transformer-less).
# unique_id is mqtt_topic + key with / replaced by -.
RETIRED_UNIQUE_IDS = frozenset(
    {
        "sungold_sph302480a-pv-total_power",
        "sungold_sph302480a-grid-power",
        "sungold_sph302480a-temperature-transformer",
        "sungold_sph302480a-pv-voltage",
        "sungold_sph302480a-pv-current",
        "sungold_sph302480a-pv-power",
    }
)
RETIRED_ENTITY_IDS = frozenset(
    {
        "sensor.sungold_sph302480a_pv_total_power",
        "sensor.sungold_sph302480a_grid_power",
        "sensor.sungold_sph302480a_temperature_transformer",
    }
)

# MQTT unique_id order (register keys). Lovelace uses live entity_id for each.
PREFERRED_UNIQUE_IDS = (
    "sungold_sph302480a-pv1-voltage",
    "sungold_sph302480a-pv1-current",
    "sungold_sph302480a-pv1-power",
    "sungold_sph302480a-battery-soc",
    "sungold_sph302480a-battery-voltage",
    "sungold_sph302480a-battery-current",
    "sungold_sph302480a-battery-temperature",
    "sungold_sph302480a-battery-charge_state",
    "sungold_sph302480a-inverter-charging_power",
    "sungold_sph302480a-inverter-voltage",
    "sungold_sph302480a-inverter-frequency",
    "sungold_sph302480a-load-current",
    "sungold_sph302480a-load-power",
    "sungold_sph302480a-grid-voltage",
    "sungold_sph302480a-grid-current",
    "sungold_sph302480a-grid-frequency",
    "sungold_sph302480a-inverter-state",
    "sungold_sph302480a-temperature-dc_dc",
    "sungold_sph302480a-temperature-dc_ac",
    "sungold_sph302480a-inverter-failcode",
    "sungold_sph302480a-inverter-error_flags",
    "sungold_sph302480a-inverter-fault_active",
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


def entity_tile(entity_id: str) -> dict:
    return {"type": "tile", "entity": entity_id, "name": dict(TILE_ENTITY_NAME)}


def apply_entity_tile_names(view: dict) -> None:
    for section in view.get("sections") or []:
        for card in section.get("cards") or []:
            if card.get("type") == "tile" and card.get("entity"):
                card["name"] = dict(TILE_ENTITY_NAME)


def _add_label(labels: list | None) -> list[str]:
    out = list(labels or [])
    if LABEL_ID not in out:
        out.append(LABEL_ID)
    return out


def _is_sungold_entity(ent: dict) -> bool:
    eid = ent.get("entity_id") or ""
    uid = ent.get("unique_id") or ""
    if eid in RETIRED_ENTITY_IDS or uid in RETIRED_UNIQUE_IDS:
        return False
    if uid.startswith(UNIQUE_ID_PREFIX):
        return True
    return ENTITY_PREFIX in eid


def label_entities_and_device(storage: Path) -> list[tuple[str, str]]:
    er_path = storage / "core.entity_registry"
    payload = load_store(er_path)
    entities = payload["data"]["entities"]
    found: list[tuple[str, str]] = []
    device_ids: set[str] = set()
    for ent in entities:
        if not _is_sungold_entity(ent):
            continue
        eid = ent.get("entity_id") or ""
        uid = ent.get("unique_id") or ""
        ent["labels"] = _add_label(ent.get("labels"))
        found.append((uid, eid))
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


def ordered_entities(found: list[tuple[str, str]]) -> list[str]:
    by_uid = {uid: eid for uid, eid in found if uid}
    preferred = [by_uid[uid] for uid in PREFERRED_UNIQUE_IDS if uid in by_uid]
    used = set(preferred)
    extra = sorted(eid for _uid, eid in found if eid not in used)
    return preferred + extra


def sungold_section(entity_ids: list[str]) -> dict:
    cards: list[dict] = [
        {"type": "heading", "heading": HEADING, "icon": LABEL_ICON}
    ]
    cards.extend(entity_tile(eid) for eid in entity_ids)
    # max_columns keeps tiles readable on phone-width Tailscale Companion views.
    # https://www.home-assistant.io/dashboards/sections/
    return {"type": "grid", "column_span": 1, "cards": cards}


def is_sungold_section(section: dict) -> bool:
    for card in section.get("cards") or []:
        if card.get("type") == "heading" and card.get("heading") == HEADING:
            return True
    return False


def is_sungold_view(view: dict) -> bool:
    path = (view.get("path") or "").strip().lower()
    title = (view.get("title") or "").strip().lower()
    return path == "sungold" or title == "sungold"


def sungold_view(entity_ids: list[str]) -> dict:
    """Dedicated sidebar view so mobile Tailscale users do not bury Sungold under EM16."""
    return {
        "title": HEADING,
        "path": "sungold",
        "icon": LABEL_ICON,
        "type": "sections",
        "max_columns": 2,
        "sections": [sungold_section(entity_ids)],
    }


def solar_flow_link_card(url: str) -> dict:
    """Markdown card pointing at the Tailscale / LAN solar-flow URL (no token)."""
    clean = url.rstrip("/") + "/"
    return {
        "type": "markdown",
        "content": (
            f"### Animated solar flow\n"
            f"[Open live diagram]({clean}) — same Victron / Sungold / EM16 numbers "
            f"as this dashboard (Tailscale or LAN)."
        ),
    }


def upsert_sungold_view(views: list[dict], entity_ids: list[str]) -> None:
    view = sungold_view(entity_ids)
    for idx, existing in enumerate(views):
        if is_sungold_view(existing):
            # Preserve any operator-added cards after the Sungold section.
            sections = existing.setdefault("sections", [])
            replaced = False
            for s_idx, section in enumerate(sections):
                if is_sungold_section(section):
                    sections[s_idx] = view["sections"][0]
                    replaced = True
                    break
            if not replaced:
                sections.insert(0, view["sections"][0])
            existing["title"] = HEADING
            existing["path"] = "sungold"
            existing["icon"] = LABEL_ICON
            existing["type"] = "sections"
            existing["max_columns"] = 2
            views[idx] = existing
            return
    views.append(view)


def upsert_solar_section(
    storage: Path,
    entity_ids: list[str],
    *,
    solar_flow_url: str | None = None,
) -> None:
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
        # Insert near the top so phone Tailscale users see Sungold without endless scroll.
        insert_at = 1 if len(sections) >= 1 else 0
        sections.insert(insert_at, section)

    if solar_flow_url:
        link = solar_flow_link_card(solar_flow_url)
        # Keep a single animated-diagram markdown card at the front of the first section.
        first = sections[0] if sections else None
        if first and isinstance(first.get("cards"), list):
            cards = first["cards"]
            cards[:] = [
                c
                for c in cards
                if not (
                    c.get("type") == "markdown"
                    and "Animated solar flow" in (c.get("content") or "")
                )
            ]
            cards.insert(0, link)

    apply_entity_tile_names(view)
    upsert_sungold_view(views, entity_ids)
    write_store(path, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--storage",
        default="/opt/homeassistant/.storage",
        help="Home Assistant .storage directory",
    )
    parser.add_argument(
        "--solar-flow-url",
        default=os.environ.get("SOLAR_FLOW_PUBLIC_URL", "").strip() or None,
        help="Public Tailscale/LAN URL for the animated diagram (markdown link on Solar)",
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
        print("WARN: no Sungold entities in registry; Solar section is heading only")
    upsert_solar_section(storage, ordered, solar_flow_url=args.solar_flow_url)
    print(f"OK: label {LABEL_ID} ({LABEL_NAME}); entities={len(ordered)}")
    for eid in ordered:
        print(f"  {eid}")
    print("OK: Solar view 'Sungold' (path=/sungold) for mobile Tailscale parity")
    if args.solar_flow_url:
        print(f"OK: solar-flow link -> {args.solar_flow_url.rstrip('/')}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
