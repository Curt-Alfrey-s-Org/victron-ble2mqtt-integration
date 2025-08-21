# /home/n4s1/victron-ble2mqtt-integration/override/victron_ble2mqtt/user_settings.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Any
import importlib, os, socket

@dataclass
class MqttConfig:
    host: str = "localhost"
    port: int = 1883
    username: Optional[str] = None
    user_name: Optional[str] = None
    password: Optional[str] = None
    tls: bool = False
    ca_file: Optional[str] = None
    main_uid: Optional[str] = None
    publish_config_throttle_seconds: int = 60

@dataclass
class DeviceEntry:
    mac: str
    type: Optional[str] = None
    name: Optional[str] = None
    advertisement_key: Optional[str] = None

@dataclass
class UserSettings:
    mqtt: MqttConfig = field(default_factory=MqttConfig)
    devices: List[DeviceEntry] = field(default_factory=list)
    def __post_init__(self) -> None:
        data = importlib.import_module("victron_ble2mqtt.user_settings_data")
        try:
            data = importlib.reload(data)
        except Exception:
            pass
        self.mqtt.host = getattr(data, "mqtt_host", self.mqtt.host)
        self.mqtt.port = int(getattr(data, "mqtt_port", self.mqtt.port))
        self.mqtt.username = getattr(data, "mqtt_username", None)
        self.mqtt.user_name = getattr(data, "mqtt_username", None) or self.mqtt.username or os.getenv("MQTT_USER")
        self.mqtt.password = getattr(data, "mqtt_password", None)
        self.mqtt.main_uid = getattr(data, "main_uid", None) or os.getenv("MAIN_UID") or socket.gethostname()
        pcs = getattr(data, "publish_config_throttle_seconds", None) or os.getenv("PUBLISH_CONFIG_THROTTLE_SEC")
        if pcs not in (None, ""):
            try:
                self.mqtt.publish_config_throttle_seconds = int(pcs)
            except Exception:
                pass
        raw_devices: List[dict[str, Any]] = list(getattr(data, "devices", []))
        norm: List[DeviceEntry] = []
        for d in raw_devices:
            if isinstance(d, dict):
                norm.append(DeviceEntry(
                    mac=str(d.get("mac","")),
                    type=d.get("type"),
                    name=d.get("name"),
                    advertisement_key=d.get("advertisement_key"),
                ))
        self.devices = norm
