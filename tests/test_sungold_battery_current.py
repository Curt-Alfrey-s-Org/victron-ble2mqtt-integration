"""Battery current sign matches INPUT BATT KW (positive when charging)."""

from __future__ import annotations

from sungold.sungold_modbus_ro.reconcile import reconcile_battery_current


def test_reconcile_forces_positive_amps_when_charging() -> None:
    out = reconcile_battery_current("749", "26.9", "-29.3")
    assert out == "29.3"


def test_reconcile_uses_power_over_voltage_when_amps_near_zero() -> None:
    out = reconcile_battery_current("749", "26.9", "0.0")
    assert out == "27.8"


def test_reconcile_leaves_idle_current_unchanged() -> None:
    out = reconcile_battery_current("2", "26.9", "-0.1")
    assert out == "-0.1"
