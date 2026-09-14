"""ha_label_victron_refoss.py — Victron/Refoss labels + official headings."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ha_label_victron_refoss as vr  # noqa: E402


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_victron_refoss_labels_and_headings(tmp_path: Path) -> None:
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
                        "entity_id": "sensor.battery_1_voltage",
                        "labels": [],
                        "device_id": "batt1",
                    },
                    {
                        "entity_id": "sensor.solar_controller_solar",
                        "labels": [],
                        "device_id": "mppt",
                    },
                    {
                        "entity_id": "sensor.em16_a3_power",
                        "labels": [],
                        "device_id": "em16",
                    },
                    {
                        "entity_id": "sensor.em16_a3_voltage",
                        "labels": [],
                        "device_id": "em16",
                    },
                    {
                        "entity_id": "sensor.em16_b2_power",
                        "labels": [],
                        "device_id": "em16",
                    },
                    {
                        "entity_id": "sensor.mppt_charger_solar_power",
                        "labels": [],
                        "device_id": "ble-leftover",
                        "disabled_by": "user",
                    },
                    {
                        "entity_id": "sensor.sungold_sph302480a_pv_voltage",
                        "labels": ["sungold"],
                        "device_id": "sungold",
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
                        "id": "batt1",
                        "name": "Battery 1",
                        "manufacturer": "Victron Energy",
                        "model": "SmartShunt 500A/50mV",
                        "labels": [],
                        "identifiers": [["mqtt", "pi4-d4effbb3d70c"]],
                    },
                    {
                        "id": "mppt",
                        "name": "Solar-controller",
                        "manufacturer": "Victron Energy",
                        "model": "BlueSolar Charger MPPT 75/15 rev3",
                        "labels": [],
                        "identifiers": [["mqtt", "pi4-d769eb1ff83d"]],
                    },
                    {
                        "id": "em16",
                        "name": "em16",
                        "manufacturer": "Refoss",
                        "labels": [],
                        "identifiers": [["refoss", "c4:e7:ae:0e:10:3d"]],
                    },
                    {
                        "id": "ble-leftover",
                        "name": "Mppt charger",
                        "manufacturer": "Victron Energy BV",
                        "labels": [],
                        "disabled_by": "user",
                        "identifiers": [["bluetooth", "D7:69:EB:1F:F8:3D"]],
                    },
                    {
                        "id": "sungold",
                        "name": "Sungold SPH302480A",
                        "manufacturer": "SunGoldPower",
                        "labels": ["sungold"],
                        "identifiers": [["mqtt", "sungold_sph302480a"]],
                    },
                ]
            },
        },
    )
    _write(
        storage / "lovelace.dashboard_solar",
        {
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
                                },
                                {
                                    "type": "grid",
                                    "cards": [
                                        {
                                            "type": "heading",
                                            "heading": "SmartShunt HQ2239CQYT2",
                                        },
                                        {
                                            "type": "tile",
                                            "entity": "sensor.battery_1_voltage",
                                        },
                                    ],
                                },
                                {
                                    "type": "grid",
                                    "cards": [
                                        {"type": "heading", "heading": "Sungold"},
                                        {
                                            "type": "tile",
                                            "entity": "sensor.sungold_sph302480a_pv_voltage",
                                        },
                                    ],
                                },
                            ],
                        }
                    ]
                }
            },
        },
    )
    _write(
        storage / "lovelace.dashboard_refoss",
        {
            "version": 1,
            "minor_version": 1,
            "key": "lovelace.dashboard_refoss",
            "data": {
                "config": {
                    "views": [
                        {
                            "type": "sections",
                            "title": "view0",
                            "sections": [
                                {
                                    "type": "grid",
                                    "cards": [
                                        {"type": "heading", "heading": "em16"},
                                        {
                                            "type": "tile",
                                            "entity": "sensor.em16_a3_power",
                                        },
                                    ],
                                }
                            ],
                        }
                    ]
                }
            },
        },
    )
    _write(
        storage / "core.label_registry",
        {
            "version": 1,
            "minor_version": 2,
            "key": "core.label_registry",
            "data": {
                "labels": [
                    {
                        "label_id": "sungold",
                        "name": "Sungold",
                        "icon": "mdi:solar-power-variant",
                        "color": "#FFC107",
                        "description": "cart",
                        "created_at": "2026-01-01T00:00:00+00:00",
                        "modified_at": "2026-01-01T00:00:00+00:00",
                    }
                ]
            },
        },
    )

    vr.ensure_label(storage, vr.VICTRON_LABEL)
    vr.ensure_label(storage, vr.REFOSS_LABEL)
    v_devices, v_ents = vr.label_victron(storage)
    r_devices, r_ents = vr.label_refoss(storage)
    heading_changes = vr.rename_solar_headings(storage)
    n_sections = vr.upsert_refoss_dashboard(storage, r_ents)

    labels = json.loads((storage / "core.label_registry").read_text(encoding="utf-8"))
    by_id = {row["label_id"]: row for row in labels["data"]["labels"]}
    assert by_id["sungold"]["name"] == "Sungold"
    assert by_id["victron"]["name"] == "Victron"
    assert by_id["refoss"]["name"] == "Refoss"

    ents = json.loads((storage / "core.entity_registry").read_text(encoding="utf-8"))
    e_by = {e["entity_id"]: e for e in ents["data"]["entities"]}
    assert "victron" in e_by["sensor.battery_1_voltage"]["labels"]
    assert "victron" in e_by["sensor.solar_controller_solar"]["labels"]
    assert "refoss" in e_by["sensor.em16_a3_power"]["labels"]
    assert "victron" not in e_by["sensor.sungold_sph302480a_pv_voltage"]["labels"]
    assert "victron" not in e_by["sensor.mppt_charger_solar_power"]["labels"]

    devs = json.loads((storage / "core.device_registry").read_text(encoding="utf-8"))
    d_by = {d["id"]: d for d in devs["data"]["devices"]}
    assert "victron" in d_by["batt1"]["labels"]
    assert d_by["em16"]["name_by_user"] == "Refoss Smart Energy Monitor, EM16"
    assert "refoss" in d_by["em16"]["labels"]
    assert "victron" not in (d_by["ble-leftover"].get("labels") or [])

    solar = json.loads((storage / "lovelace.dashboard_solar").read_text(encoding="utf-8"))
    headings = [
        card["heading"]
        for section in solar["data"]["config"]["views"][0]["sections"]
        for card in section["cards"]
        if card.get("type") == "heading"
    ]
    assert headings == [
        "BlueSolar MPPT 75/15",
        "SmartShunt HQ2239CQYT2",
        "Sungold",
    ]
    assert heading_changes == ["Mppt charger -> BlueSolar MPPT 75/15"]
    solar_tiles = [
        card
        for section in solar["data"]["config"]["views"][0]["sections"]
        for card in section["cards"]
        if card.get("type") == "tile"
    ]
    assert all(card.get("name") == {"type": "entity"} for card in solar_tiles)

    refoss = json.loads((storage / "lovelace.dashboard_refoss").read_text(encoding="utf-8"))
    view = refoss["data"]["config"]["views"][0]
    assert view["title"] == "Refoss"
    section_headings = [
        card["heading"]
        for section in view["sections"]
        for card in section["cards"]
        if card.get("type") == "heading"
    ]
    assert section_headings == ["A3", "B2"]
    assert n_sections == 2
    assert "Battery 1" in v_devices
    assert r_devices == ["Refoss Smart Energy Monitor, EM16"]


def test_em16_channel_table():
    assert vr.EM16_CHANNELS[0] == "A1"
    assert vr.EM16_CHANNELS[5] == "A6"
    assert vr.EM16_CHANNELS[6] == "B1"
    assert vr.EM16_CHANNELS[-1] == "C6"
    assert vr.em16_entity_id("A3", "power") == "sensor.em16_a3_power"
