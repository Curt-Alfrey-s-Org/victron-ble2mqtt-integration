"""Tests for scripts/solar_flow_server.py (demo snapshot + soak view)."""

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


def _demo_states(
    *,
    solar: str = "400",
    load: str = "100",
    soc: str = "92",
    charge: str = "absorption",
    plug_1: str = "on",
) -> dict[str, dict]:
    return {
        "sensor.solar_controller_solar_power": {"entity_id": "sensor.solar_controller_solar_power", "state": solar},
        "sensor.em16_a3_power": {"entity_id": "sensor.em16_a3_power", "state": load},
        "sensor.battery_1_soc": {"entity_id": "sensor.battery_1_soc", "state": soc},
        "sensor.battery_1_voltage": {"entity_id": "sensor.battery_1_voltage", "state": "28.6"},
        "sensor.battery_1_current": {"entity_id": "sensor.battery_1_current", "state": "2.1"},
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
    monkeypatch.delenv("HA_TOKEN", raising=False)
    monkeypatch.delenv("HA_TOKEN_FILE", raising=False)
    monkeypatch.delenv("HA_LONG_LIVED_TOKEN_FILE", raising=False)
    snap = sfs.build_snapshot(now=1000.0)
    assert snap["mode"] == "demo"
    assert "DEMO" in snap.get("label", "")
    assert snap["entities"]["sensor.solar_controller_solar_power"]["state"] == "400"
    assert snap["ai"]["meta"]["surplus_w"] == 120.0
    assert all(d["action"] == "skip" for d in snap["ai"]["decisions"])


def test_decide_soak_view_surplus_math() -> None:
    view = sfs.decide_soak_view(states=_demo_states(), now=1000.0)
    meta = view["meta"]
    assert meta["effective_load_w"] == 280.0
    assert meta["sim_plug_w"] == 180
    assert meta["surplus_w"] == 120.0
    assert "Surplus 120W" in view["thinking"]
    assert len(view["decisions"]) == 6


def test_decide_soak_view_turns_on_above_threshold() -> None:
    states = _demo_states(solar="800", load="100", plug_1="off")
    view = sfs.decide_soak_view(states=states, now=1000.0)
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
    assert set(filtered.keys()) == {
        "sensor.solar_controller_solar_power",
        "switch.sim_ac_plug_1",
    }
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


def test_filter_prefers_canonical_over_alias() -> None:
    rows = [
        {"entity_id": "sensor.solar_controller_solar_power", "state": "400", "attributes": {}},
        {"entity_id": "sensor.solar_controller_solar", "state": "1", "attributes": {}},
    ]
    filtered = sfs.filter_entities(rows)
    assert filtered["sensor.solar_controller_solar_power"]["state"] == "400"
    assert "source_entity_id" not in filtered["sensor.solar_controller_solar_power"]


def test_http_snapshot_cache_control(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HA_TOKEN", raising=False)
    monkeypatch.delenv("HA_TOKEN_FILE", raising=False)
    monkeypatch.delenv("HA_LONG_LIVED_TOKEN_FILE", raising=False)

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
    monkeypatch.delenv("HA_TOKEN", raising=False)
    monkeypatch.delenv("HA_TOKEN_FILE", raising=False)
    monkeypatch.delenv("HA_LONG_LIVED_TOKEN_FILE", raising=False)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), sfs.SolarFlowHandler)
    _host, port = httpd.server_address
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/snapshot", timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        assert payload["mode"] == "demo"
        assert payload["ai"]["meta"]["surplus_w"] == 120.0
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_live_handler_error_json_redacts_token(monkeypatch: pytest.MonkeyPatch) -> None:
    token = "abc123secret-token"
    monkeypatch.setenv("HA_TOKEN", token)

    def _fail_live(_token: str) -> dict:
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


def test_required_entity_ids_include_battery_2_and_plug_power() -> None:
    assert "sensor.battery_2_soc" in sfs.REQUIRED_ENTITY_IDS
    assert "sensor.battery_2_power" in sfs.REQUIRED_ENTITY_IDS
    assert "sensor.sim_ac_plug_1_power" in sfs.REQUIRED_ENTITY_IDS
    assert "sensor.sim_soak_load_power" in sfs.REQUIRED_ENTITY_IDS
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
    snap = sfs.build_demo_snapshot(now=1000.0)
    assert snap["ai"]["meta"]["surplus_w"] == 120.0


def test_live_missing_lists_sungold_when_absent() -> None:
    rows = [
        {"entity_id": "sensor.solar_controller_solar", "state": "250", "attributes": {}},
        {"entity_id": "switch.sim_ac_plug_1", "state": "off", "attributes": {}},
    ]
    filtered = sfs.filter_entities(rows)
    missing = sorted(eid for eid in sfs.REQUIRED_ENTITY_IDS if eid not in filtered)
    assert "sensor.sungold_sph302480a_pv_power" in missing
    assert "sensor.solar_controller_solar_power" not in missing


def test_decide_soak_view_decisions_have_current_and_target() -> None:
    view = sfs.decide_soak_view(states=_demo_states())
    assert view["decisions"]
    row = view["decisions"][0]
    assert row["current"] in ("on", "off")
    assert row["target"] in ("on", "off", "skip")
    assert row["action"] == row["target"]


def test_unsynced_soc_zero_still_decides() -> None:
    states = _demo_states(solar="800", load="100", soc="0", plug_1="off")
    view = sfs.decide_soak_view(states=states, now=1000.0)
    assert view["soc_unsynced"] is True
    assert view["soc_gate"] == "skipped_unsynced"
    assert view["shunt_v"] == 28.6
    assert view["shunt_a"] == 2.1
    assert view.get("skipped") is None
    assert "SoC gate skipped: unsynced; using V/A + charge state only" in view["thinking"]
    assert "28.6V" in view["thinking"]
    assert any(d["action"] == "on" for d in view["decisions"])


def test_synced_soc_zero_skips_min_percent() -> None:
    view = sfs.decide_soak_view(
        states=_demo_states(solar="800", load="100", soc="0"),
        settings={"ha_soc_unsynced": "false"},
        now=1000.0,
    )
    assert view["skipped"] == "soc below 85"
    assert view["decisions"] == []


def test_filter_aliases_sungold_pv1_entity_ids() -> None:
    rows = [
        {
            "entity_id": "sensor.sungold_sph302480a_pv1_power",
            "state": "42",
            "attributes": {"unit_of_measurement": "W"},
        },
        {
            "entity_id": "sensor.sungold_sph302480a_pv1_voltage",
            "state": "48.1",
            "attributes": {"unit_of_measurement": "V"},
        },
        {
            "entity_id": "sensor.sungold_sph302480a_inverter_charging_power",
            "state": "900",
            "attributes": {"unit_of_measurement": "W"},
        },
    ]
    filtered = sfs.filter_entities(rows)
    assert filtered["sensor.sungold_sph302480a_pv_power"]["state"] == "42"
    assert filtered["sensor.sungold_sph302480a_pv_voltage"]["state"] == "48.1"
    assert filtered["sensor.sungold_sph302480a_charging_power"]["state"] == "900"


def test_resolve_bind_host_tailscale_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOLAR_FLOW_HOST", raising=False)
    monkeypatch.delenv("SOLAR_FLOW_TAILSCALE", raising=False)
    args = sfs.parse_args(["--tailscale"])
    assert sfs.resolve_bind_host(args) == "0.0.0.0"


def test_access_urls_localhost_only_by_default() -> None:
    urls = sfs.access_urls("127.0.0.1", 8765)
    assert urls == ["http://127.0.0.1:8765/"]


def test_access_urls_includes_tailscale_when_discovered(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sfs,
        "discover_tailscale_identity",
        lambda: {
            "tailscale_ip": "100.64.1.2",
            "magicdns": "ha-host.tailnet.ts.net",
        },
    )
    monkeypatch.setattr(sfs, "discover_serve_https_url", lambda: "https://ha-host.tailnet.ts.net")
    urls = sfs.access_urls("0.0.0.0", 8765)
    assert "http://127.0.0.1:8765/" in urls
    assert "http://100.64.1.2:8765/" in urls
    assert "http://ha-host.tailnet.ts.net:8765/" in urls
    assert "https://ha-host.tailnet.ts.net/" in urls