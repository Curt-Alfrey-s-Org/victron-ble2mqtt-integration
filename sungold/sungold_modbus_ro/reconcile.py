"""Align INPUT BATT A sign with INPUT BATT KW (Victron-style: + charge, - discharge)."""

from __future__ import annotations

_CHARGE_POWER_W = 15.0
_MIN_VOLTAGE_V = 20.0
_ZERO_CURRENT_A = 0.05


def reconcile_battery_current(
    charging_power_s: str | None,
    voltage_s: str | None,
    current_s: str | None,
) -> str | None:
    """When battery input power is clearly charging, force positive amps."""
    if current_s is None:
        return None
    try:
        watts = float(charging_power_s) if charging_power_s is not None else 0.0
        volts = float(voltage_s) if voltage_s is not None else 0.0
        amps = float(current_s)
    except (TypeError, ValueError):
        return current_s
    if watts > _CHARGE_POWER_W and volts > _MIN_VOLTAGE_V:
        mag = abs(amps)
        if mag < _ZERO_CURRENT_A:
            mag = watts / volts
        return f"{mag:.1f}"
    return current_s
