"""Dump-load control on the real H5082 sockets (config/packages/dump_control.yaml).

Structure checks always run. Template behaviour is rendered with jinja2 and a fake
HA state table when jinja2 is installed (HA's own template engine is Jinja2).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from govee_h5082.mqtt_bridge import PLUGS, SIDES

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "config" / "packages" / "dump_control.yaml"
DOCS = ROOT / "docs" / "DUMP_LOAD_HA_CONTROL.md"
DASHBOARD = ROOT / "config" / "dashboards" / "solar-plant.yaml"
INSTALL = ROOT / "scripts" / "install_dump_control_ha.sh"

# C38D feeds the Pi 4; it is deliberately not a dump candidate.
PI_SUPPLY = "c38d"
# Stage order = plug id order (same as the Site solar cards and the label script).
SOCKS = [
    f"{plug}_{side}"
    for plug in sorted(name[-4:].lower() for _address, name in PLUGS)
    if plug != PI_SUPPLY
    for side, _port, _label in SIDES
]
ALL_H5082_SWITCHES = {
    f"switch.{name.lower()}_{label.lower()}" for _a, name in PLUGS for _s, _p, label in SIDES
}


def _load() -> dict:
    data = yaml.safe_load(PACKAGE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _templates() -> dict[str, dict]:
    out = {}
    for block in _load()["template"]:
        for row in block.get("sensor", []) + block.get("binary_sensor", []):
            out[row["unique_id"]] = row
    return out


def _automations() -> dict[str, dict]:
    return {a["id"]: a for a in _load()["automation dump_load"]}


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def test_no_simulated_plugs_left() -> None:
    text = PACKAGE.read_text(encoding="utf-8")
    assert "sim_" not in text
    assert not (ROOT / "config" / "packages" / "sim_dump_control.yaml").exists()
    assert not (ROOT / "config" / "packages" / "sim_dump_plugs.yaml").exists()


def test_socket_list_matches_bridge_discovery() -> None:
    text = PACKAGE.read_text(encoding="utf-8")
    lists = re.findall(r"\[\s*('[0-9a-f]{4}_(?:left|right)'(?:,\s*'[0-9a-f]{4}_(?:left|right)')*)\s*\]", text)
    assert lists, "no socket list found"
    for raw in lists:
        assert re.findall(r"'([^']+)'", raw) == SOCKS
    # The switch ids the templates build are the ids HA gives the bridge's discovery.
    for s in SOCKS:
        assert f"switch.ihoment_h5082_{s}" in ALL_H5082_SWITCHES
    assert PI_SUPPLY not in text.split("# Victron float hold")[1]


def test_helpers_per_socket() -> None:
    data = _load()
    for s in SOCKS:
        sel = data["input_select"][f"h5082_{s}_inverter"]
        assert sel["options"] == ["Sungold", "T2", "KU"]
        assert "initial" not in sel  # bus choice must survive HA restarts
        assert data["timer"][f"h5082_{s}_min_on"]["duration"] == "00:15:00"
        assert data["timer"][f"h5082_{s}_cooldown"]["duration"] == "00:10:00"
        assert data["timer"][f"h5082_{s}_cooldown"]["restore"] is True
    # The per-socket use select is the UI helper from create_h5082_socket_labels.py;
    # defining it here too would collide with it.
    assert not any(k.endswith("_use") for k in data["input_select"])
    assert "dump_control_enabled" in data["input_boolean"]
    assert "initial" not in data["input_boolean"]["dump_control_enabled"]
    assert data["input_number"]["dump_site_confirm_s"]["initial"] == 5


def test_switch_actions_are_never_hardcoded() -> None:
    for auto in _automations().values():
        for node in _walk(auto["actions"]):
            if node.get("action") in ("switch.turn_on", "switch.turn_off"):
                target = node["target"]["entity_id"]
                assert "{{" in target, f"{auto['id']} hardcodes {target}"
                assert target in (
                    "{{ target }}",
                    "switch.ihoment_h5082_{{ repeat.item }}",
                ), target


def test_timings_kept() -> None:
    autos = _automations()
    assert set(autos) == {
        "dump_turn_on",
        "dump_turn_off_solar_gone",
        "dump_turn_off_bulk",
        "dump_shed_load_exceeds_solar",
        "dump_notify_load_exceeds_solar",
        "dump_turn_off_rebulk_t2",
        "dump_turn_off_rebulk_ku",
        "dump_turn_off_rebulk_sph",
        "dump_turn_off_batt_t2",
        "dump_turn_off_batt_ku",
        "dump_turn_off_batt_sph",
    }
    for aid, auto in autos.items():
        for trig in auto["triggers"]:
            if trig.get("entity_id") != "sensor.dump_next_plug":
                want = "00:10:00" if aid == "dump_notify_load_exceeds_solar" else "00:01:00"
                assert trig["for"] == want, aid
        if aid != "dump_notify_load_exceeds_solar":
            assert auto["conditions"][0] == {
                "condition": "state",
                "entity_id": "input_boolean.dump_control_enabled",
                "state": "on",
            }
    seq = autos["dump_turn_on"]["actions"][0]["repeat"]["sequence"]
    delays = [n["delay"] for n in seq if "delay" in n]
    assert "{{ states('input_number.dump_site_confirm_s') | int(5) }}" in delays
    for shed in ("dump_turn_off_bulk", "dump_shed_load_exceeds_solar"):
        seq = autos[shed]["actions"][0]["repeat"]["sequence"]
        assert seq[-1] == {"delay": "00:01:00"}


def test_turn_on_waits_for_the_plug_and_respects_kill_switch() -> None:
    auto = _automations()["dump_turn_on"]
    seq = auto["actions"][0]["repeat"]["sequence"]
    waits = [n for n in seq if "wait_template" in n]
    assert waits and waits[0]["wait_template"] == "{{ is_state(target, 'on') }}"
    whiles = auto["actions"][0]["repeat"]["while"]
    assert {"condition": "state", "entity_id": "input_boolean.dump_control_enabled", "state": "on"} in whiles
    blob = str(auto["conditions"]) + str(whiles)
    assert "binary_sensor.dump_load_exceeds_solar" in blob


def test_docs_and_install() -> None:
    docs = DOCS.read_text(encoding="utf-8")
    assert "dump_control.yaml" in docs
    assert "input_select.h5082_<id>_<side>_use" in docs
    assert "sim_ac_plug" not in docs
    text = INSTALL.read_text(encoding="utf-8")
    assert "dump_control.yaml" in text
    assert "sim_dump_control.yaml" in text  # removes the old copy on .105


def test_dashboard_references_real_dump_helpers() -> None:
    blob = DASHBOARD.read_text(encoding="utf-8")
    assert "sim_ac_plug" not in blob
    assert "dump_plug_" not in blob
    assert "timer.h5082_" in blob
    for s in SOCKS:
        assert f"input_select.h5082_{s}_inverter" in blob


# ---------------------------------------------------------------- template behaviour

jinja2 = pytest.importorskip("jinja2")


def _is_number(value) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def _render(template: str, states: dict[str, str]):
    env = jinja2.Environment()
    env.globals.update(
        states=lambda eid: states.get(eid, "unknown"),
        is_state=lambda eid, value: states.get(eid, "unknown") == value,
        is_number=_is_number,
    )
    return env.from_string(template).render().strip()


def _ok_states(**over) -> dict[str, str]:
    st = {
        "binary_sensor.dump_solar_present": "on",
        "binary_sensor.dump_charge_float": "on",
        "binary_sensor.dump_soc_ok": "on",
        "binary_sensor.dump_batt_sph_ok": "on",
        "binary_sensor.dump_batt_t2_ok": "on",
        "binary_sensor.dump_batt_ku_ok": "on",
        "binary_sensor.dump_v_float_sph": "on",
        "binary_sensor.dump_v_float_t2": "on",
        "binary_sensor.dump_v_float_ku": "on",
        "binary_sensor.dump_v_rebulk_sph": "off",
        "binary_sensor.dump_v_rebulk_t2": "off",
        "binary_sensor.dump_v_rebulk_ku": "off",
        "sensor.sungold_sph302480a_load_power": "300",
        "sensor.battery_1_power": "50",
        "sensor.battery_2_power": "40",
        "input_number.dump_ac_limit_sph_w": "2000",
        "input_number.dump_ac_limit_t2_w": "2000",
        "input_number.dump_ac_limit_ku_w": "2000",
    }
    for s in SOCKS:
        st[f"switch.ihoment_h5082_{s}"] = "off"
        st[f"input_select.h5082_{s}_use"] = "normal"
        st[f"input_select.h5082_{s}_inverter"] = "Sungold"
        st[f"timer.h5082_{s}_cooldown"] = "idle"
    st.update(over)
    return st


def _next(states):
    return _render(_templates()["dump_next_plug"]["state"], states)


def _shed(states):
    return _render(_templates()["dump_shed_plug"]["state"], states)


def test_next_plug_ignores_normal_sockets() -> None:
    assert _next(_ok_states()) == "none"


def test_next_plug_picks_first_eligible_dump_socket() -> None:
    st = _ok_states(**{
        "input_select.h5082_3013_right_use": "dump",
        "input_select.h5082_c061_left_use": "dump",
    })
    assert _next(st) == "switch.ihoment_h5082_3013_right"
    st["timer.h5082_3013_right_cooldown"] = "active"
    assert _next(st) == "switch.ihoment_h5082_c061_left"
    st["switch.ihoment_h5082_c061_left"] = "unavailable"  # bridge offline: never pick
    assert _next(st) == "none"


def test_next_plug_blocks_on_bus_and_site_conditions() -> None:
    base = {"input_select.h5082_2f9d_left_use": "dump", "input_select.h5082_2f9d_left_inverter": "T2"}
    assert _next(_ok_states(**base)) == "switch.ihoment_h5082_2f9d_left"
    for key, value in (
        ("binary_sensor.dump_v_rebulk_t2", "on"),
        ("binary_sensor.dump_v_float_t2", "off"),
        ("binary_sensor.dump_batt_t2_ok", "off"),
        ("binary_sensor.dump_charge_float", "off"),
        ("binary_sensor.dump_solar_present", "off"),
        ("binary_sensor.dump_soc_ok", "unavailable"),
        ("sensor.battery_1_power", "-2500"),  # pack already supplying > AC cap
    ):
        assert _next(_ok_states(**base, **{key: value})) == "none", key
    # A problem on another bus does not block this one.
    assert _next(_ok_states(**base, **{"binary_sensor.dump_v_rebulk_ku": "on"})) != "none"


def test_shed_plug_only_sheds_dump_sockets_last_first() -> None:
    st = _ok_states(**{
        "switch.ihoment_h5082_cf79_right": "on",  # normal load, must stay
        "switch.ihoment_h5082_2f9d_left": "on",
        "input_select.h5082_2f9d_left_use": "dump",
        "switch.ihoment_h5082_9607_left": "on",
        "input_select.h5082_9607_left_use": "dump",
    })
    assert _shed(st) == "switch.ihoment_h5082_9607_left"
    st["switch.ihoment_h5082_9607_left"] = "off"
    assert _shed(st) == "switch.ihoment_h5082_2f9d_left"
    st["switch.ihoment_h5082_2f9d_left"] = "off"
    assert _shed(st) == "none"


def _targets(aid: str, states) -> list[str]:
    auto = _automations()[aid]
    tpl = auto["actions"][0]["variables"]["targets"]
    return yaml.safe_load(_render(tpl, states).replace("'", '"'))


def test_bus_turn_off_hits_only_dump_sockets_on_that_bus() -> None:
    st = _ok_states(**{
        "input_select.h5082_2f9d_left_use": "dump",
        "input_select.h5082_2f9d_left_inverter": "T2",
        "switch.ihoment_h5082_2f9d_left": "on",
        "input_select.h5082_3013_left_use": "dump",
        "input_select.h5082_3013_left_inverter": "T2",
        "switch.ihoment_h5082_3013_left": "unavailable",  # still sent off
        "input_select.h5082_3ec9_left_use": "dump",
        "input_select.h5082_3ec9_left_inverter": "KU",
        "switch.ihoment_h5082_3ec9_left": "on",
        "input_select.h5082_cf79_left_inverter": "T2",  # normal, on: untouched
        "switch.ihoment_h5082_cf79_left": "on",
    })
    for aid in ("dump_turn_off_rebulk_t2", "dump_turn_off_batt_t2"):
        assert _targets(aid, st) == ["2f9d_left", "3013_left"]
    for aid in ("dump_turn_off_rebulk_ku", "dump_turn_off_batt_ku"):
        assert _targets(aid, st) == ["3ec9_left"]
    for aid in ("dump_turn_off_rebulk_sph", "dump_turn_off_batt_sph"):
        assert _targets(aid, st) == []
    assert _targets("dump_turn_off_solar_gone", st) == ["2f9d_left", "3013_left", "3ec9_left"]
