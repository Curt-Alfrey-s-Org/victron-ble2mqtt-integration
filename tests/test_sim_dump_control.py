"""Validate HA dump-load CONTROL package (HA owns on/off)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "config" / "packages" / "sim_dump_control.yaml"
DOCS = ROOT / "docs" / "DUMP_LOAD_HA_CONTROL.md"
INSTALL = ROOT / "scripts" / "install_sim_dump_control_ha.sh"

PLUGS = [
    "switch.sim_ac_plug_1",
    "switch.sim_ac_plug_2",
    "switch.sim_ac_plug_3",
    "switch.sim_ac_plug_4",
    "switch.sim_ac_plug_5",
    "switch.sim_ac_plug_6",
]


def _load() -> dict:
    assert PACKAGE.is_file(), f"missing {PACKAGE}"
    data = yaml.safe_load(PACKAGE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_docs_and_install_exist() -> None:
    assert DOCS.is_file()
    assert "Home Assistant owns dump-load" in DOCS.read_text(encoding="utf-8")
    assert INSTALL.is_file()
    text = INSTALL.read_text(encoding="utf-8")
    assert "sim_dump_control.yaml" in text
    assert "install_sim_dump_plugs_ha.sh" in text


def test_kill_switch_and_timers() -> None:
    data = _load()
    assert "dump_control_enabled" in (data.get("input_boolean") or {})
    timers = data.get("timer") or {}
    assert timers["dump_min_on"]["duration"] == "00:10:00"
    assert timers["dump_min_off"]["duration"] == "00:05:00"
    assert timers["dump_min_on"].get("restore") is True


def test_surplus_template_and_charge_ok() -> None:
    data = _load()
    sensors = []
    binaries = []
    for block in data.get("template") or []:
        sensors.extend(block.get("sensor") or [])
        binaries.extend(block.get("binary_sensor") or [])
    surplus = next(s for s in sensors if s.get("default_entity_id") == "sensor.dump_surplus_w")
    assert "sensor.solar_controller_solar" in surplus["state"]
    assert "sensor.sim_dump_load_power" in surplus["state"]
    charge = next(b for b in binaries if b.get("default_entity_id") == "binary_sensor.dump_charge_ok")
    assert "absorption" in charge["state"]
    assert "float" in charge["state"]


def test_threshold_hysteresis_200_50() -> None:
    data = _load()
    helpers = data.get("binary_sensor") or []
    high = next(h for h in helpers if h.get("name") == "Dump surplus high")
    assert high["platform"] == "threshold"
    assert high["entity_id"] == "sensor.dump_surplus_w"
    assert high["upper"] == 125
    assert high["hysteresis"] == 75
    falling = next(h for h in helpers if h.get("name") == "Dump PV falling")
    assert falling["platform"] == "threshold"
    assert falling["lower"] == 0
    assert falling["hysteresis"] == 5


def test_automations_use_switch_services_and_dwell() -> None:
    data = _load()
    autos = data.get("automation dump_load") or data.get("automation")
    assert isinstance(autos, list)
    by_id = {a["id"]: a for a in autos}
    assert set(by_id) == {
        "sim_dump_turn_on",
        "sim_dump_turn_off_surplus",
        "sim_dump_turn_off_bulk",
    }
    on = by_id["sim_dump_turn_on"]
    off_s = by_id["sim_dump_turn_off_surplus"]
    off_b = by_id["sim_dump_turn_off_bulk"]
    for auto in (on, off_s, off_b):
        for trig in auto["triggers"]:
            if trig.get("trigger") == "state":
                assert trig.get("for") == "00:01:00"
    on_action = on["actions"][0]
    assert on_action["action"] == "switch.turn_on"
    assert on_action["target"]["entity_id"] == PLUGS
    assert off_s["actions"][0]["action"] == "switch.turn_off"
    assert off_b["actions"][0]["action"] == "switch.turn_off"
    assert any(
        a.get("action") == "timer.cancel" for a in off_b["actions"]
    ), "bulk off must cancel min-on timer"
