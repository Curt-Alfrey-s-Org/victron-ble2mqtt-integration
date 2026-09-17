"""Tests for scripts/solar_flow_server.py (demo snapshot + dump-load view)."""

from __future__ import annotations

import json
import sys
import threading
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import solar_flow_server as sfs  # noqa: E402


def _clear_ha_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force demo path even if a gitignored token file exists on disk."""
    monkeypatch.delenv("HA_TOKEN", raising=False)
    monkeypatch.delenv("HA_TOKEN_FILE", raising=False)
    monkeypatch.delenv("HA_LONG_LIVED_TOKEN_FILE", raising=False)
    monkeypatch.setattr(sfs, "default_ha_token_paths", lambda: [])


def _demo_states(
    *,
    solar: str = "400",
    load: str = "280",
    soc: str = "92",
    charge: str = "absorption",
    plug_1: str = "on",
) -> dict[str, dict]:
    return {
        "sensor.solar_controller_solar_power": {"entity_id": "sensor.solar_controller_solar_power", "state": solar},
        "sensor.sim_dump_load_power": {
            "entity_id": "sensor.sim_dump_load_power",
            "state": load,
        },
        "sensor.em16_a3_power": {"entity_id": "sensor.em16_a3_power", "state": "100"},
        "sensor.battery_1_soc": {"entity_id": "sensor.battery_1_soc", "state": soc},
        "sensor.battery_1_voltage": {"entity_id": "sensor.battery_1_voltage", "state": "28.6"},
        "sensor.battery_1_current": {"entity_id": "sensor.battery_1_current", "state": "2.1"},
        "sensor.battery_2_voltage": {"entity_id": "sensor.battery_2_voltage", "state": "25.6"},
        "sensor.battery_2_current": {"entity_id": "sensor.battery_2_current", "state": "-4.8"},
        "sensor.solar_controller_battery_state": {
            "entity_id": "sensor.solar_controller_battery_state",
            "state": charge,
        },
        "switch.sim_ac_plug_1": {"entity_id": "switch.sim_ac_plug_1", "state": plug_1},
        "switch.sim_ac_plug_2": {"entity_id": "switch.sim_ac_plug_2", "state": "off"},
        "switch.sim_ac_plug_3": {"entity_id": "switch.sim_ac_plug_3", "state": "off"},
        "switch.sim_ac_plug_4": {"entity_id": "switch.sim_ac_plug_4", "state": "off"},
        "switch.sim_ac_plug_5": {"entity_id": "switch.sim_ac_plug_5", "state": "off"},
        "switch.sim_ac_plug_6": {"entity_id": "switch.sim_ac_plug_6", "state": "off"},
    }


def test_build_snapshot_demo_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_ha_token(monkeypatch)
    snap = sfs.build_snapshot(now=1000.0)
    assert snap["mode"] == "demo"
    assert snap.get("sim_dump_demo") is True
    assert "sensor.solar_controller_solar_power" not in snap["entities"]
    assert snap["entities"]["switch.sim_ac_plug_1"]["state"] == "on"
    assert snap["ai"]["meta"]["solar_w"] is None
    assert all(d["action"] == "skip" for d in snap["ai"]["decisions"])


def test_decide_dump_view_surplus_math() -> None:
    view = sfs.decide_dump_view(states=_demo_states(), now=1000.0)
    meta = view["meta"]
    assert meta["effective_load_w"] == 280.0
    assert meta["sim_plug_w"] == 180
    assert meta["surplus_w"] == 120.0
    assert "Surplus 120W" in view["thinking"]
    assert "soak" not in view["thinking"].lower()
    assert len(view["decisions"]) == 6
    assert view["watt_hops"]
    assert "vent_fan" in {h["id"] for h in view["watt_hops"]}
    assert "pi4" in {h["id"] for h in view["watt_hops"]}
    assert "ku_renogy_ac" in {h["id"] for h in view["watt_hops"]}
    assert view["ku_renogy_ac_est_w"] == 100.0
    assert "Battery 2 load 100W" in view["thinking"]


def test_weather_strip_clear_of_dump_banner_and_plug1() -> None:
    """SVG text y is the alphabetic baseline (SVG 1.1 TextElement)."""
    html = (ROOT / "web" / "solar-flow" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "web" / "solar-flow" / "styles.css").read_text(encoding="utf-8")
    weather_y = 12
    weather_h = 88
    weather_bottom = weather_y + weather_h
    banner_baseline = 128
    banner_font_px = 15
    assert 'class="wx-sky-bg" x="1148" y="12" width="380" height="88"' in html
    assert 'class="sim-dump-banner" x="1338" y="128"' in html
    assert "font-size: 15px" in css
    assert banner_baseline - banner_font_px >= weather_bottom
    plug1 = html.split('id="node-plug-1"', 1)[1]
    assert 'x="1176" y="140" width="340" height="76"' in plug1[:800]
    plug1_top = 140
    assert plug1_top >= banner_baseline


def test_ku_suitcase_panel_spacing_matches_t2() -> None:
    """T2 panel brick 150x100 at x=40; KU rows use 16px gutters and T2's 190-254 hop."""
    html = (ROOT / "web" / "solar-flow" / "index.html").read_text(encoding="utf-8")
    assert 'id="node-t2-panels"' in html
    assert 'x="40" y="76" width="150" height="100"' in html
    p1 = html.split('id="node-ku-panel-mppt1"', 1)[1]
    p2 = html.split('id="node-ku-panel-mppt2"', 1)[1]
    p3 = html.split('id="node-ku-panel-pwm"', 1)[1]
    assert 'x="40" y="332" width="150" height="100"' in p1[:400]
    assert 'x="40" y="448" width="150" height="100"' in p2[:400]
    assert 'x="40" y="564" width="150" height="100"' in p3[:400]
    assert 448 - (332 + 100) == 16
    assert 564 - (448 + 100) == 16
    assert 'd="M 190 126 L 254 126"' in html
    assert 'd="M 190 382 L 254 382"' in html
    assert 'class="lane-band lane-ku-dc" x="16" y="304" width="1116" height="400"' in html


def test_solar_flow_web_copy_has_no_soak_or_dash_watts() -> None:
    html = (ROOT / "web" / "solar-flow" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "web" / "solar-flow" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "web" / "solar-flow" / "styles.css").read_text(encoding="utf-8")
    blob = "\n".join((html, js, css))
    assert "soak" not in blob.lower()
    assert "-- W" not in blob
    assert "A/C" in html
    assert "D/C" in html
    assert "dump load" in html.lower()
    assert 'viewBox="0 0 1560 1420"' in html
    assert 'path-t2-ku-jumper' in html
    assert 'id="node-vent-fan"' in html
    assert 'id="node-pi4"' in html
    assert 'id="val-batt2-load"' in html
    assert 'id="val-ku-renogy-note"' in html
    assert "opts.kuRenogyAcW" in js
    assert "setHopLabel('path-ku-batt2-inverter', opts.batt2W" not in js
    assert 'id="art-pv"' in html
    assert 'id="path-outlet-vent-fan"' in html
    assert 'id="path-b3-outlet"' in html
    assert 'id="path-outlet-uti"' in html
    assert 'id="hop-path-b3-outlet"' in html
    assert 'id="hop-path-outlet-uti"' in html
    assert 'id="node-sg-uti"' in html
    assert 'path-b3-outlet-sg-uti' not in html
    assert 'id="path-sg-acout-pi4"' in html
    assert "watt-pos" in css
    assert "watt-neg" in css
    assert "watt-zero" in css
    assert "function wattSignClass" in js
    assert "function applyLoadSign" in js
    assert "function setWattValue" in js
    assert "function formatSignedW" in js
    assert "function kuUnmeteredPvEstW" in js
    assert "function kuEqualShareW" in js
    assert "function utiHopW" in js
    assert "function ventFanEstimateW" in js
    assert "trailerW - utiW" in js
    assert 'x="300" y="1088"' in html
    assert 'id="node-plug-1"' in html
    assert 'x="1176" y="140" width="340" height="76"' in html
    assert "function b3OutletHopW" in js
    assert "return batt2W - jumperW + kuRenogyAcW" in js
    assert "function setHopLabel" in js
    assert "{ label: 'T2 shunt V'" in js
    assert "{ label: 'T2 shunt A'" in js
    assert "{ label: 'KU shunt V'" in js
    assert "{ label: 'KU shunt A'" in js
    assert "{ label: 'Shunt V'" not in js
    assert "{ label: 'Shunt A'" not in js
    assert 'id="node-ku-mppt-1"' in html
    assert 'id="node-ku-mppt-2"' in html
    assert 'id="node-ku-pwm"' in html
    assert 'id="val-ku-mppt-1-w"' in html
    assert 'id="val-ku-pwm-w"' in html
    assert ">est.<" in html
    assert "w > 0 ? '+' : w < 0 ? '-' : ''" not in js
    assert "val > 0 ? '+' : ''" not in js
    assert "setWattValue('val-ku-victron-panels-w', 0)" not in js
    assert "setWattValue('val-ku-pwm-panels-w', 0)" not in js


def test_public_missing_entity_ids_omits_legacy_unique_id() -> None:
    assert sfs.public_missing_entity_ids(
        ["sensor.em16_a3_power", "sensor.sim_soak_load_power"]
    ) == ["sensor.em16_a3_power"]


def test_decide_dump_view_turns_on_above_threshold() -> None:
    states = _demo_states(solar="800", load="100", plug_1="off")
    view = sfs.decide_dump_view(states=states, now=1000.0)
    assert view["meta"]["surplus_w"] == 700.0
    on_actions = [d for d in view["decisions"] if d["action"] == "on"]
    assert on_actions


def test_filter_entities_only_required() -> None:
    rows = [
        {"entity_id": "sensor.solar_controller_solar_power", "state": "400", "attributes": {}},
        {"entity_id": "light.kitchen", "state": "on", "attributes": {}},
        {"entity_id": "switch.sim_ac_plug_1", "state": "off", "attributes": {}},
    ]
    filtered = sfs.filter_entities(rows)
    assert filtered["sensor.solar_controller_solar_power"]["state"] == "400"
    assert filtered["sensor.solar_controller_solar"]["state"] == "400"
    assert filtered["sensor.solar_controller_solar"]["source_entity_id"] == (
        "sensor.solar_controller_solar_power"
    )
    assert "switch.sim_ac_plug_1" in filtered
    assert "light.kitchen" not in filtered


def test_filter_aliases_lovelace_solar_and_soc() -> None:
    rows = [
        {
            "entity_id": "sensor.solar_controller_solar",
            "state": "312",
            "attributes": {"unit_of_measurement": "W"},
            "last_updated": "2026-09-16T14:00:00+00:00",
        },
        {
            "entity_id": "sensor.battery_1_state_of_charge",
            "state": "91",
            "attributes": {"unit_of_measurement": "%"},
        },
        {"entity_id": "light.kitchen", "state": "on", "attributes": {}},
    ]
    filtered = sfs.filter_entities(rows)
    assert filtered["sensor.solar_controller_solar"]["state"] == "312"
    assert filtered["sensor.solar_controller_solar_power"]["state"] == "312"
    assert filtered["sensor.solar_controller_solar_power"]["source_entity_id"] == (
        "sensor.solar_controller_solar"
    )
    assert filtered["sensor.solar_controller_solar_power"]["last_updated"] == (
        "2026-09-16T14:00:00+00:00"
    )
    assert filtered["sensor.battery_1_soc"]["state"] == "91"
    assert "light.kitchen" not in filtered


def test_filter_prefers_live_over_canonical() -> None:
    rows = [
        {"entity_id": "sensor.solar_controller_solar_power", "state": "400", "attributes": {}},
        {"entity_id": "sensor.solar_controller_solar", "state": "302", "attributes": {}},
        {"entity_id": "sensor.sungold_sph302480a_load_power", "state": "10", "attributes": {}},
        {
            "entity_id": "sensor.sungold_sph302480a_load_active_power",
            "state": "441",
            "attributes": {},
        },
    ]
    filtered = sfs.filter_entities(rows)
    assert filtered["sensor.solar_controller_solar"]["state"] == "302"
    assert filtered["sensor.solar_controller_solar_power"]["state"] == "302"
    assert filtered["sensor.solar_controller_solar_power"]["source_entity_id"] == (
        "sensor.solar_controller_solar"
    )
    assert filtered["sensor.sungold_sph302480a_load_active_power"]["state"] == "441"
    assert filtered["sensor.sungold_sph302480a_load_power"]["state"] == "441"
    assert filtered["sensor.sungold_sph302480a_load_power"]["source_entity_id"] == (
        "sensor.sungold_sph302480a_load_active_power"
    )


def test_filter_live_registry_ids_populate_gx_and_dump() -> None:
    """HA .105 registry ids (Lovelace Solar ~13:09 ET 16 Sep 2026), not dump canonicals."""
    rows = [
        {"entity_id": "sensor.solar_controller_solar", "state": "302.0", "attributes": {}},
        {"entity_id": "sensor.solar_controller_charge_state", "state": "bulk", "attributes": {}},
        {"entity_id": "sensor.solar_controller_battery", "state": "26.3", "attributes": {}},
        {
            "entity_id": "sensor.solar_controller_battery_charging",
            "state": "10.9",
            "attributes": {},
        },
        {"entity_id": "sensor.solar_controller_load", "state": "0.0", "attributes": {}},
        {"entity_id": "sensor.solar_controller_yield_today", "state": "780", "attributes": {}},
        {"entity_id": "sensor.battery_1_state_of_charge", "state": "100", "attributes": {}},
        {"entity_id": "sensor.battery_1_voltage", "state": "26.4", "attributes": {}},
        {"entity_id": "sensor.battery_1_current", "state": "8.6", "attributes": {}},
        {"entity_id": "sensor.battery_1_power", "state": "227.9", "attributes": {}},
        {"entity_id": "sensor.battery_2_state_of_charge", "state": "92.5", "attributes": {}},
        {"entity_id": "sensor.battery_2_voltage", "state": "26.3", "attributes": {}},
        {"entity_id": "sensor.battery_2_current", "state": "5.1", "attributes": {}},
        {"entity_id": "sensor.battery_2_power", "state": "133.3", "attributes": {}},
        {
            "entity_id": "sensor.sungold_sph302480a_load_active_power",
            "state": "441",
            "attributes": {},
        },
        {"entity_id": "sensor.sungold_sph302480a_battery_soc", "state": "55", "attributes": {}},
        {"entity_id": "sensor.sungold_sph302480a_battery_voltage", "state": "26.6", "attributes": {}},
        {
            "entity_id": "sensor.sungold_sph302480a_battery_current",
            "state": "-0.1",
            "attributes": {},
        },
        {"entity_id": "sensor.sungold_sph302480a_charging_power", "state": "0", "attributes": {}},
        {
            "entity_id": "sensor.sungold_sph302480a_charge_state",
            "state": "Constant voltage",
            "attributes": {},
        },
        {"entity_id": "sensor.sungold_sph302480a_grid_voltage", "state": "117", "attributes": {}},
        {"entity_id": "sensor.sungold_sph302480a_grid_current", "state": "3.70", "attributes": {}},
        {"entity_id": "sensor.sungold_sph302480a_pv_power", "state": "0", "attributes": {}},
    ]
    filtered = sfs.filter_entities(rows)
    assert filtered["sensor.solar_controller_solar"]["state"] == "302.0"
    assert filtered["sensor.solar_controller_solar_power"]["state"] == "302.0"
    assert filtered["sensor.solar_controller_charge_state"]["state"] == "bulk"
    assert filtered["sensor.solar_controller_battery_state"]["state"] == "bulk"
    assert filtered["sensor.battery_1_soc"]["state"] == "100"
    assert filtered["sensor.battery_1_voltage"]["state"] == "26.4"
    assert filtered["sensor.battery_1_current"]["state"] == "8.6"
    assert filtered["sensor.battery_1_power"]["state"] == "227.9"
    assert filtered["sensor.battery_2_soc"]["state"] == "92.5"
    assert filtered["sensor.battery_2_power"]["state"] == "133.3"
    assert filtered["sensor.sungold_sph302480a_load_active_power"]["state"] == "441"
    assert filtered["sensor.sungold_sph302480a_load_power"]["state"] == "441"
    assert filtered["sensor.sungold_sph302480a_battery_soc"]["state"] == "55"
    missing = [eid for eid in sfs.REQUIRED_ENTITY_IDS if eid not in filtered]
    assert "sensor.solar_controller_solar_power" not in missing
    assert "sensor.solar_controller_battery_state" not in missing
    assert "sensor.battery_1_soc" not in missing
    assert "sensor.sungold_sph302480a_load_power" not in missing


def test_http_snapshot_cache_control(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_ha_token(monkeypatch)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sfs.SolarFlowHandler)
    _host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/snapshot", timeout=5) as resp:
            assert resp.headers.get("Cache-Control") == "no-store"
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["mode"] == "demo"
        assert payload.get("fetched_at")
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_redact_secrets_strips_token() -> None:
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secret"
    raw = f"HTTP Error 401: Unauthorized Bearer {token}"
    safe = sfs.redact_secrets(raw, token)
    assert token not in safe
    assert "Bearer [REDACTED]" in safe or "[REDACTED]" in safe


def test_fetch_error_message_has_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token = "super-secret-ha-token-value"
    monkeypatch.setenv("HA_TOKEN", token)

    def _boom(_base: str, _tok: str) -> list[dict]:
        raise urllib.error.HTTPError(
            "http://192.168.0.105:8123/api/states",
            401,
            f"Unauthorized Bearer {token}",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(sfs, "fetch_ha_states", _boom)
    with pytest.raises(urllib.error.HTTPError) as exc:
        sfs.build_live_snapshot(token)
    safe = sfs.redact_secrets(str(exc.value), token)
    assert token not in safe


def test_http_demo_snapshot_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_ha_token(monkeypatch)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sfs.SolarFlowHandler)
    _host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/snapshot", timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["mode"] == "demo"
        assert payload.get("sim_dump_demo") is True
        assert "sensor.solar_controller_solar_power" not in payload["entities"]
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_live_handler_error_json_redacts_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token = "abc123secret-token"
    monkeypatch.setenv("HA_TOKEN", token)

    def _fail_live(_token: str, now: float | None = None) -> dict:
        raise ValueError(f"HA rejected Bearer {token}")

    monkeypatch.setattr(sfs, "build_live_snapshot", _fail_live)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sfs.SolarFlowHandler)
    _host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/snapshot", timeout=5)
            pytest.fail("expected HTTP 502")
        except urllib.error.HTTPError as err:
            assert err.code == 502
            body = err.read().decode("utf-8")
            payload = json.loads(body)
        assert token not in body
        assert "error" in payload
        assert token not in payload["error"]
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_resolve_bind_host_default_localhost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOLAR_FLOW_HOST", raising=False)
    args = sfs.parse_args([])
    assert sfs.resolve_bind_host(args) == "127.0.0.1"


def test_resolve_bind_host_lan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOLAR_FLOW_HOST", raising=False)
    args = sfs.parse_args(["--lan"])
    assert sfs.resolve_bind_host(args) == "0.0.0.0"


def test_default_settings_ha_load_entity_is_sim_dump_not_em16_a3() -> None:
    assert sfs.DEFAULT_SETTINGS["ha_load_entity"] == "sensor.sim_dump_load_power"
    assert sfs.DEFAULT_SETTINGS["ha_load_entity"] != "sensor.em16_a3_power"


def test_required_entity_ids_include_battery_2_and_plug_power() -> None:
    assert "sensor.battery_2_soc" in sfs.REQUIRED_ENTITY_IDS
    assert "sensor.battery_2_power" in sfs.REQUIRED_ENTITY_IDS
    assert "sensor.sim_ac_plug_1_power" in sfs.REQUIRED_ENTITY_IDS
    assert "sensor.sim_dump_load_power" in sfs.REQUIRED_ENTITY_IDS
    assert "sensor.sungold_sph302480a_pv_power" in sfs.REQUIRED_ENTITY_IDS
    assert "sensor.sungold_sph302480a_battery_soc" in sfs.REQUIRED_ENTITY_IDS
    assert "sensor.solar_controller_yield_today" in sfs.REQUIRED_ENTITY_IDS


def test_filter_includes_prefix_em16_and_sungold() -> None:
    rows = [
        {"entity_id": "sensor.em16_a2_power", "state": "73", "attributes": {}},
        {"entity_id": "sensor.em16_b2_power", "state": "-100", "attributes": {}},
        {"entity_id": "sensor.sungold_sph302480a_pv_power", "state": "0", "attributes": {}},
        {"entity_id": "light.kitchen", "state": "on", "attributes": {}},
        {
            "entity_id": "input_boolean.sim_ac_plug_1_internal",
            "state": "on",
            "attributes": {},
        },
    ]
    filtered = sfs.filter_entities(rows)
    assert filtered["sensor.em16_a2_power"]["state"] == "73"
    assert filtered["sensor.em16_b2_power"]["state"] == "-100"
    assert filtered["sensor.sungold_sph302480a_pv_power"]["state"] == "0"
    assert "light.kitchen" not in filtered
    assert "input_boolean.sim_ac_plug_1_internal" not in filtered


def test_filter_aliases_sungold_load_active_power() -> None:
    rows = [
        {
            "entity_id": "sensor.sungold_sph302480a_load_active_power",
            "state": "10",
            "attributes": {"unit_of_measurement": "W"},
        }
    ]
    filtered = sfs.filter_entities(rows)
    assert filtered["sensor.sungold_sph302480a_load_active_power"]["state"] == "10"
    assert filtered["sensor.sungold_sph302480a_load_power"]["state"] == "10"
    assert filtered["sensor.sungold_sph302480a_load_power"]["source_entity_id"] == (
        "sensor.sungold_sph302480a_load_active_power"
    )


def test_demo_snapshot_includes_sungold_and_em16_meters() -> None:
    entities = sfs.load_demo_entities()
    assert entities["sensor.sungold_sph302480a_charging_power"]["state"] == "1042"
    assert entities["sensor.em16_b2_power"]["state"] == "-100"
    assert entities["sensor.em16_b3_power"]["state"] == "100"
    assert entities["sensor.em16_a3_power"]["state"] == "100"
    snap = sfs.build_demo_snapshot(now=1000.0)
    assert snap.get("sim_dump_demo") is True
    assert "sensor.sungold_sph302480a_charging_power" not in snap["entities"]
    assert snap["entities"]["sensor.sim_dump_load_power"]["state"] == "280"


def _ha_rows_plug1_off() -> list[dict]:
    return [
        {
            "entity_id": "sensor.solar_controller_solar",
            "state": "302.0",
            "attributes": {"unit_of_measurement": "W"},
        },
        {
            "entity_id": "switch.sim_ac_plug_1",
            "state": "off",
            "attributes": {},
        },
        {
            "entity_id": "sensor.sim_ac_plug_1_power",
            "state": "0",
            "attributes": {"unit_of_measurement": "W"},
        },
    ]


def test_live_snapshot_keeps_ha_sim_plug_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """HA switch.sim_ac_plug_1=off must not be overwritten by demo file ON."""
    monkeypatch.setenv("HA_TOKEN", "unit-test-token")
    monkeypatch.setattr(sfs, "fetch_ha_states", lambda _b, _t: _ha_rows_plug1_off())
    snap = sfs.build_live_snapshot("unit-test-token", now=1000.0)
    assert snap["mode"] == "live"
    assert snap["view"] == "production"
    assert snap["entities"]["sensor.solar_controller_solar"]["state"] == "302.0"
    assert snap["entities"]["switch.sim_ac_plug_1"]["state"] == "off"
    assert snap["entities"]["sensor.sim_ac_plug_1_power"]["state"] == "0"


def test_live_snapshot_fills_missing_sim_dump_from_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HA_TOKEN", "unit-test-token")
    monkeypatch.setattr(sfs, "fetch_ha_states", lambda _b, _t: _ha_rows_plug1_off())
    snap = sfs.build_live_snapshot("unit-test-token", now=1000.0)
    assert snap.get("sim_dump_demo") is True
    assert snap["entities"]["switch.sim_ac_plug_2"]["state"] == "off"
    assert snap["entities"]["sensor.sim_dump_load_power"]["state"] == "280"


def test_live_snapshot_all_sim_dump_present_sim_dump_demo_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = list(_ha_rows_plug1_off())
    for plug in range(1, 7):
        rows.append(
            {
                "entity_id": f"switch.sim_ac_plug_{plug}",
                "state": "off",
                "attributes": {},
            }
        )
        rows.append(
            {
                "entity_id": f"sensor.sim_ac_plug_{plug}_power",
                "state": "0",
                "attributes": {"unit_of_measurement": "W"},
            }
        )
    rows.append(
        {
            "entity_id": "sensor.sim_dump_load_power",
            "state": "0",
            "attributes": {"unit_of_measurement": "W"},
        }
    )
    monkeypatch.setenv("HA_TOKEN", "unit-test-token")
    monkeypatch.setattr(sfs, "fetch_ha_states", lambda _b, _t: rows)
    snap = sfs.build_live_snapshot("unit-test-token", now=1000.0)
    assert snap.get("sim_dump_demo") is False


def test_live_missing_lists_sungold_when_absent() -> None:
    rows = [
        {"entity_id": "sensor.solar_controller_solar", "state": "250", "attributes": {}},
        {"entity_id": "switch.sim_ac_plug_1", "state": "off", "attributes": {}},
    ]
    filtered = sfs.filter_entities(rows)
    missing = sorted(eid for eid in sfs.REQUIRED_ENTITY_IDS if eid not in filtered)
    assert "sensor.sungold_sph302480a_pv_power" in missing
    assert "sensor.solar_controller_solar_power" not in missing


def test_decide_dump_view_decisions_have_current_and_target() -> None:
    view = sfs.decide_dump_view(states=_demo_states())
    assert view["decisions"]
    row = view["decisions"][0]
    assert row["current"] in ("on", "off")
    assert row["target"] in ("on", "off", "skip")
    assert row["action"] == row["target"]


def test_unsynced_soc_zero_still_decides() -> None:
    states = _demo_states(solar="800", load="100", soc="0", plug_1="off")
    view = sfs.decide_dump_view(states=states, now=1000.0)
    assert view["soc_unsynced"] is True
    assert view["soc_gate"] == "skipped_unsynced"
    assert view["shunt_v"] == 28.6
    assert view["shunt_a"] == 2.1
    assert view["t2_shunt_v"] == 28.6
    assert view["t2_shunt_a"] == 2.1
    assert view["ku_shunt_v"] == 25.6
    assert view["ku_shunt_a"] == -4.8
    assert view.get("skipped") is None
    assert "SoC gate skipped: unsynced; using V/A + charge state only" in view["thinking"]
    assert "T2 HQ2239CQYT2 shunt 28.6V" in view["thinking"]
    assert "T2 HQ2239CQYT2 shunt +2.1A" in view["thinking"]
    assert "KU HQ2239JTRKU shunt 25.6V" in view["thinking"]
    assert "KU HQ2239JTRKU shunt -4.8A" in view["thinking"]
    assert "Shunt 28.6V" not in view["thinking"]
    assert "soak" not in view["thinking"].lower()
    assert any(d["action"] == "on" for d in view["decisions"])


def test_synced_soc_zero_skips_min_percent() -> None:
    view = sfs.decide_dump_view(
        states=_demo_states(solar="800", load="100", soc="0"),
        settings={"ha_soc_unsynced": "false"},
        now=1000.0,
    )
    assert view["skipped"] == "soc below 85"
    assert view["decisions"] == []


def test_resolve_ha_token_reads_default_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    token_file = tmp_path / "long-lived.token"
    token_file.write_text("unit-test-token-not-real\n", encoding="utf-8")
    monkeypatch.delenv("HA_TOKEN", raising=False)
    monkeypatch.delenv("HA_TOKEN_FILE", raising=False)
    monkeypatch.delenv("HA_LONG_LIVED_TOKEN_FILE", raising=False)
    monkeypatch.setattr(sfs, "default_ha_token_paths", lambda: [token_file])
    assert sfs.resolve_ha_token() == "unit-test-token-not-real"


def test_demo_numbers_are_not_live_lovelace_table() -> None:
    entities = sfs.load_demo_entities()
    assert entities["sensor.solar_controller_solar"]["state"] == "400"
    assert entities["sensor.sungold_sph302480a_load_active_power"]["state"] == "10"
    assert entities["sensor.sungold_sph302480a_load_power"]["state"] == "10"


def test_history_rejects_unknown_entity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HA_TOKEN", "unit-test-token")
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sfs.SolarFlowHandler)
    _host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        url = (
            f"http://127.0.0.1:{port}/api/history"
            "?entity_id=light.kitchen&hours=24"
        )
        try:
            urllib.request.urlopen(url, timeout=5)
            pytest.fail("expected HTTP 400")
        except urllib.error.HTTPError as err:
            assert err.code == 400
            body = json.loads(err.read().decode("utf-8"))
        assert body["error"] == "entity_id not allowed"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_history_demo_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_ha_token(monkeypatch)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sfs.SolarFlowHandler)
    _host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        url = (
            f"http://127.0.0.1:{port}/api/history"
            "?entity_id=sensor.solar_controller_solar&hours=24"
        )
        try:
            urllib.request.urlopen(url, timeout=5)
            pytest.fail("expected HTTP 503")
        except urllib.error.HTTPError as err:
            assert err.code == 503
            body = json.loads(err.read().decode("utf-8"))
        assert "error" in body
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_history_uses_filter_entity_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HA_TOKEN", "unit-test-token")
    captured: dict[str, str] = {}

    def _fake_urlopen(req, timeout=15.0):
        captured["url"] = req.full_url
        payload = json.dumps(
            [[{"entity_id": "sensor.em16_a3_power", "state": "100", "last_changed": "2026-09-16T12:00:00+00:00"}]]
        ).encode("utf-8")

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return payload

        return _Resp()

    monkeypatch.setattr(sfs, "urlopen", _fake_urlopen)
    rows = sfs.fetch_ha_history(
        "http://192.168.0.105:8123",
        "unit-test-token",
        "sensor.em16_a3_power",
        hours=24,
    )
    url = captured["url"]
    assert "filter_entity_id=sensor.em16_a3_power" in url
    assert "minimal_response" in url
    assert "no_attributes" in url
    assert "end_time=" in url
    assert "%3A" in url or "%2B" in url
    assert "significant_changes_only" not in url
    assert rows[0]["state"] == "100"


def test_build_ha_history_url_caps_hours_at_ten() -> None:
    from datetime import datetime, timezone
    from urllib.parse import parse_qs, unquote, urlparse

    url = sfs.build_ha_history_url(
        "http://192.168.0.105:8123",
        "sensor.solar_controller_solar",
        hours=24,
    )
    assert "filter_entity_id=sensor.solar_controller_solar" in url
    assert "hours=" not in url

    parsed = urlparse(url)
    start_raw = unquote(parsed.path.rsplit("/", 1)[-1])
    end_raw = unquote(parse_qs(parsed.query)["end_time"][0])
    start = datetime.fromisoformat(start_raw)
    end = datetime.fromisoformat(end_raw)
    delta_h = (end - start).total_seconds() / 3600.0
    assert 9.99 <= delta_h <= 10.01
    assert start.tzinfo is not None or start_raw.endswith("+00:00")
    assert end.tzinfo is not None or end_raw.endswith("+00:00")


def test_history_empty_returns_points_array(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HA_TOKEN", "unit-test-token")

    def _empty(_base: str, _token: str, _entity_id: str, hours: int = 24):
        return []

    monkeypatch.setattr(sfs, "fetch_ha_history", _empty)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sfs.SolarFlowHandler)
    _host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        url = (
            f"http://127.0.0.1:{port}/api/history"
            "?entity_id=sensor.em16_a3_power&hours=24"
        )
        with urllib.request.urlopen(url, timeout=5) as resp:
            assert resp.headers.get("Cache-Control") == "no-store"
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["points"] == []
        assert payload["hours"] == 10
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_is_history_entity_allowed_prefix_em16() -> None:
    assert sfs.is_history_entity_allowed("sensor.em16_a2_power")
    assert not sfs.is_history_entity_allowed("light.kitchen")


def test_build_ha_history_url_matches_official_encoding() -> None:
    url = sfs.build_ha_history_url(
        "http://192.168.0.105:8123",
        "sensor.em16_a3_power",
        hours=1,
    )
    assert url.startswith("http://192.168.0.105:8123/api/history/period/")
    assert "filter_entity_id=sensor.em16_a3_power" in url
    assert "end_time=" in url
    assert "%3A" in url
    assert "significant_changes_only" not in url


def test_http_view_demo_with_token_returns_illustrative_plant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HA_TOKEN", "unit-test-token")
    monkeypatch.setattr(
        sfs,
        "fetch_ha_states",
        lambda _b, _t: [{"entity_id": "sensor.solar_controller_solar", "state": "302", "attributes": {}}],
    )
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sfs.SolarFlowHandler)
    _host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/snapshot?view=demo", timeout=5
        ) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["mode"] == "demo"
        assert payload["view"] == "demo"
        assert payload["entities"]["sensor.solar_controller_solar_power"]["state"] == "400"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_http_view_production_with_token_uses_live_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HA_TOKEN", "unit-test-token")
    monkeypatch.setattr(sfs, "fetch_ha_states", lambda _b, _t: _ha_rows_plug1_off())
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sfs.SolarFlowHandler)
    _host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        with urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/snapshot?view=production", timeout=5
        ) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["mode"] == "live"
        assert payload["view"] == "production"
        assert payload["entities"]["switch.sim_ac_plug_1"]["state"] == "off"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_http_view_unknown_returns_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_ha_token(monkeypatch)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sfs.SolarFlowHandler)
    _host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/snapshot?view=nope", timeout=5
            )
            pytest.fail("expected HTTP 400")
        except urllib.error.HTTPError as err:
            assert err.code == 400
            body = json.loads(err.read().decode("utf-8"))
        assert "error" in body
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_history_ha_404_returns_recorder_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HA_TOKEN", "unit-test-token")

    def _raise_404(*_args, **_kwargs):
        raise urllib.error.HTTPError(
            "http://192.168.0.105:8123/api/history/period/x",
            404,
            "Not Found",
            None,
            None,
        )

    monkeypatch.setattr(sfs, "fetch_ha_history", _raise_404)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sfs.SolarFlowHandler)
    _host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        url = (
            f"http://127.0.0.1:{port}/api/history"
            "?entity_id=sensor.em16_a3_power&hours=24"
        )
        try:
            urllib.request.urlopen(url, timeout=5)
            pytest.fail("expected HTTP 503")
        except urllib.error.HTTPError as err:
            assert err.code == 503
            body = json.loads(err.read().decode("utf-8"))
        assert body["error"] == sfs.HISTORY_RECORDER_DISABLED_MSG
    finally:
        httpd.shutdown()
        thread.join(timeout=2)
