"""Curated read-only holding registers for Sungold SPH302480A.

HA entity names follow the official LCD real-time pages and fault table
(SPH302480A user manual §4.1 and §6.2), not SRNE nicknames.

Manual: https://sungoldpower.com/products/3000w-24v-solar-inverter-charger
Reprint: https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf

Register addresses/scaling still follow timbit123/srne-modbus (Apache-2.0).
The SPH302480A manual does not publish a Modbus map.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# CHARGE LED: Flash = Battery charging; Steady = Charging completed.
# Setup items [09]/[11]: boost charge / floating charge.
CHARGING_STATES: dict[int, str] = {
    0: "Not charging",
    1: "Boost charge",
    2: "Constant-voltage charge",
    4: "Floating charge",
    6: "Lithium battery activation",
    8: "Charging completed",
}

# AC/INV yellow LED (§4.1): Steady on = Mains output; Flash = Inverter output.
# 0/1 are not named on the SPH302480A LCD.
MACHINE_STATES: dict[int, str] = {
    0: "Initialization",
    1: "Standby",
    2: "Mains output",
    3: "Inverter output",
}

# §6.2 Fault code meaning (【NN】 names from the SPH302480A manual).
FAIL_CODES: dict[int, str] = {
    0: "No reported error",
    1: "Battery undervoltage alarm",
    2: "Battery discharge average current overcurrent software protection",
    3: "Battery not-connected alarm",
    4: "Battery undervoltage stop discharge alarm",
    5: "Battery overcurrent hardware protection",
    6: "Charging overvoltage protection",
    7: "Bus overvoltage hardware protection",
    8: "Bus overvoltage software protection",
    9: "PV overvoltage protection",
    10: "Buck overcurrent software protection",
    11: "Buck overcurrent hardware protection",
    12: "Mains power down",
    13: "Bypass overload protection",
    14: "Inverter overload protection",
    15: "Inverter overcurrent hardware protection",
    17: "Inverter short circuit protection",
    19: "Buck heat sink over temperature protection",
    20: "Inverter heat sink over temperature protection",
    21: "Fan failure",
    22: "Memory failure",
    23: "Model setting error",
    26: "Inverted AC output backfills to bypass AC input",
    29: "Internal battery boost circuit failure",
    30: "Battery capacity rate lower than 10%",
    31: "Battery capacity rate lower than 5%",
    32: "Inverter stops when battery capacity is low",
    34: "CAN communication fault in parallel operation",
    58: "BMS communication error",
    59: "BMS alarm",
    60: "BMS battery low temperature alarm",
    61: "BMS battery over temperature alarm",
    62: "BMS battery over current alarm",
    63: "BMS low battery alarm",
    64: "BMS battery over voltage alarm",
}

# Removed from SPH302480A discovery (unique_id uses mqtt_topic + key).
RETIRED_DISCOVERY: tuple[tuple[str, str], ...] = (
    ("sensor", "pv/total_power"),
    ("sensor", "grid/power"),
    ("sensor", "temperature/transformer"),
)


@dataclass(frozen=True)
class EntityDef:
    key: str
    name: str
    register: int
    topic_type: str = "sensor"
    scale: float = 1.0
    signed: bool = False
    integer: bool = False
    lookup: dict[int, str] | None = None
    device_class: str | None = None
    state_class: str | None = None
    unit: str | None = None
    icon: str | None = None
    entity_category: str | None = None
    clamp_zero: bool = False
    format_hex: bool = False
    invert: bool = False
    value_fn: str | None = None  # "failcode" for special decode


# Single-phase 120 V, one MPPT / one PV port.
CURATED_ENTITIES: tuple[EntityDef, ...] = (
    EntityDef("pv1/voltage", "PV input voltage", 0x0107, scale=0.1, device_class="voltage", state_class="measurement", unit="V", icon="mdi:solar-power"),
    EntityDef("pv1/current", "PV output current", 0x0108, scale=0.1, device_class="current", state_class="measurement", unit="A", icon="mdi:solar-power"),
    EntityDef("pv1/power", "PV output power", 0x0109, integer=True, device_class="power", state_class="measurement", unit="W", icon="mdi:solar-power"),
    EntityDef("battery/soc", "Remaining battery", 0x0100, integer=True, device_class="battery", state_class="measurement", unit="%", icon="mdi:battery"),
    EntityDef("battery/voltage", "Battery input voltage", 0x0101, scale=0.1, device_class="voltage", state_class="measurement", unit="V", icon="mdi:current-dc"),
    EntityDef("battery/current", "Input battery current", 0x0102, scale=0.1, signed=True, device_class="current", state_class="measurement", unit="A", icon="mdi:current-dc"),
    EntityDef("battery/temperature", "Battery temperature", 0x0103, scale=0.1, signed=True, device_class="temperature", state_class="measurement", unit="°C", icon="mdi:thermometer"),
    EntityDef("battery/charge_state", "Charge state", 0x010B, lookup=CHARGING_STATES, icon="mdi:battery-charging"),
    EntityDef("inverter/charging_power", "Battery input power", 0x010E, integer=True, device_class="power", state_class="measurement", unit="W", icon="mdi:battery-charging"),
    EntityDef("inverter/state", "Output mode", 0x0210, lookup=MACHINE_STATES, icon="mdi:information"),
    EntityDef("inverter/error_flags", "Inverter error flags", 0x0200, integer=True, format_hex=True, entity_category="diagnostic", icon="mdi:alert-circle"),
    EntityDef("inverter/failcode", "Fault code", 0x0204, value_fn="failcode", entity_category="diagnostic", icon="mdi:alert-circle"),
    EntityDef("grid/voltage", "AC input voltage", 0x0213, scale=0.1, device_class="voltage", state_class="measurement", unit="V", icon="mdi:transmission-tower"),
    EntityDef("grid/current", "AC input current", 0x0214, scale=0.1, device_class="current", state_class="measurement", unit="A", icon="mdi:transmission-tower"),
    EntityDef("grid/frequency", "AC input frequency", 0x0215, scale=0.01, device_class="frequency", state_class="measurement", unit="Hz", icon="mdi:sine-wave"),
    EntityDef("inverter/voltage", "Output load voltage", 0x0216, scale=0.1, device_class="voltage", state_class="measurement", unit="V", icon="mdi:lightning-bolt"),
    EntityDef("inverter/frequency", "AC output frequency", 0x0218, scale=0.01, device_class="frequency", state_class="measurement", unit="Hz", icon="mdi:sine-wave"),
    EntityDef("load/current", "AC output load current", 0x0219, scale=0.1, clamp_zero=True, device_class="current", state_class="measurement", unit="A", icon="mdi:flash"),
    EntityDef("load/power", "Load active power", 0x021B, clamp_zero=True, device_class="power", state_class="measurement", unit="W", icon="mdi:flash"),
    EntityDef("temperature/dc_dc", "PV charger heatsink temperature", 0x0220, scale=0.1, signed=True, device_class="temperature", state_class="measurement", unit="°C", icon="mdi:thermometer"),
    EntityDef("temperature/dc_ac", "Inverter heat sink temperature", 0x0221, scale=0.1, signed=True, device_class="temperature", state_class="measurement", unit="°C", icon="mdi:thermometer"),
    EntityDef("inverter/fault_active", "Fault state", 0x0204, topic_type="binary_sensor", value_fn="fault_binary", icon="mdi:alert"),
)


def decode_failcode(raw: int) -> str:
    if raw == 0:
        return FAIL_CODES[0]
    return FAIL_CODES.get(raw, f"Unknown fault ({raw})")


def decode_fault_binary(raw: int) -> str:
    return "ON" if raw != 0 else "OFF"


VALUE_FN: dict[str, Callable[[int], str]] = {
    "failcode": decode_failcode,
    "fault_binary": decode_fault_binary,
}
