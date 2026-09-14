"""Home Assistant MQTT discovery publisher (sensors and binary_sensors only)."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

import paho.mqtt.client as mqtt

from .entities import CURATED_ENTITIES, EntityDef
from .vedirect_text import ParsedMetrics

if TYPE_CHECKING:
    from .config import Settings


class MqttHaPublisher:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._device = {
            "identifiers": ["bms_supervisor", settings.adapter, settings.bank_id],
            "name": settings.device_name,
            "manufacturer": settings.manufacturer,
            "model": settings.model,
        }
        self._hidden: set[str] = set()
        self._availability_topic = f"{settings.mqtt_topic}/{settings.adapter}/status"
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv311)
        self._client.username_pw_set(settings.mqtt_user, settings.mqtt_password)
        self._client.on_connect = self._on_connect
        self._client.will_set(self._availability_topic, payload="offline", qos=1, retain=True)

    @property
    def client(self) -> mqtt.Client:
        return self._client

    def connect_with_retry(self) -> None:
        delay = 1.0
        while True:
            try:
                self._client.connect(self._settings.mqtt_host, self._settings.mqtt_port)
                return
            except OSError as exc:
                print(f"MQTT connection failed: {exc} -- retrying in {delay:.0f}s")
                time.sleep(delay)
                delay = min(delay * 2, 60.0)

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            print(f"MQTT connect failed: {reason_code}")
            return
        print(f"MQTT connected ({reason_code})")
        self._client.publish(self._availability_topic, "online", qos=1, retain=True)
        for entity in CURATED_ENTITIES:
            if entity.key not in self._hidden:
                self.publish_discovery(entity)

    def _field_name(self, entity: EntityDef) -> str:
        return (
            f"{self._settings.mqtt_topic}-{self._settings.adapter}-"
            f"{self._settings.bank_id}-{entity.key.replace('/', '-')}"
        )

    def _state_topic(self, entity: EntityDef) -> str:
        return f"{self._settings.mqtt_topic}/{self._settings.adapter}/{entity.key}/state"

    def discovery_topic(self, entity: EntityDef) -> str:
        base = f"{self._settings.mqtt_topic}-{self._settings.adapter}-{entity.key.replace('/', '-')}"
        return f"homeassistant/{entity.topic_type}/{base}/config"

    def build_discovery_payload(self, entity: EntityDef) -> dict:
        payload: dict = {
            "name": entity.name,
            "unique_id": self._field_name(entity),
            "device": self._device,
            "state_topic": self._state_topic(entity),
            "availability_topic": self._availability_topic,
            "payload_available": "online",
            "payload_not_available": "offline",
        }
        if entity.icon:
            payload["icon"] = entity.icon
        if entity.device_class:
            payload["device_class"] = entity.device_class
        if entity.state_class:
            payload["state_class"] = entity.state_class
        if entity.unit:
            payload["unit_of_measurement"] = entity.unit
        if entity.topic_type == "binary_sensor":
            payload["payload_on"] = "ON"
            payload["payload_off"] = "OFF"
        return payload

    def publish_discovery(self, entity: EntityDef) -> None:
        topic = self.discovery_topic(entity)
        payload = json.dumps(self.build_discovery_payload(entity))
        self._client.publish(topic, payload, retain=True)

    def hide_entity(self, entity: EntityDef) -> None:
        if entity.key in self._hidden:
            return
        self._hidden.add(entity.key)
        self._client.publish(self.discovery_topic(entity), "", retain=True)
        print(f"Disabled HA entity (no data): {entity.key}")

    def restore_entity(self, entity: EntityDef) -> None:
        if entity.key not in self._hidden:
            return
        self._hidden.discard(entity.key)
        self.publish_discovery(entity)
        print(f"Restored HA entity: {entity.key}")

    def publish_state(self, entity: EntityDef, value: str, *, publish_timeout: float = 5.0) -> bool:
        # Heartbeat liveness: only count publishes that left the client (Paho MQTTMessageInfo).
        # https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html#paho.mqtt.client.Client.publish
        if not self._client.is_connected():
            return False
        info = self._client.publish(self._state_topic(entity), value, retain=False)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            return False
        try:
            info.wait_for_publish(timeout=publish_timeout)
        except (RuntimeError, ValueError):
            return False
        return info.is_published()

    def publish_metrics(self, metrics: ParsedMetrics) -> bool:
        """Publish present metrics; hide temperature when absent. True only if MQTT state succeeded."""
        published_any = False
        for entity in CURATED_ENTITIES:
            raw = getattr(metrics, entity.metric_attr, None)
            if raw is None:
                if entity.key == "temperature" and entity.key not in self._hidden:
                    self.hide_entity(entity)
                continue
            if entity.key == "temperature" and entity.key in self._hidden:
                self.restore_entity(entity)
            if entity.topic_type == "binary_sensor":
                value = str(raw)
            elif isinstance(raw, float):
                value = f"{raw:.3f}".rstrip("0").rstrip(".")
            else:
                value = str(raw)
            if self.publish_state(entity, value):
                published_any = True
        return published_any
