"""Entry point: read VE.Direct Text from USB and publish read-only HA MQTT."""

from __future__ import annotations

import os
import signal
import sys
import time

import serial

from .config import load_settings
from .mqtt_ha import MqttHaPublisher
from .vedirect_text import VeDirectTextParser, fields_to_metrics

# Official serial settings: 19200 8N1, no flow control.
# https://www.victronenergy.com/upload/documents/VE.Direct-Protocol-3.34.pdf
# https://pyserial.readthedocs.io/en/latest/pyserial_api.html#serial.Serial


def main() -> int:
    settings = load_settings()
    print(
        f"bms_supervisor: adapter={settings.adapter} bank={settings.bank_id} "
        f"device={settings.serial_device} topic={settings.mqtt_topic}"
    )

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

    parser = VeDirectTextParser()
    ser: serial.Serial | None = None
    reconnect_delay = 2.0

    while running:
        if ser is None or not ser.is_open:
            try:
                ser = serial.Serial(
                    port=settings.serial_device,
                    baudrate=19200,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1.0,
                    write_timeout=0,
                )
                print(f"Serial open: {settings.serial_device}")
                reconnect_delay = 2.0
            except serial.SerialException as exc:
                print(f"Serial open failed: {exc} -- retry in {reconnect_delay:.0f}s")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60.0)
                continue

        try:
            waiting = ser.in_waiting
            chunk = ser.read(waiting if waiting > 0 else 1)
        except serial.SerialException as exc:
            print(f"Serial read error: {exc}")
            try:
                ser.close()
            except serial.SerialException:
                pass
            ser = None
            time.sleep(reconnect_delay)
            continue

        if not chunk:
            continue

        for fields in parser.feed(chunk):
            metrics = fields_to_metrics(fields)
            if mqtt_pub.publish_metrics(metrics):
                try:
                    with open(settings.heartbeat_file, "a", encoding="utf-8"):
                        pass
                    os.utime(settings.heartbeat_file, None)
                except OSError as exc:
                    print(f"Heartbeat touch failed: {exc}")

    if ser is not None and ser.is_open:
        ser.close()
    mqtt_pub.client.loop_stop()
    mqtt_pub.client.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
