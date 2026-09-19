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
    docs = DOCS.read_text(encoding="utf-8")
    assert "Home Assistant owns dump-load" in docs
    assert "dump_ac_limit_t2_w" in docs
    assert "dump_batt_t2_ok" in docs
    assert "dump_plug_N_power_entity" in docs
    assert "dump_plug_N_inverter" in docs
    assert "dump_plug_N_watts" not in docs
    assert "sensor.battery_1_power" in docs
    assert "sensor.battery_2_power" in docs
    assert "sensor.sungold_sph302480a_load_power" in docs
    assert "You do **not** type the wattage" in docs
    assert "ha_set_number" in docs
    assert "2000" in docs
    assert "sensor.dump_next_plug" in docs
    assert "sim_dump_turn_off_unknown_watts" in docs
    assert "Already-ON leftover" in docs
    assert "dump_charge_float" in docs
    assert "dump_solar_present" in docs
    assert "dump_rebulk" in docs
    assert "95%" in docs
    assert INSTALL.is_file()
    text = INSTALL.read_text(encoding="utf-8")
    assert "sim_dump_control.yaml" in text
    assert "install_sim_dump_plugs_ha.sh" in text
    assert "solar-plant.yaml" in text


def test_kill_switch_and_timers() -> None:
    data = _load()
    assert "dump_control_enabled" in (data.get("input_boolean") or {})
    numbers = data.get("input_number") or {}
    for key in ("dump_ac_limit_t2_w", "dump_ac_limit_ku_w", "dump_ac_limit_sph_w"):
        ac_limit = numbers[key]
        assert ac_limit["initial"] == 2000
        assert ac_limit["unit_of_measurement"] == "W"
        assert ac_limit["min"] == 500
        assert ac_limit["max"] == 4000
    assert numbers["dump_max_discharge_t2_w"]["initial"] == 0
    assert numbers["dump_max_discharge_ku_w"]["initial"] == 0
    assert numbers["dump_max_discharge_sph_w"]["initial"] == 50
    assert numbers["dump_float_t2_v"]["initial"] == 27.0
    assert numbers["dump_rebulk_t2_v"]["initial"] == 26.8
    assert numbers["dump_min_solar_w"]["initial"] == 50
    assert numbers["dump_min_soc_percent"]["initial"] == 95
    assert "dump_plug_1_watts" not in numbers
    booleans = data.get("input_boolean") or {}
    assert booleans["dump_soc_unsynced"].get("initial") is True
    selects = data.get("input_select") or {}
    for n in range(1, 7):
        sel = selects[f"dump_plug_{n}_inverter"]
        assert sel["options"] == ["T2", "KU", "SPH"]
        assert sel["initial"] == "SPH"
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
    nxt = next(s for s in sensors if s.get("default_entity_id") == "sensor.dump_next_plug")
    nxt_state = nxt["state"]
    assert "sensor.sim_ac_plug_1_power" in nxt_state
    assert "sensor.dump_plug_1_last_w" in nxt_state
    assert "input_number.dump_plug_1_watts" not in nxt_state
    assert "input_number.dump_ac_limit_t2_w" in nxt_state
    assert "input_number.dump_ac_limit_ku_w" in nxt_state
    assert "input_number.dump_ac_limit_sph_w" in nxt_state
    assert "sensor.battery_1_power" in nxt_state
    assert "sensor.battery_2_power" in nxt_state
    assert "sensor.sungold_sph302480a_load_power" in nxt_state
    assert "binary_sensor.dump_batt_t2_ok" in nxt_state
    assert "binary_sensor.dump_batt_ku_ok" in nxt_state
    assert "binary_sensor.dump_batt_sph_ok" in nxt_state
    assert "binary_sensor.dump_charge_float" in nxt_state
    assert "binary_sensor.dump_solar_present" in nxt_state
    assert "binary_sensor.dump_v_float_t2" in nxt_state
    assert "binary_sensor.dump_v_rebulk_t2" in nxt_state
    assert "last_w <= surplus" not in nxt_state
    charge = next(b for b in binaries if b.get("default_entity_id") == "binary_sensor.dump_charge_ok")
    assert "absorption" in charge["state"]
    assert "float" in charge["state"]
    flt = next(b for b in binaries if b.get("default_entity_id") == "binary_sensor.dump_charge_float")
    assert "float" in flt["state"]
    assert "absorption" not in flt["state"]
    solar = next(b for b in binaries if b.get("default_entity_id") == "binary_sensor.dump_solar_present")
    assert "input_number.dump_min_solar_w" in solar["state"]
    rebulk = next(b for b in binaries if b.get("default_entity_id") == "binary_sensor.dump_v_rebulk_t2")
    assert "input_number.dump_rebulk_t2_v" in rebulk["state"]
    t2_ok = next(b for b in binaries if b.get("default_entity_id") == "binary_sensor.dump_batt_t2_ok")
    assert "sensor.battery_1_power" in t2_ok["state"]
    ku_ok = next(b for b in binaries if b.get("default_entity_id") == "binary_sensor.dump_batt_ku_ok")
    assert "sensor.battery_2_power" in ku_ok["state"]
    sph_ok = next(b for b in binaries if b.get("default_entity_id") == "binary_sensor.dump_batt_sph_ok")
    assert "sensor.sungold_sph302480a_battery_current" in sph_ok["state"]
    assert "sensor.sungold_sph302480a_battery_voltage" in sph_ok["state"]


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
        "sim_dump_turn_off_solar_gone",
        "sim_dump_turn_off_bulk",
        "sim_dump_turn_off_rebulk_t2",
        "sim_dump_turn_off_rebulk_ku",
        "sim_dump_turn_off_rebulk_sph",
        "sim_dump_turn_off_batt_t2",
        "sim_dump_turn_off_batt_ku",
        "sim_dump_turn_off_batt_sph",
        "sim_dump_turn_off_unknown_watts",
    }
    on = by_id["sim_dump_turn_on"]
    off_s = by_id["sim_dump_turn_off_solar_gone"]
    off_b = by_id["sim_dump_turn_off_bulk"]
    off_batt = (
        by_id["sim_dump_turn_off_batt_t2"],
        by_id["sim_dump_turn_off_batt_ku"],
        by_id["sim_dump_turn_off_batt_sph"],
    )
    off_rebulk = (
        by_id["sim_dump_turn_off_rebulk_t2"],
        by_id["sim_dump_turn_off_rebulk_ku"],
        by_id["sim_dump_turn_off_rebulk_sph"],
    )
    for auto in (off_s, off_b) + off_batt + off_rebulk:
        for trig in auto["triggers"]:
            if trig.get("trigger") == "state":
                assert trig.get("for") == "00:01:00"
    on_state_trigs = [
        t for t in on["triggers"] if t.get("trigger") == "state" and t.get("entity_id") != "sensor.dump_next_plug"
    ]
    assert {t["entity_id"] for t in on_state_trigs} == {
        "binary_sensor.dump_charge_float",
        "binary_sensor.dump_solar_present",
    }
    for trig in on_state_trigs:
        assert trig.get("for") == "00:01:00"
    unk = by_id["sim_dump_turn_off_unknown_watts"]
    unk_by_id = {t.get("id"): t for t in unk["triggers"]}
    assert unk_by_id["unknown_dwell"]["trigger"] == "template"
    assert unk_by_id["unknown_dwell"]["for"] == "00:00:15"
    assert "sensor.sim_ac_plug_1_power" in unk_by_id["unknown_dwell"]["value_template"]
    assert unk_by_id["ha_start"] == {
        "trigger": "homeassistant",
        "id": "ha_start",
        "event": "start",
    }
    assert unk_by_id["autos_reloaded"]["event_type"] == "automation_reloaded"
    unk_txt = str(unk["actions"])
    assert "00:00:15" in unk_txt
    assert "switch.turn_off" in unk_txt
    assert "timer.cancel" in unk_txt
    assert "timer.dump_min_on" in unk_txt
    assert "dump_control_enabled" in str(unk["conditions"])
    on_repeat = on["actions"][0]["repeat"]
    on_seq = on_repeat["sequence"]
    seq_txt = str(on_seq)
    assert "wait_template" in seq_txt
    assert "dump plug reported no live watts" in seq_txt
    turn_on = next(a for a in on_seq if a.get("action") == "switch.turn_on")
    assert "{{ target }}" in str(turn_on["target"]["entity_id"])
    assert PLUGS != turn_on["target"]["entity_id"]
    while_t = " ".join(str(c) for c in on_repeat["while"])
    assert "dump_next_plug" in while_t
    assert "dump_charge_float" in while_t
    assert "dump_solar_present" in while_t
    assert "dump_surplus_high" not in while_t
    assert "repeat.index" in while_t
    assert any(a.get("delay") == 1 for a in on_seq)
    assert any(
        a.get("action") == "timer.start"
        and a.get("target", {}).get("entity_id") == "timer.dump_min_on"
        for a in on_seq
    )
    assert off_s["actions"][0]["action"] == "switch.turn_off"
    assert off_b["actions"][0]["action"] == "switch.turn_off"
    assert any(
        a.get("action") == "timer.cancel" for a in off_s["actions"]
    ), "solar-gone off must cancel min-on timer"
    assert any(
        a.get("action") == "timer.cancel" for a in off_b["actions"]
    ), "bulk off must cancel min-on timer"
    assert by_id["sim_dump_turn_off_batt_t2"]["triggers"][0]["entity_id"] == (
        "binary_sensor.dump_batt_t2_ok"
    )
    assert by_id["sim_dump_turn_off_rebulk_t2"]["triggers"][0]["entity_id"] == (
        "binary_sensor.dump_v_rebulk_t2"
    )
    ku_each = by_id["sim_dump_turn_off_batt_ku"]["actions"][0]["repeat"]["for_each"]
    assert any(item.get("select") == "input_select.dump_plug_3_inverter" for item in ku_each)
