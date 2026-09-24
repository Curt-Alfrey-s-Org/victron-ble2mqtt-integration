"""Validate HA dump-load CONTROL package (HA owns on/off)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "config" / "packages" / "sim_dump_control.yaml"
DOCS = ROOT / "docs" / "DUMP_LOAD_HA_CONTROL.md"
SIM_DOCS = ROOT / "docs" / "SIM_DUMP_PLUGS.md"
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
    assert "site confirm" in docs.lower() or "site load delta" in docs.lower()
    assert "dump_site_confirm_s" in docs
    assert "dump_site_delta_min_w" in docs
    assert "15 min" in docs or "00:15:00" in docs
    assert "10 min" in docs or "00:10:00" in docs
    assert "govee_ble" in docs
    assert "H5082" in docs
    assert "Shelly" not in docs
    assert "shelly" not in docs
    assert "sim_dump_turn_off_unknown_watts" not in docs
    assert "Already-ON leftover" not in docs
    assert "dump_charge_float" in docs
    assert "dump_solar_present" in docs
    assert "dump_load_exceeds_solar" in docs
    assert "dump_notify_service" in docs
    assert "dump_shed_plug" in docs
    assert "mobile_app_" in docs
    assert "dump_rebulk" in docs
    assert "95%" in docs
    assert INSTALL.is_file()
    text = INSTALL.read_text(encoding="utf-8")
    assert "sim_dump_control.yaml" in text
    assert "install_sim_dump_plugs_ha.sh" in text
    assert "Settings > Helpers" in docs or "Helpers" in docs
    assert "solar-plant.yaml" not in text
    sim_docs = SIM_DOCS.read_text(encoding="utf-8")
    assert "dump_site_confirm_s" in sim_docs
    assert "govee_ble" in sim_docs
    assert "H5082" in sim_docs
    assert "Shelly" not in sim_docs
    assert "shelly" not in sim_docs


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
    assert numbers["dump_site_confirm_s"]["initial"] == 5
    assert numbers["dump_site_confirm_s"]["min"] == 5
    assert numbers["dump_site_confirm_s"]["max"] == 30
    assert numbers["dump_site_delta_min_w"]["initial"] == 25
    assert numbers["dump_site_delta_min_w"]["min"] == 5
    assert numbers["dump_site_delta_min_w"]["max"] == 500
    texts = data.get("input_text") or {}
    assert texts["dump_notify_service"]["initial"] == "persistent_notification"
    assert "dump_plug_1_watts" not in numbers
    booleans = data.get("input_boolean") or {}
    assert booleans["dump_soc_unsynced"].get("initial") is True
    selects = data.get("input_select") or {}
    for n in range(1, 7):
        sel = selects[f"dump_plug_{n}_inverter"]
        assert sel["options"] == ["T2", "KU", "Sungold"]
        assert sel["initial"] == "Sungold"
    timers = data.get("timer") or {}
    assert "dump_min_on" not in timers
    assert "dump_min_off" not in timers
    for n in range(1, 7):
        assert timers[f"dump_plug_{n}_min_on"]["duration"] == "00:15:00"
        assert timers[f"dump_plug_{n}_cooldown"]["duration"] == "00:10:00"
        assert timers[f"dump_plug_{n}_min_on"].get("restore") is True
        assert timers[f"dump_plug_{n}_cooldown"].get("restore") is True


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
    t2_load = next(s for s in sensors if s.get("default_entity_id") == "sensor.dump_bus_load_t2")
    assert "sensor.battery_1_power" in t2_load["state"]
    ku_load = next(s for s in sensors if s.get("default_entity_id") == "sensor.dump_bus_load_ku")
    assert "sensor.battery_2_power" in ku_load["state"]
    sph_load = next(s for s in sensors if s.get("default_entity_id") == "sensor.dump_bus_load_sph")
    assert "sensor.sungold_sph302480a_load_power" in sph_load["state"]
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
    assert "timer.dump_plug_" in nxt_state
    assert "_cooldown" in nxt_state
    assert "is_state(cd, 'idle')" in nxt_state
    assert "ns.blocked" not in nxt_state
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
    exceeds = next(b for b in binaries if b.get("default_entity_id") == "binary_sensor.dump_load_exceeds_solar")
    assert "sensor.site_solar_power" in exceeds["state"]
    assert "sensor.sungold_sph302480a_load_power" in exceeds["state"]
    shed = next(s for s in sensors if s.get("default_entity_id") == "sensor.dump_shed_plug")
    assert "switch.sim_ac_plug_" in shed["state"]
    assert "range(6, 0, -1)" in shed["state"]
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
        "sim_dump_shed_load_exceeds_solar",
        "sim_dump_notify_load_exceeds_solar",
        "sim_dump_turn_off_rebulk_t2",
        "sim_dump_turn_off_rebulk_ku",
        "sim_dump_turn_off_rebulk_sph",
        "sim_dump_turn_off_batt_t2",
        "sim_dump_turn_off_batt_ku",
        "sim_dump_turn_off_batt_sph",
    }
    assert "sim_dump_turn_off_unknown_watts" not in by_id
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
    on_repeat = on["actions"][0]["repeat"]
    on_seq = on_repeat["sequence"]
    seq_txt = str(on_seq)
    assert "wait_template" not in seq_txt
    assert "dump plug reported no live watts" not in seq_txt
    assert "dump_site_confirm_s" in seq_txt
    assert "dump_site_delta_min_w" in seq_txt
    assert "dump_bus_load_t2" in seq_txt
    assert "dump_bus_load_ku" in seq_txt
    assert "dump_bus_load_sph" in seq_txt
    assert "confirmed" in seq_txt
    not_conf = next(
        a
        for a in on_seq
        if a.get("if")
        and any(
            "not confirmed" in str(c.get("value_template", ""))
            for c in (a.get("if") or [])
        )
    )
    assert "stop" not in str(not_conf.get("then") or [])
    turn_on = next(a for a in on_seq if a.get("action") == "switch.turn_on")
    assert "{{ target }}" in str(turn_on["target"]["entity_id"])
    assert PLUGS != turn_on["target"]["entity_id"]
    delay_confirm = next(
        a for a in on_seq if isinstance(a, dict) and "delay" in a and "dump_site_confirm_s" in str(a["delay"])
    )
    assert delay_confirm is not None
    assert "timer.dump_plug_" in seq_txt and "min_on" in seq_txt
    assert seq_txt.index("dump_site_confirm_s") < seq_txt.index("min_on")
    assert seq_txt.index("switch.turn_on") < seq_txt.index("dump_site_confirm_s")
    while_t = " ".join(str(c) for c in on_repeat["while"])
    assert "dump_next_plug" in while_t
    assert "dump_charge_float" in while_t
    assert "dump_solar_present" in while_t
    assert "dump_surplus_high" not in while_t
    assert "repeat.index" in while_t
    assert "timer.dump_min_off" not in str(on["conditions"])
    off_s_txt = str(off_s["actions"])
    assert "timer.dump_plug_1_min_on" in off_s_txt
    assert "timer.dump_plug_1_cooldown" in off_s_txt
    assert "timer.dump_min_on" not in off_s_txt
    assert off_s["actions"][0]["action"] == "switch.turn_off"
    bulk_txt = str(off_b["actions"])
    assert "sensor.dump_shed_plug" in bulk_txt
    assert "repeat.index" in bulk_txt
    assert "timer.dump_plug_" in bulk_txt
    assert "cooldown" in bulk_txt
    shed_over = by_id["sim_dump_shed_load_exceeds_solar"]
    assert shed_over["triggers"][0]["entity_id"] == "binary_sensor.dump_load_exceeds_solar"
    assert shed_over["triggers"][0]["for"] == "00:01:00"
    assert "sensor.dump_shed_plug" in str(shed_over["actions"])
    note = by_id["sim_dump_notify_load_exceeds_solar"]
    assert note["triggers"][0]["for"] == "00:10:00"
    assert "notify.persistent_notification" in str(note["actions"])
    assert "dump_notify_service" in str(note["actions"])
    assert "switch.turn_off" not in str(note["actions"])
    assert any(
        a.get("action") == "timer.cancel" for a in off_s["actions"]
    ), "solar-gone off must cancel min-on timers"
    assert any(
        a.get("action") == "timer.start" for a in off_s["actions"]
    ), "solar-gone off must start cooldown timers"
    assert "timer.cancel" in bulk_txt
    assert "timer.start" in bulk_txt
    rebulk_t2_txt = str(by_id["sim_dump_turn_off_rebulk_t2"]["actions"])
    assert "timer.start" in rebulk_t2_txt
    assert "timer.cancel" in rebulk_t2_txt
    assert "cooldown" in rebulk_t2_txt
    assert "min_on" in rebulk_t2_txt
    assert by_id["sim_dump_turn_off_batt_t2"]["triggers"][0]["entity_id"] == (
        "binary_sensor.dump_batt_t2_ok"
    )
    assert by_id["sim_dump_turn_off_rebulk_t2"]["triggers"][0]["entity_id"] == (
        "binary_sensor.dump_v_rebulk_t2"
    )
    ku_each = by_id["sim_dump_turn_off_batt_ku"]["actions"][0]["repeat"]["for_each"]
    assert any(item.get("select") == "input_select.dump_plug_3_inverter" for item in ku_each)
