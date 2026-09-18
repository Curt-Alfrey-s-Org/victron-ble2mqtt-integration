"""ha_set_display_precision.py — tenths on numeric HA sensors."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ha_set_display_precision as prec  # noqa: E402


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_skips_timestamp_and_switches(tmp_path: Path) -> None:
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
                        "entity_id": "sensor.em16_a3_power",
                        "original_device_class": "power",
                        "options": {"sensor": {"unit_of_measurement": "W"}},
                    },
                    {
                        "entity_id": "sensor.em16_a3_power_factor",
                        "original_device_class": "power_factor",
                        "options": {
                            "sensor": {
                                "display_precision": 2,
                                "suggested_display_precision": 2,
                            }
                        },
                    },
                    {
                        "entity_id": "sensor.battery_1_remaining_minutes",
                        "original_device_class": "duration",
                        "options": {},
                    },
                    {
                        "entity_id": "sensor.last_seen",
                        "original_device_class": "timestamp",
                    },
                    {"entity_id": "switch.sim_ac_plug_1"},
                    {
                        "entity_id": "number.example_setpoint",
                        "options": {},
                    },
                ]
            },
        },
    )
    stats = prec.apply_storage(storage, 1)
    assert stats["updated"] == 4
    assert stats["skipped"] == 2
    assert stats["unchanged"] == 0
    ents = {e["entity_id"]: e for e in json.loads(
        (storage / "core.entity_registry").read_text(encoding="utf-8")
    )["data"]["entities"]}
    power = ents["sensor.em16_a3_power"]["options"]["sensor"]
    assert power["display_precision"] == 1
    assert power["suggested_display_precision"] == 1
    assert power["unit_of_measurement"] == "W"
    pf = ents["sensor.em16_a3_power_factor"]["options"]["sensor"]
    assert pf["display_precision"] == 1
    assert pf["suggested_display_precision"] == 1
    minutes = ents["sensor.battery_1_remaining_minutes"]["options"]["sensor"]
    assert minutes["display_precision"] == 1
    assert "options" not in ents["sensor.last_seen"] or "sensor" not in ents[
        "sensor.last_seen"
    ].get("options", {})
    assert ents["switch.sim_ac_plug_1"].get("options") in (None, {})
    num = ents["number.example_setpoint"]["options"]["number"]
    assert num["display_precision"] == 1
    assert "suggested_display_precision" not in num
    assert (storage / "core.entity_registry.bak-display-precision").is_file()


def test_idempotent_second_run(tmp_path: Path) -> None:
    storage = tmp_path / ".storage"
    storage.mkdir()
    _write(
        storage / "core.entity_registry",
        {
            "version": 1,
            "key": "core.entity_registry",
            "data": {
                "entities": [
                    {
                        "entity_id": "sensor.solar_controller_solar",
                        "original_device_class": "power",
                        "options": {
                            "sensor": {
                                "display_precision": 1,
                                "suggested_display_precision": 1,
                            }
                        },
                    }
                ]
            },
        },
    )
    first = prec.apply_storage(storage, 1)
    second = prec.apply_storage(storage, 1)
    assert first["updated"] == 0
    assert first["unchanged"] == 1
    assert second["updated"] == 0
    assert second["unchanged"] == 1


def test_docs_name_the_apply_script() -> None:
    docs = (ROOT / "docs" / "SOLAR_HA_DASHBOARD.md").read_text(encoding="utf-8")
    devices = (ROOT / "docs" / "DEVICES.md").read_text(encoding="utf-8")
    assert "apply_ha_display_precision.sh" in docs
    assert "display_precision" in docs
    assert "apply_ha_display_precision.sh" in devices
    script = (ROOT / "scripts" / "apply_ha_display_precision.sh").read_text(
        encoding="utf-8"
    )
    assert "docker stop homeassistant" in script
    assert "ha_set_display_precision.py" in script
