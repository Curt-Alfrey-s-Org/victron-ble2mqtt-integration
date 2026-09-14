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
import time
from typing import Any

from bleak import AdvertisementData, BleakScanner, BLEDevice
from paho.mqtt.client import Client as PahoClient
from paho.mqtt.enums import CallbackAPIVersion
from victron_ble.scanner import BaseScanner

# Same-package imports so `python -m` does not pick /app/victron_ble2mqtt/mqtt.py
# (WORKDIR /app prepends cwd onto sys.path unless PYTHONSAFEPATH is set).
# https://docs.python.org/3/reference/import.html#package-relative-imports
# https://docs.python.org/3/using/cmdline.html#envvar-PYTHONSAFEPATH
from .cli_app.settings import get_settings
from .instant_readout import prepare_seen_data_for_republish
from .mqtt import VictronMqttDeviceHandler
from .victron_ble_utils import DeviceHandler

# Liveness heartbeat: the publish loop touches this file after each successful
# system-info publish; the container healthcheck fails when it goes stale.
HEARTBEAT_FILE = os.getenv("HEARTBEAT_FILE", "/tmp/victron_ble2mqtt.heartbeat")

_module_logger = logging.getLogger(__name__)


def touch_heartbeat(path: str = HEARTBEAT_FILE) -> None:
    try:
        with open(path, "a"):
            os.utime(path, None)
    except OSError as e:
        _module_logger.warning("Cannot touch heartbeat file %s: %s", path, e)


def _build_mqtt_client(
    host: str, port: int, username: str | None, password: str | None
) -> PahoClient:
    client = PahoClient(callback_api_version=CallbackAPIVersion.VERSION2)
    if username:
        client.username_pw_set(username, password or "")
    client.connect(host, port)
    client.loop_start()
    return client


def _settings_to_keys(user_settings) -> list[dict[str, Any]]:
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
    uname = getattr(user_settings.mqtt, "user_name", None) or getattr(
        user_settings.mqtt, "username", None
    )
    paho = _build_mqtt_client(
        host=getattr(user_settings.mqtt, "host", "localhost"),
        port=int(getattr(user_settings.mqtt, "port", 1883)),
        username=uname,
        password=getattr(user_settings.mqtt, "password", None),
    )

    class MqttPublisher(BaseScanner):
        def __init__(self, *, keys: list[dict[str, Any]]):
            super().__init__()
            # USB BLE dongles are often hci1 while the Pi built-in is hci0; victron_ble's
            # BaseScanner defaults to BlueZ default adapter. Override via .env:
            #   BLE_ADAPTER=hci1   (or VICTRON_BLE_ADAPTER=hci1)
            # bleak 3.x: 'adapter=' kwarg is deprecated -> bluez={'adapter': ...}
            # (https://github.com/hbldh/bleak/blob/develop/CHANGELOG.rst, v3.0.0)
            self._ble_adapter = (os.getenv("BLE_ADAPTER") or os.getenv("VICTRON_BLE_ADAPTER") or "").strip()
            self._rebuild_scanner("passive")
            if self._ble_adapter:
                logger.info(
                    "BLE scanner using adapter %s (BLE_ADAPTER / VICTRON_BLE_ADAPTER)",
                    self._ble_adapter,
                )
            self.device_handler = DeviceHandler(keys)
            self.victron_mqtt_handler = VictronMqttDeviceHandler(user_settings=user_settings)
            self.mqtt_client = paho
            # Throttles
            self._last_pub: dict[str, float] = {}
            self._pub_gap = float(getattr(user_settings.mqtt, "publish_throttle_seconds", 3) or 3)
            self._log_gap = float(getattr(user_settings.mqtt, "log_throttle_seconds", 3) or 3)
            self._last_warn: dict[str, float] = {}
            self._last_rssi: dict[str, int | None] = {}
            # System info periodic publish interval (seconds). Default 60 so
            # iwconfig/CPU MQTT does not occupy the Bleak event loop.
            self._sys_poll_gap = float(
                getattr(user_settings.mqtt, "system_poll_throttle_seconds", 60) or 60
            )

        def _rebuild_scanner(self, scanning_mode: str) -> None:
            # Instant Readout is advertisement-only. Passive avoids a second
            # BlueZ StartDiscovery while Pi4 Theengs uses active scan on hci0.
            # https://bleak.readthedocs.io/en/stable/api/scanner.html
            scan_kwargs = {
                "detection_callback": self._detection_callback,
                "scanning_mode": scanning_mode,
            }
            if self._ble_adapter:
                scan_kwargs["bluez"] = {"adapter": self._ble_adapter}
            self._scanner = BleakScanner(**scan_kwargs)

        async def start_with_fallback(self) -> None:
            last_error: BaseException | None = None
            for mode in ("passive", "active"):
                self._rebuild_scanner(mode)
                logger.info("Starting BLE scanner scanning_mode=%s", mode)
                try:
                    await asyncio.wait_for(self.start(), timeout=30)
                except TimeoutError:
                    logger.error("BLE scanner start timed out after 30s (mode=%s)", mode)
                    try:
                        await self.stop()
                    except Exception:
                        logger.exception("BLE scanner stop failed after timeout")
                    last_error = TimeoutError(f"start timeout mode={mode}")
                    continue
                except Exception as exc:
                    logger.exception("BLE scanner failed to start (mode=%s)", mode)
                    last_error = exc
                    continue
                logger.info("BLE scanner started scanning_mode=%s", mode)
                return
            if last_error is not None:
                logger.error("BLE scanner could not start in passive or active mode")

        async def periodic_system_info_publish(self) -> None:
            """Publish Pi4 system info on a fixed interval regardless of BLE traffic.

            poll_and_publish runs iwconfig and many MQTT config publishes. Run it
            in a worker thread so Bleak can still deliver Instant Readout ads.
            https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread
            """
            while True:
                try:
                    await asyncio.to_thread(
                        self.victron_mqtt_handler.main_mqtt_device.poll_and_publish,
                        self.mqtt_client,
                    )
                except Exception as e:
                    logger.warning("System info publish failed: %s", e)
                else:
                    if self.mqtt_client.is_connected():
                        touch_heartbeat()
                await asyncio.sleep(self._sys_poll_gap)

        def _detection_callback(self, device: BLEDevice, advertisement: AdvertisementData):
            # Bleak 0.19+ keeps RSSI on AdvertisementData, not BLEDevice.
            # https://bleak.readthedocs.io/en/latest/api/index.html
            self._last_rssi[device.address] = advertisement.rssi
            data = advertisement.manufacturer_data.get(0x02E1)
            if not data or not data.startswith(b"\x10"):
                return
            last = self._last_pub.get(device.address, 0.0)
            if not prepare_seen_data_for_republish(
                payload=data,
                seen_data=self._seen_data,
                last_pub=last,
                now=time.monotonic(),
                pub_gap=self._pub_gap,
            ):
                return
            super()._detection_callback(device, advertisement)

        # victron-ble 0.9.2 BaseScanner.callback(device, data)
        # https://github.com/keshavdv/victron-ble/blob/v0.9.2/victron_ble/scanner.py
        def callback(self, ble_device: BLEDevice, raw_data: bytes):
            try:
                self._callback_inner(ble_device, raw_data)
            except Exception:
                logger.exception("Victron BLE publish failed for %s", ble_device.address)

        def _callback_inner(self, ble_device: BLEDevice, raw_data: bytes):
            now = time.monotonic()
            # Rate-limit noisy debug
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("BLE payload from %s: %s", ble_device.address.lower(), raw_data.hex())
            if generic := self.device_handler.get_generic_device(ble_device, raw_data):
                last = self._last_pub.get(ble_device.address, 0.0)
                if (now - last) >= self._pub_gap:
                    self._last_pub[ble_device.address] = now
                    self.victron_mqtt_handler.publish(
                        ble_device=ble_device,
                        raw_data=raw_data,
                        generic_device=generic,
                        rssi=self._last_rssi.get(ble_device.address),
                        mqtt_client=self.mqtt_client,
                    )
                else:
                    # Occasionally log that we skipped (throttled)
                    lw = self._last_warn.get(ble_device.address, 0.0)
                    if (now - lw) >= self._log_gap:
                        self._last_warn[ble_device.address] = now
                        logger.info(
                            "Throttled publish for %s (gap %.1fs)",
                            ble_device.address,
                            self._pub_gap,
                        )
            else:
                lw = self._last_warn.get(ble_device.address + ":unsupported", 0.0)
                if (now - lw) >= self._log_gap:
                    self._last_warn[ble_device.address + ":unsupported"] = now
                    logger.warning("Unsupported: %s (%s)", ble_device.name, ble_device.address)

    async def _run():
        scanner = MqttPublisher(keys=keys)
        # System-info in the background; do not block BLE start on iwconfig.
        asyncio.create_task(scanner.periodic_system_info_publish())
        await scanner.start_with_fallback()

    loop = asyncio.get_event_loop()
    loop.create_task(_run())
    loop.run_forever()


if __name__ == "__main__":
    main()
