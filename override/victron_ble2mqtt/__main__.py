"""
Minimal runtime entrypoint for victron_ble2mqtt.

- Uses production Python settings (no TOML), via override:
    victron_ble2mqtt.cli_app.settings.get_settings()
- Publishes over MQTT with paho-mqtt (connected in this file).
- Scans BLE via victron_ble.scanner.BaseScanner and forwards to your
  VictronMqttDeviceHandler in override/victron_ble2mqtt/mqtt.py.

This file allows:  python -m victron_ble2mqtt
and works with PYTHONPATH prioritizing /app/override before /app.
"""

import asyncio
import logging
import os
from typing import List, Dict, Any

from bleak import AdvertisementData, BLEDevice
from paho.mqtt.client import Client as PahoClient
from victron_ble.scanner import BaseScanner

# Production settings & handlers from your override package
from victron_ble2mqtt.cli_app.settings import get_settings
from victron_ble2mqtt.mqtt import VictronMqttDeviceHandler
from victron_ble2mqtt.victron_ble_utils import DeviceHandler


def _build_mqtt_client(host: str, port: int, username: str | None, password: str | None) -> PahoClient:
    client = PahoClient()
    if username:
        client.username_pw_set(username, password or "")
    client.connect(host, port)
    client.loop_start()
    return client


def _settings_to_keys(user_settings) -> List[Dict[str, Any]]:
    # Convert dataclass device entries to the dict structure DeviceHandler expects.
    keys = []
    for d in getattr(user_settings, "devices", []):
        keys.append(
            {
                "mac": getattr(d, "mac", None),
                "type": getattr(d, "type", None),
                "name": getattr(d, "name", None),
                "advertisement_key": getattr(d, "advertisement_key", None),
            }
        )
    return keys


def main() -> None:
    # Logging level: from env LOG_LEVEL or default INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    try:
        level = getattr(logging, log_level, logging.INFO)
    except Exception:
        level = logging.INFO
    logging.basicConfig(level=level)
    logger = logging.getLogger(__name__)

    # Load production settings (override/victron_ble2mqtt/user_settings*.py)
    user_settings = get_settings()

    # Build device keys list for the DeviceHandler
    keys = _settings_to_keys(user_settings)
    logger.info("victron_ble2mqtt starting with %d device entries", len(keys))

    # Prepare MQTT client (paho-mqtt)
    uname = getattr(user_settings.mqtt, "user_name", None) or getattr(user_settings.mqtt, "username", None)
    paho = _build_mqtt_client(
        host=getattr(user_settings.mqtt, "host", "localhost"),
        port=int(getattr(user_settings.mqtt, "port", 1883)),
        username=uname,
        password=getattr(user_settings.mqtt, "password", None),
    )

    class MqttPublisher(BaseScanner):
        def __init__(self, *, keys: List[Dict[str, Any]]):
            super().__init__()
            self.device_handler = DeviceHandler(keys)
            self.victron_mqtt_handler = VictronMqttDeviceHandler(user_settings=user_settings)
            self.mqtt_client = paho
            self.rssi_info: dict[str, int] = {}

        def _detection_callback(self, device: BLEDevice, advertisement: AdvertisementData):
            # cache latest RSSI by MAC
            self.rssi_info[device.address] = advertisement.rssi
            return super()._detection_callback(device, advertisement)

        def callback(self, ble_device: BLEDevice, raw_data: bytes):
            logger.debug("BLE payload from %s: %s", ble_device.address.lower(), raw_data.hex())
            if generic := self.device_handler.get_generic_device(ble_device, raw_data):
                self.victron_mqtt_handler.publish(
                    ble_device=ble_device,
                    raw_data=raw_data,
                    generic_device=generic,
                    rssi=self.rssi_info.get(ble_device.address),
                    mqtt_client=self.mqtt_client,
                )
            else:
                logger.warning("Unsupported: %s (%s)", ble_device.name, ble_device.address)

    async def _run():
        scanner = MqttPublisher(keys=keys)
        await scanner.start()

    loop = asyncio.get_event_loop()
    loop.create_task(_run())
    loop.run_forever()


if __name__ == "__main__":
    main()
