"""Watt hop ledger: KU residual stays None without KU Renogy DC."""

from __future__ import annotations

import sys
from math import isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from solar_watt_ledger import (  # noqa: E402
    _CONVERSION_HOP_IDS,
    apply_ledger_to_meta,
    build_watt_ledger,
    ku_equal_share_w,
    ku_unmetered_pv_residual,
)


def _row(eid: str, state: str) -> dict:
    return {"entity_id": eid, "state": state}


def test_ku_unmetered_pv_residual_formula() -> None:
    assert isclose(ku_unmetered_pv_residual(80.3, 4.5, 400.0), 475.8, rel_tol=1e-6)
    assert ku_unmetered_pv_residual(80.3, 4.5, None) is None
    assert isclose(ku_unmetered_pv_residual(-803.4, 223.4, 0.0), -1026.8, rel_tol=1e-6)
    assert ku_unmetered_pv_residual(-803.4, 223.4, None) is None


def test_ku_unmetered_pv_est_stays_none_without_renogy_dc() -> None:
    states = {
        "sensor.solar_controller_solar_power": _row(
            "sensor.solar_controller_solar_power", "250"
        ),
        "sensor.battery_1_power": _row("sensor.battery_1_power", "26.6"),
        "sensor.battery_2_power": _row("sensor.battery_2_power", "-803.4"),
    }
    ledger = build_watt_ledger(states)
    assert ledger["ku_unmetered_pv_est_w"] is None
    hop = {h["id"]: h for h in ledger["watt_hops"]}["ku_victron_pwm"]
    assert hop["unmetered"] is True
    assert hop["watts_in"] is None
    assert hop["loss_w"] is None
    meta: dict = {}
    apply_ledger_to_meta(meta, states, 250.0)
    assert meta["ku_unmetered_pv_est_w"] is None
    assert "ku_victron_pwm" not in {"t2_mppt", "sungold"}


def test_ku_renogy_ac_est_is_batt2_load_not_shunt() -> None:
    states = {
        "sensor.solar_controller_solar_power": _row(
            "sensor.solar_controller_solar_power", "150"
        ),
        "sensor.battery_1_power": _row("sensor.battery_1_power", "225"),
        "sensor.battery_2_power": _row("sensor.battery_2_power", "276"),
        "sensor.em16_a3_power": _row("sensor.em16_a3_power", "25"),
    }
    ledger = build_watt_ledger(states)
    assert isclose(ledger["jumper_w"], -75.0, rel_tol=1e-6)
    assert isclose(ledger["ku_renogy_ac_est_w"], 25.0, rel_tol=1e-6)
    assert isclose(ledger["ku_unmetered_pv_est_w"], 376.0, rel_tol=1e-6)
    assert ledger["ku_unmetered_pv_est_kind"] == "ac_lower_bound"
    hops = {h["id"]: h for h in ledger["watt_hops"]}
    assert hops["ku_battery"]["stored_w"] == 276.0
    assert hops["ku_renogy_ac"]["watts_in"] == 25.0
    assert hops["ku_renogy_ac"]["watts_in"] != hops["ku_battery"]["stored_w"]
    assert hops["ku_victron_pwm"]["unmetered"] is True
    assert hops["ku_victron_pwm"]["watts_in"] is None
    naive = (276.0 + 25.0) / 3.0
    share = 376.0 / 3.0
    assert isclose(ledger["ku_charger_equal_share_w"], share, rel_tol=1e-6)
    assert isclose(ku_equal_share_w(376.0), share, rel_tol=1e-6)
    assert not isclose(ledger["ku_charger_equal_share_w"], naive, rel_tol=1e-6)


def test_vent_fan_residual_matches_trailer_minus_uti_hop() -> None:
    states = {
        "sensor.em16_a3_power": _row("sensor.em16_a3_power", "25"),
        "sensor.sungold_sph302480a_grid_voltage": _row(
            "sensor.sungold_sph302480a_grid_voltage", "117"
        ),
        "sensor.sungold_sph302480a_grid_current": _row(
            "sensor.sungold_sph302480a_grid_current", "0"
        ),
        "sensor.sungold_sph302480a_load_active_power": _row(
            "sensor.sungold_sph302480a_load_active_power", "5"
        ),
    }
    ledger = build_watt_ledger(states)
    assert ledger["sungold_ac_in_w"] == 5.0
    assert ledger["vent_fan_w"] == 20.0
    hops = {h["id"]: h for h in ledger["watt_hops"]}
    assert hops["vent_fan"]["watts_in"] == 20.0


def test_sungold_ac_in_passthrough_from_load_when_grid_va_zero() -> None:
    states = {
        "sensor.em16_a3_power": _row("sensor.em16_a3_power", "25"),
        "sensor.sungold_sph302480a_grid_voltage": _row(
            "sensor.sungold_sph302480a_grid_voltage", "117"
        ),
        "sensor.sungold_sph302480a_grid_current": _row(
            "sensor.sungold_sph302480a_grid_current", "0"
        ),
        "sensor.sungold_sph302480a_load_active_power": _row(
            "sensor.sungold_sph302480a_load_active_power", "5"
        ),
    }
    ledger = build_watt_ledger(states)
    assert ledger["sungold_ac_in_w"] == 5.0
    hops = {h["id"]: h for h in ledger["watt_hops"]}
    assert hops["ac_a3_uti"]["watts_in"] == 5.0


def test_combined_path_losses_and_vent_fan_not_conversion() -> None:
    states = {
        "sensor.solar_controller_solar_power": _row(
            "sensor.solar_controller_solar_power", "150"
        ),
        "sensor.battery_1_power": _row("sensor.battery_1_power", "225"),
        "sensor.battery_2_power": _row("sensor.battery_2_power", "276"),
        "sensor.em16_a3_power": _row("sensor.em16_a3_power", "25"),
    }
    ledger = build_watt_ledger(states)
    conv = float(ledger["combined_losses_w"])
    vdrop = float(ledger["combined_vdrop_loss_w"])
    path = float(ledger["combined_path_losses_w"])
    assert isclose(path, conv + vdrop, rel_tol=1e-6)
    assert "vent_fan" not in _CONVERSION_HOP_IDS
    hops = {h["id"]: h for h in ledger["watt_hops"]}
    assert hops["vent_fan"]["id"] == "vent_fan"
    assert hops["vent_fan"].get("loss_w") is None
