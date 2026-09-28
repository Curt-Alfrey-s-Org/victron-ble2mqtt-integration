"""Dump-load control on the real H5082 sockets (config/packages/dump_control.yaml).

Structure checks always run. Template behaviour is rendered with jinja2 and a fake
HA state table when jinja2 is installed (HA's own template engine is Jinja2).
"""

from __future__ import annotations

import ast
import datetime as dt
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from govee_h5082.mqtt_bridge import PLUGS, SIDES

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "config" / "packages" / "dump_control.yaml"
DOCS = ROOT / "docs" / "DUMP_LOAD_HA_CONTROL.md"
DASHBOARD = ROOT / "config" / "dashboards" / "solar-plant.yaml"
INSTALL = ROOT / "scripts" / "install_dump_control_ha.sh"

# Stage order = plug id order (same as the Site solar cards and the label script).
# Every bridge plug is a dump candidate (C38D paired 2026-09-28): 8 plugs, 16 sockets.
# (Nothing here says what is plugged into a socket: that is the HA Load text.)
SOCKS = [
    f"{plug}_{side}"
    for plug in sorted(name[-4:].lower() for _address, name in PLUGS)
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
    assert len(SOCKS) == 16
    assert "'c38d_left', 'c38d_right'" in text.split("# Victron float hold")[1]


def test_helpers_per_socket() -> None:
    data = _load()
    for s in SOCKS:
        sel = data["input_select"][f"h5082_{s}_inverter"]
        # Sungold stays first (first-install default); House = grid-powered house plug.
        assert sel["options"] == ["Sungold", "T2", "KU", "House"]
        assert "initial" not in sel  # bus choice must survive HA restarts
        assert data["timer"][f"h5082_{s}_min_on"]["duration"] == "00:15:00"
        assert data["timer"][f"h5082_{s}_cooldown"]["duration"] == "00:10:00"
        assert data["timer"][f"h5082_{s}_cooldown"]["restore"] is True
    # The per-socket use select is the UI helper from create_h5082_socket_labels.py;
    # defining it here too would collide with it.
    assert not any(k.endswith("_use") for k in data["input_select"])
    assert "dump_control_enabled" in data["input_boolean"]
    assert "initial" not in data["input_boolean"]["dump_control_enabled"]
    # 2026-09-28: no `initial:` anywhere, so tuned values survive HA restarts
    # (tests/test_site_solar_persist_and_help.py covers every helper).
    assert "initial" not in data["input_number"]["dump_site_confirm_s"]
    assert data["input_number"]["dump_site_confirm_s"]["min"] == 5


USE_DUMP = re.compile(r"is_state\('input_select\.h5082_' ~ (\w+) ~ '_use', 'dump'\)")


def test_every_dump_pick_has_the_house_guard() -> None:
    """One guard everywhere: Use is dump AND Inverter is not House."""
    text = PACKAGE.read_text(encoding="utf-8")
    hits = list(USE_DUMP.finditer(text))
    # dump_sockets (count + list), next, shed, turn_on recheck, solar gone, 3 re-bulk,
    # 3 batt, and the two manual-hold rules (hold start, hold end).
    assert len(hits) == 14
    for m in hits:
        guard = f" and not is_state('input_select.h5082_' ~ {m.group(1)} ~ '_inverter', 'House'))"
        assert text[m.start() - 1] == "(", text[m.start() - 40 : m.end()]
        assert text[m.end() : m.end() + len(guard)] == guard, text[m.start() : m.end() + 80]


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
        "dump_hold_start",
        "dump_hold_end",
    }
    for aid, auto in autos.items():
        if aid.startswith("dump_hold_"):
            continue  # state triggers on the switches / hold timers; checked below
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
jinja2_sandbox = pytest.importorskip("jinja2.sandbox")


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


def test_house_sockets_are_never_picked_or_switched() -> None:
    """Inverter = House (grid-powered house plug): dump control never switches it."""
    house = {
        "input_select.h5082_2f9d_left_use": "dump",
        "input_select.h5082_2f9d_left_inverter": "House",
    }
    tpl = _templates()
    # Off: never offered to turn on.
    st = _ok_states(**house)
    assert _next(st) == "none"
    assert _render(tpl["dump_sockets"]["state"], st) == "0"
    assert yaml.safe_load(_render(tpl["dump_sockets"]["attributes"]["entities"], st)) == []
    # The next real dump socket is still picked.
    st["input_select.h5082_3013_left_use"] = "dump"
    assert _next(st) == "switch.ihoment_h5082_3013_left"
    # On: never shed and never in any turn-off list (solar gone, re-bulk, battery).
    st = _ok_states(**house, **{"switch.ihoment_h5082_2f9d_left": "on"})
    assert _shed(st) == "none"
    offs = [a for a in _automations() if a.startswith("dump_turn_off_") and a != "dump_turn_off_bulk"]
    assert len(offs) == 7
    for aid in offs:
        assert "2f9d_left" not in _targets(aid, st), aid
    # dump_turn_on rechecks the socket right before switch.turn_on.
    seq = _automations()["dump_turn_on"]["actions"][0]["repeat"]["sequence"]
    recheck = [n for n in seq if n.get("condition") == "template"]
    assert len(recheck) == 1
    env_st = dict(st)
    tmpl = recheck[0]["value_template"].replace("sock", "'2f9d_left'")
    assert _render(tmpl, env_st) == "False"
    env_st["input_select.h5082_2f9d_left_inverter"] = "KU"
    assert _render(tmpl, env_st) == "True"
    # Dashboard "Dump sockets by name" says so instead of naming a bus.
    assert "House (grid power): never switched by dump control" in DASHBOARD.read_text(encoding="utf-8")


# ---------------------------------------------------------------- manual hold

HOLD_ON = " and states('timer.h5082_' ~ {v} ~ '_hold') not in ['active', 'paused']"
HOLD_OFF = (
    " and (states('timer.h5082_' ~ {v} ~ '_hold') not in ['active', 'paused']"
    " or not is_state('input_boolean.dump_hold_blocks_turn_off', 'on'))"
)
TURN_OFF_LISTS = (
    "dump_turn_off_solar_gone",
    "dump_turn_off_rebulk_t2",
    "dump_turn_off_rebulk_ku",
    "dump_turn_off_rebulk_sph",
    "dump_turn_off_batt_t2",
    "dump_turn_off_batt_ku",
    "dump_turn_off_batt_sph",
)


def _strings(node) -> str:
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        return "\n".join(_strings(v) for v in node.values())
    if isinstance(node, list):
        return "\n".join(_strings(v) for v in node)
    return ""


def _lists(node):
    if isinstance(node, list):
        yield node
        for v in node:
            yield from _lists(v)
    elif isinstance(node, dict):
        for v in node.values():
            yield from _lists(v)


def test_manual_hold_helpers() -> None:
    data = _load()
    hold_ids = []
    for s in SOCKS:
        tm = data["timer"][f"h5082_{s}_hold"]
        assert tm["restore"] is True
        assert tm["name"] == f"{s[:4].upper()} {s[5:]} dump manual hold"
        hold_ids.append(f"timer.h5082_{s}_hold")
    num = data["input_number"]["dump_manual_hold_min"]
    assert (num["min"], num["max"], num["unit_of_measurement"]) == (0, 720, "min")
    assert "initial" not in num  # a new helper starts at 0 = hold off
    assert "initial" not in data["input_boolean"]["dump_hold_blocks_turn_off"]
    clear = data["script"]["dump_clear_holds"]["sequence"][0]
    assert clear["action"] == "timer.cancel"
    assert clear["target"]["entity_id"] == hold_ids
    defaults = _strings(data["script"]["dump_load_recommended_defaults"])
    assert "input_number.dump_manual_hold_min" in defaults
    assert "input_boolean.dump_hold_blocks_turn_off" in defaults
    autos = _automations()
    start = autos["dump_hold_start"]["triggers"][0]
    assert start["entity_id"] == [f"switch.ihoment_h5082_{s}" for s in SOCKS]
    assert (start["from"], start["to"]) == (["on", "off"], ["on", "off"])
    end = autos["dump_hold_end"]["triggers"][0]
    assert end["entity_id"] == hold_ids
    assert (end["from"], end["to"]) == ("active", "idle")


def test_every_dump_path_has_the_hold_guard() -> None:
    """Turn-on always skips a held socket; turn-offs skip it only when the toggle is on."""
    text = PACKAGE.read_text(encoding="utf-8")
    tpl = _templates()
    autos = _automations()
    assert HOLD_ON.format(v="s") in tpl["dump_next_plug"]["state"]
    assert HOLD_ON.format(v="sock") in _strings(autos["dump_turn_on"]["actions"])
    assert HOLD_OFF.format(v="s") in tpl["dump_shed_plug"]["state"]
    for aid in TURN_OFF_LISTS:
        assert HOLD_OFF.format(v="s") in autos[aid]["actions"][0]["variables"]["targets"], aid
    # Exactly those 10 places (the 2 shed rules use dump_shed_plug).
    assert text.count(HOLD_ON.format(v="s")) + text.count(HOLD_ON.format(v="sock")) == 2
    assert text.count(HOLD_OFF.format(v="s")) == 8
    # "Sockets set to dump" still counts held sockets and lists them in `held`.
    assert "_hold'" not in tpl["dump_sockets"]["state"]
    assert "_hold')" in tpl["dump_sockets"]["attributes"]["held"]


def test_held_socket_is_never_turned_on() -> None:
    st = _ok_states(**{
        "input_select.h5082_2f9d_left_use": "dump",
        "input_select.h5082_3013_left_use": "dump",
        "timer.h5082_2f9d_left_hold": "active",
    })
    assert _next(st) == "switch.ihoment_h5082_3013_left"
    st["timer.h5082_3013_left_hold"] = "paused"
    assert _next(st) == "none"
    st["timer.h5082_2f9d_left_hold"] = "idle"
    assert _next(st) == "switch.ihoment_h5082_2f9d_left"
    # dump_turn_on rechecks right before switch.turn_on, whatever the toggle says.
    seq = _automations()["dump_turn_on"]["actions"][0]["repeat"]["sequence"]
    recheck = next(n for n in seq if n.get("condition") == "template")["value_template"]
    tmpl = recheck.replace("sock", "'2f9d_left'")
    assert _render(tmpl, st) == "True"
    st["timer.h5082_2f9d_left_hold"] = "active"
    assert _render(tmpl, st) == "False"
    st["input_boolean.dump_hold_blocks_turn_off"] = "off"
    assert _render(tmpl, st) == "False"


def test_hold_blocks_turn_offs_only_when_the_toggle_is_on() -> None:
    st = _ok_states(**{
        "input_select.h5082_2f9d_left_use": "dump",
        "input_select.h5082_2f9d_left_inverter": "T2",
        "switch.ihoment_h5082_2f9d_left": "on",
        "timer.h5082_2f9d_left_hold": "active",
        "input_select.h5082_3013_left_use": "dump",
        "input_select.h5082_3013_left_inverter": "T2",
        "switch.ihoment_h5082_3013_left": "on",
    })
    # Toggle off (or a brand-new helper): the turn-off rules still act on a held socket.
    for aid in ("dump_turn_off_solar_gone", "dump_turn_off_rebulk_t2", "dump_turn_off_batt_t2"):
        assert _targets(aid, st) == ["2f9d_left", "3013_left"], aid
    st["switch.ihoment_h5082_3013_left"] = "off"
    assert _shed(st) == "switch.ihoment_h5082_2f9d_left"
    # Toggle on: the held socket is left alone by every turn-off rule and the sheds.
    st["input_boolean.dump_hold_blocks_turn_off"] = "on"
    st["switch.ihoment_h5082_3013_left"] = "on"
    for aid in TURN_OFF_LISTS:
        assert "2f9d_left" not in _targets(aid, st), aid
    assert _targets("dump_turn_off_rebulk_t2", st) == ["3013_left"]
    assert _shed(st) == "switch.ihoment_h5082_3013_left"
    st["switch.ihoment_h5082_3013_left"] = "off"
    assert _shed(st) == "none"
    st["timer.h5082_2f9d_left_hold"] = "idle"  # hold over: back to normal
    assert _shed(st) == "switch.ihoment_h5082_2f9d_left"


def test_every_dump_switch_action_is_announced_first() -> None:
    found = 0
    for auto in _automations().values():
        for seq in _lists(auto["actions"]):
            for i, node in enumerate(seq):
                if not isinstance(node, dict) or node.get("action") not in ("switch.turn_on", "switch.turn_off"):
                    continue
                found += 1
                prev = seq[i - 1]
                assert i > 0 and prev.get("event") == "dump_control_switching", auto["id"]
                assert prev["event_data"]["state"] == node["action"].split("_")[-1], auto["id"]
                want = "{{ repeat.item }}" if "repeat.item" in node["target"]["entity_id"] else "{{ sock }}"
                assert prev["event_data"]["sock"] == want, auto["id"]
    assert found == 13  # turn on + 2 unconfirmed offs, 2 sheds, 7 turn-off lists, hold end


def _render_ha(template: str, states: dict[str, str] | None = None, **extra) -> str:
    """Closer to HA: sandboxed, with now / as_timestamp / state_attr / timedelta."""
    states = states or {}

    def as_timestamp(value, default=None):
        if isinstance(value, dt.datetime):
            return value.timestamp()
        try:
            return dt.datetime.fromisoformat(str(value)).timestamp()
        except (TypeError, ValueError):
            return default

    env = jinja2_sandbox.ImmutableSandboxedEnvironment()
    env.globals.update(
        states=lambda eid: states.get(eid, "unknown"),
        is_state=lambda eid, value: states.get(eid, "unknown") == value,
        is_number=_is_number,
        now=extra.pop("now", lambda: dt.datetime.now(dt.timezone.utc)),
        as_timestamp=as_timestamp,
        timedelta=dt.timedelta,
        state_attr=extra.pop("state_attr", lambda eid, attr: None),
    )
    return env.from_string(template).render(**extra).strip()


def test_intent_sensor_keeps_one_request_per_socket() -> None:
    block = next(b for b in _load()["template"] if "triggers" in b)
    assert block["triggers"] == [{"trigger": "event", "event_type": "dump_control_switching"}]
    tpl = block["sensor"][0]["attributes"]["intents"]

    def fire(this, sock, state):
        trig = {"event": {"data": {"sock": sock, "state": state}}}
        extra = {"trigger": trig}
        if this is not None:
            extra["this"] = SimpleNamespace(attributes=this)
        return ast.literal_eval(_render_ha(tpl, **extra))

    one = fire(None, "2f9d_left", "on")
    assert list(one) == ["2f9d_left"] and one["2f9d_left"][0] == "on"
    two = fire({"intents": one}, "3013_left", "off")
    assert set(two) == {"2f9d_left", "3013_left"}
    three = fire({"intents": two}, "2f9d_left", "done")
    assert three["2f9d_left"][0] == "done" and three["3013_left"][0] == "off"
    fresh = fire({}, "c38d_right", "off")  # restored without intents: starts clean
    assert list(fresh) == ["c38d_right"] and fresh["c38d_right"][0] == "off"
    assert isinstance(fresh["c38d_right"][1], float)


def test_hold_start_tells_dump_control_from_a_hand_switch() -> None:
    auto = _automations()["dump_hold_start"]
    tpl = auto["variables"]["by_dump"]
    now = dt.datetime.now(dt.timezone.utc)

    def by_dump(intents, to_state):
        return _render_ha(
            tpl,
            now=lambda: now,
            state_attr=lambda e, a: intents if (e, a) == ("sensor.dump_control_switching", "intents") else None,
            sock="2f9d_left",
            trigger={"to_state": {"state": to_state}},
        )

    ts = now.timestamp()
    assert by_dump({"2f9d_left": ["on", ts - 20]}, "on") == "True"  # dump control asked
    assert by_dump({"2f9d_left": ["on", ts - 20]}, "off") == "False"  # opposite: by hand
    assert by_dump({"2f9d_left": ["on", ts - 200]}, "on") == "False"  # stale request
    assert by_dump({"2f9d_left": ["done", ts - 5]}, "on") == "False"  # already used up
    assert by_dump({"3013_left": ["on", ts - 5]}, "on") == "False"  # other socket
    assert by_dump(None, "on") == "False"  # registry empty / unknown
    # A hand switch starts the hold only on a dump socket (not House) with minutes > 0.
    cond = next(a for a in auto["actions"] if a.get("condition") == "template")["value_template"]
    assert "'_inverter', 'House'" in cond and "hold_min > 0" in cond
    start = next(a for a in auto["actions"] if a.get("action") == "timer.start")
    assert start["target"]["entity_id"] == "timer.h5082_{{ sock }}_hold"
    for minutes, want in ((5, "00:05:00"), (60, "01:00:00"), (720, "12:00:00")):
        assert _render_ha(start["data"]["duration"], hold_min=minutes) == want
    # Runs even with the master switch off: no master-switch condition.
    assert "dump_control_enabled" not in _strings(auto)


def test_hold_end_turns_off_only_what_dump_control_would_want_off() -> None:
    auto = _automations()["dump_hold_end"]
    why = auto["variables"]["why_off"]
    ok = _ok_states(**{"binary_sensor.dump_charge_ok": "on", "binary_sensor.dump_load_exceeds_solar": "off"})
    assert _render_ha(why, ok, bus="T2") == ""
    assert _render_ha(why, {**ok, "binary_sensor.dump_solar_present": "off"}, bus="T2") == "solar gone"
    assert _render_ha(why, {**ok, "binary_sensor.dump_v_rebulk_t2": "on"}, bus="T2") == "T2 bus at stop volts"
    assert _render_ha(why, {**ok, "binary_sensor.dump_v_rebulk_t2": "on"}, bus="KU") == ""
    assert _render_ha(why, {**ok, "binary_sensor.dump_batt_sph_ok": "off"}, bus="Sungold") == (
        "Sungold battery past its discharge limit"
    )
    assert _render_ha(why, {**ok, "binary_sensor.dump_charge_ok": "off"}, bus="KU") == (
        "T2 charger left absorption/float"
    )
    blob = _strings(auto["actions"])
    assert "input_boolean.dump_control_enabled" in blob
    assert "'_inverter', 'House'" in blob
