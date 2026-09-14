"""Environment-driven configuration for bms_supervisor sidecar."""

from __future__ import annotations

import os
from dataclasses import dataclass

VALID_ADAPTERS = frozenset({"generic_shunt", "litime_shunt", "aes_lynk_observe"})

ADAPTER_METADATA: dict[str, dict[str, str]] = {
    "generic_shunt": {
        "manufacturer": "Victron Energy",
        "model": "SmartShunt (generic)",
    },
    "litime_shunt": {
        "manufacturer": "LiTime",
        "model": "External shunt via VE.Direct",
    },
    "aes_lynk_observe": {
        "manufacturer": "Discover AES",
        "model": "External shunt observe (not LYNK)",
    },
}


@dataclass(frozen=True)
class Settings:
    serial_device: str
    adapter: str
    bank_id: str
    mqtt_host: str
    mqtt_port: int
    mqtt_user: str
    mqtt_password: str
    mqtt_topic: str
    device_name: str
    heartbeat_file: str
    manufacturer: str
    model: str


def load_settings() -> Settings:
    user = os.getenv("MQTT_USER") or os.getenv("MQTT_USERNAME") or ""
    password = os.getenv("MQTT_PASSWORD") or ""
    if not user or not password:
        raise ValueError("MQTT_USER/MQTT_USERNAME and MQTT_PASSWORD must be set")

    adapter = os.getenv("BMS_ADAPTER", "generic_shunt").strip().lower()
    if adapter not in VALID_ADAPTERS:
        raise ValueError(
            f"BMS_ADAPTER must be one of {sorted(VALID_ADAPTERS)}, got '{adapter}'"
        )

    meta = ADAPTER_METADATA[adapter]
    bank_id = os.getenv("BMS_BANK_ID", "bench").strip().lower()
    device_name = os.getenv("BMS_DEVICE_NAME") or f"BMS supervisor ({adapter}, {bank_id})"

    return Settings(
        serial_device=os.getenv("BMS_SERIAL_DEVICE", "/dev/vedirect"),
        adapter=adapter,
        bank_id=bank_id,
        mqtt_host=os.getenv("MQTT_HOST", "127.0.0.1"),
        mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
        mqtt_user=user,
        mqtt_password=password,
        mqtt_topic=os.getenv("BMS_MQTT_TOPIC", "bms_supervisor"),
        device_name=device_name,
        heartbeat_file=os.getenv("HEARTBEAT_FILE", "/tmp/bms_supervisor.heartbeat"),
        manufacturer=meta["manufacturer"],
        model=meta["model"],
    )
