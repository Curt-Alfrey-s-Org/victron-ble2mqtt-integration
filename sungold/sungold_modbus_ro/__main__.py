"""Entry point: poll SRNE registers and publish read-only HA MQTT discovery."""

from __future__ import annotations

import os
import signal
import sys
import time

from .config import load_settings
from .modbus_io import ReadOnlyModbusClient
from .mqtt_ha import MqttHaPublisher
from .reconcile import reconcile_battery_current
from .registers import CURATED_ENTITIES


def touch_heartbeat(path: str) -> None:
    with open(path, "a", encoding="utf-8"):
        pass
    os.utime(path, None)


def run_poll_cycle(modbus: ReadOnlyModbusClient, mqtt_pub: MqttHaPublisher) -> bool:
    published_any = False
    values: dict[str, str] = {}
    for entity in CURATED_ENTITIES:
        if not modbus.is_register_available(entity.register):
            continue
        value = modbus.read_entity(entity)
        if value is None:
            continue
        values[entity.key] = value

    fixed = reconcile_battery_current(
        values.get("inverter/charging_power"),
        values.get("battery/voltage"),
        values.get("battery/current"),
    )
    if fixed is not None:
        values["battery/current"] = fixed

    for entity in CURATED_ENTITIES:
        value = values.get(entity.key)
        if value is None:
            continue
        if mqtt_pub.publish_state(entity, value):
            published_any = True
    return published_any


def main() -> int:
    settings = load_settings()
    print(
        f"sungold_modbus_ro: address={settings.modbus_address} "
        f"device={settings.modbus_device} topic={settings.mqtt_topic}"
    )

    modbus = ReadOnlyModbusClient(settings)
    mqtt_pub = MqttHaPublisher(settings)
    mqtt_pub.connect_with_retry()
    mqtt_pub.client.loop_start()

    running = True

    def _stop(signum, frame) -> None:
        nonlocal running
        print("\nShutdown requested")
        running = False

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    time.sleep(1.0)

    while running:
        if run_poll_cycle(modbus, mqtt_pub):
            try:
                touch_heartbeat(settings.heartbeat_file)
            except OSError as exc:
                print(f"Heartbeat touch failed: {exc}")

        modbus.check_reconnect()
        time.sleep(settings.poll_interval_sec)

    mqtt_pub.client.loop_stop()
    mqtt_pub.client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
