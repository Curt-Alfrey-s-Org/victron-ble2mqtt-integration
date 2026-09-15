"""Validate sim soak plug HA package (entity contract + watt table)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "config" / "packages" / "sim_soak_plugs.yaml"

EXPECTED_SWITCHES = {
    "switch.sim_ac_plug_1": ("sim_ac_plug_1", 180, "input_boolean.sim_ac_plug_1_internal"),
    "switch.sim_ac_plug_2": ("sim_ac_plug_2", 300, "input_boolean.sim_ac_plug_2_internal"),
    "switch.sim_ac_plug_3": ("sim_ac_plug_3", 1200, "input_boolean.sim_ac_plug_3_internal"),
    "switch.sim_ac_plug_4": ("sim_ac_plug_4", 130, "input_boolean.sim_ac_plug_4_internal"),
    "switch.sim_ac_plug_5": ("sim_ac_plug_5", 130, "input_boolean.sim_ac_plug_5_internal"),
    "switch.sim_ac_plug_6": ("sim_ac_plug_6", 300, "input_boolean.sim_ac_plug_6_internal"),
}


def _load_package() -> dict:
    assert PACKAGE.is_file(), f"missing {PACKAGE}"
    return yaml.safe_load(PACKAGE.read_text(encoding="utf-8"))


def test_input_boolean_internal_helpers_exist():
    data = _load_package()
    ib = data.get("input_boolean") or {}
    for _switch_id, (_uid, _w, internal) in EXPECTED_SWITCHES.items():
        key = internal.replace("input_boolean.", "")
        assert key in ib, f"missing input_boolean {key}"


def test_template_switches_pinned_entity_ids():
    data = _load_package()
    blocks = data.get("template") or []
    switches = []
    for block in blocks:
        if "switch" in block:
            switches.extend(block["switch"])
    assert len(switches) == 6
    seen_default: set[str] = set()
    for sw in switches:
        default_id = sw["default_entity_id"]
        assert default_id.startswith("switch.sim_ac_plug_")
        assert default_id not in seen_default
        seen_default.add(default_id)
        assert sw["unique_id"] == default_id.replace("switch.", "")
        assert "device_class" not in sw
        assert "turn_on" in sw and "turn_off" in sw
        turn_on = sw["turn_on"][0]
        turn_off = sw["turn_off"][0]
        assert turn_on["action"] == "input_boolean.turn_on"
        assert turn_off["action"] == "input_boolean.turn_off"
        internal = turn_on["target"]["entity_id"]
        assert internal.startswith("input_boolean.sim_ac_plug_")
        assert internal.endswith("_internal")
    assert seen_default == set(EXPECTED_SWITCHES.keys())


def test_power_sensors_watts_and_metadata():
    data = _load_package()
    blocks = data.get("template") or []
    sensors = []
    for block in blocks:
        if "sensor" in block:
            sensors.extend(block["sensor"])
    power_sensors = [s for s in sensors if s.get("default_entity_id", "").startswith("sensor.sim_ac_plug_")]
    assert len(power_sensors) == 6
    for sw_entity, (uid, watts, internal) in EXPECTED_SWITCHES.items():
        n = sw_entity.replace("switch.sim_ac_plug_", "")
        sensor = next(s for s in power_sensors if s["default_entity_id"] == f"sensor.sim_ac_plug_{n}_power")
        assert sensor["unique_id"] == f"sim_ac_plug_{n}_power"
        assert sensor["device_class"] == "power"
        assert sensor["state_class"] == "measurement"
        assert sensor["unit_of_measurement"] == "W"
        state_tpl = sensor["state"]
        assert str(watts) in state_tpl
        assert internal in state_tpl
        assert "{{ none }}" in state_tpl


def test_total_load_sensor_present():
    data = _load_package()
    blocks = data.get("template") or []
    sensors = []
    for block in blocks:
        if "sensor" in block:
            sensors.extend(block["sensor"])
    total = next(s for s in sensors if s.get("default_entity_id") == "sensor.sim_soak_load_power")
    assert total["device_class"] == "power"
    assert "180" in total["state"] and "1200" in total["state"]
