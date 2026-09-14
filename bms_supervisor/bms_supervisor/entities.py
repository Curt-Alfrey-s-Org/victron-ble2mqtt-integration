"""Home Assistant MQTT entity definitions (sensors and binary_sensors only)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityDef:
    key: str
    name: str
    topic_type: str  # sensor or binary_sensor
    device_class: str | None = None
    state_class: str | None = None
    unit: str | None = None
    icon: str | None = None
    metric_attr: str = ""  # attribute on ParsedMetrics


CURATED_ENTITIES: tuple[EntityDef, ...] = (
    EntityDef(
        key="voltage",
        name="Battery voltage",
        topic_type="sensor",
        device_class="voltage",
        state_class="measurement",
        unit="V",
        metric_attr="voltage_v",
    ),
    EntityDef(
        key="current",
        name="Battery current",
        topic_type="sensor",
        device_class="current",
        state_class="measurement",
        unit="A",
        metric_attr="current_a",
    ),
    EntityDef(
        key="power",
        name="Battery power",
        topic_type="sensor",
        device_class="power",
        state_class="measurement",
        unit="W",
        metric_attr="power_w",
    ),
    EntityDef(
        key="soc",
        name="State of charge",
        topic_type="sensor",
        device_class="battery",
        state_class="measurement",
        unit="%",
        metric_attr="soc_pct",
    ),
    EntityDef(
        key="consumed_ah",
        name="Consumed amp hours",
        topic_type="sensor",
        state_class="total_increasing",
        unit="Ah",
        metric_attr="consumed_ah",
    ),
    EntityDef(
        key="temperature",
        name="Battery temperature",
        topic_type="sensor",
        device_class="temperature",
        state_class="measurement",
        unit="C",
        metric_attr="temperature_c",
    ),
    EntityDef(
        key="alarm",
        name="Alarm",
        topic_type="binary_sensor",
        device_class="problem",
        metric_attr="alarm",
    ),
)
