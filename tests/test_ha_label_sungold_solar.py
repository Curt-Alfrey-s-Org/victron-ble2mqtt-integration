"""ha_label_sungold_solar.py — label registry + Solar section."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ha_label_sungold_solar as sungold  # noqa: E402


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _solar_stub() -> dict:
    return {
        "version": 1,
        "minor_version": 1,
        "key": "lovelace.dashboard_solar",
        "data": {
            "config": {
                "views": [
                    {
                        "type": "sections",
                        "sections": [
                            {
                                "type": "grid",
                                "cards": [
                                    {"type": "heading", "heading": "Mppt charger"},
                                    {
                                        "type": "tile",
                                        "entity": "sensor.solar_controller_solar",
                                    },
                                ],
                            }
                        ],
                    }
                ]
            }
        },
    }


def test_label_and_solar_section(tmp_path: Path) -> None:
    storage = tmp_path / ".storage"
    storage.mkdir()
    _write(
        storage / "core.entity_registry",
        {
            "version": 1,
            "minor_version": 1,
            "key": "core.entity_registry",
            "data": {
                "entities": [
                    {
                        "entity_id": "sensor.sungold_sph302480a_load_active_power",
                        "unique_id": "sungold_sph302480a-load-power",
                        "labels": [],
                        "device_id": "dev1",
                    },
                    {
                        "entity_id": "sensor.sungold_sph302480a_pv_input_voltage",
                        "unique_id": "sungold_sph302480a-pv1-voltage",
                        "labels": [],
                        "device_id": "dev1",
                    },
                    {
                        "entity_id": "sensor.sungold_sph302480a_pv_voltage",
                        "unique_id": "sungold_sph302480a-pv-voltage",
                        "labels": [],
                        "device_id": "dev1",
                    },
                    {
                        "entity_id": "sensor.battery_1_voltage",
                        "unique_id": "battery-1-voltage",
                        "labels": [],
                        "device_id": "other",
                    },
                ]
            },
        },
    )
    _write(
        storage / "core.device_registry",
        {
            "version": 1,
            "minor_version": 1,
            "key": "core.device_registry",
            "data": {
                "devices": [
                    {
                        "id": "dev1",
                        "name": "Sungold SPH302480A",
                        "labels": [],
                        "identifiers": [["mqtt", "sungold_sph302480a"]],
                    }
                ]
            },
        },
    )
    _write(storage / "lovelace.dashboard_solar", _solar_stub())

    sungold.ensure_label(storage)
    found = sungold.label_entities_and_device(storage)
    ordered = sungold.ordered_entities(found)
    sungold.upsert_solar_section(storage, ordered)

    labels = json.loads((storage / "core.label_registry").read_text(encoding="utf-8"))
    row = labels["data"]["labels"][0]
    assert row["label_id"] == "sungold"
    assert row["name"] == "Sungold"
    assert row["icon"] == "mdi:solar-power-variant"

    ents = json.loads((storage / "core.entity_registry").read_text(encoding="utf-8"))
    by_id = {e["entity_id"]: e for e in ents["data"]["entities"]}
    assert "sungold" in by_id["sensor.sungold_sph302480a_pv_input_voltage"]["labels"]
    assert "sungold" in by_id["sensor.sungold_sph302480a_load_active_power"]["labels"]
    assert "sungold" not in by_id["sensor.sungold_sph302480a_pv_voltage"]["labels"]
    assert "sungold" not in by_id["sensor.battery_1_voltage"]["labels"]

    devs = json.loads((storage / "core.device_registry").read_text(encoding="utf-8"))
    assert "sungold" in devs["data"]["devices"][0]["labels"]

    solar = json.loads((storage / "lovelace.dashboard_solar").read_text(encoding="utf-8"))
    sections = solar["data"]["config"]["views"][0]["sections"]
    assert len(sections) == 2
    heading = sections[1]["cards"][0]
    assert heading == {
        "type": "heading",
        "heading": "Sungold",
        "icon": "mdi:solar-power-variant",
    }
    tiles = [c["entity"] for c in sections[1]["cards"][1:]]
    assert tiles[0] == "sensor.sungold_sph302480a_pv_input_voltage"
    assert tiles[1] == "sensor.sungold_sph302480a_load_active_power"
    assert "sensor.sungold_sph302480a_pv_voltage" not in tiles
    assert sungold.RETIRED_UNIQUE_IDS.isdisjoint(sungold.PREFERRED_UNIQUE_IDS)


def test_heading_only_when_registry_empty(tmp_path: Path) -> None:
    storage = tmp_path / ".storage"
    storage.mkdir()
    _write(
        storage / "core.entity_registry",
        {
            "version": 1,
            "minor_version": 1,
            "key": "core.entity_registry",
            "data": {"entities": []},
        },
    )
    _write(
        storage / "core.device_registry",
        {
            "version": 1,
            "minor_version": 1,
            "key": "core.device_registry",
            "data": {"devices": []},
        },
    )
    _write(storage / "lovelace.dashboard_solar", _solar_stub())

    found = sungold.label_entities_and_device(storage)
    ordered = sungold.ordered_entities(found)
    sungold.upsert_solar_section(storage, ordered)
    solar = json.loads((storage / "lovelace.dashboard_solar").read_text(encoding="utf-8"))
    cards = solar["data"]["config"]["views"][0]["sections"][1]["cards"]
    assert cards == [
        {"type": "heading", "heading": "Sungold", "icon": "mdi:solar-power-variant"}
    ]
    assert not any(c.get("type") == "tile" for c in cards)
