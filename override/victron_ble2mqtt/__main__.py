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
import re
import time
from typing import Any

from bleak import AdvertisementData, BleakScanner, BLEDevice
from bleak.assigned_numbers import AdvertisementDataType
from paho.mqtt.client import Client as PahoClient
from paho.mqtt.enums import CallbackAPIVersion
from victron_ble.scanner import BaseScanner

# Same-package imports so `python -m` does not pick /app/victron_ble2mqtt/mqtt.py
# (WORKDIR /app prepends cwd onto sys.path unless PYTHONSAFEPATH is set).
# https://docs.python.org/3/reference/import.html#package-relative-imports
# https://docs.python.org/3/using/cmdline.html#envvar-PYTHONSAFEPATH
from .cli_app.settings import get_settings
from .instant_readout import prepare_seen_data_for_republish
from .liveness import (
    remove_file,
    touch_ble_publish_heartbeat,
    touch_scanner_ok,
    touch_system_heartbeat,
)
from .mqtt import VictronMqttDeviceHandler
from .victron_ble_utils import DeviceHandler

_module_logger = logging.getLogger(__name__)


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


def _advkey_env_name(device: dict[str, Any]) -> str:
    # Same slug rule as user_settings_data.py (ADVKEY_<NAME_SLUG>).
    label = device.get("name") or device.get("type") or device.get("mac") or ""
    return "ADVKEY_" + re.sub(r"[^A-Za-z0-9]+", "_", str(label).strip()).strip("_").upper()


def _required_secret_errors(user_settings, keys: list[dict[str, Any]]) -> list[str]:
    """Return one message per required secret that is missing (empty list = OK).

    - MQTT_PASSWORD is required whenever MQTT_USER is set (no anonymous fallback
      with a username and an empty password).
    - At least one configured device needs an advertisement key (ADVKEY_*),
      otherwise nothing can be decrypted and the bridge would publish nothing.
    """
    errors: list[str] = []
    mqtt = user_settings.mqtt
    uname = getattr(mqtt, "user_name", None) or getattr(mqtt, "username", None)
    if uname and not getattr(mqtt, "password", None):
        errors.append("MQTT_PASSWORD is empty but MQTT_USER is set")
    if keys and not any(str(k.get("advertisement_key") or "").strip() for k in keys):
        expected = ", ".join(_advkey_env_name(k) for k in keys)
        errors.append(f"no advertisement key set for any configured device (set {expected})")
    return errors


class MqttPublisher(BaseScanner):
    def __init__(
        self,
        *,
        keys: list[dict[str, Any]],
        user_settings: Any,
        mqtt_client: PahoClient,
    ):
        super().__init__()
        # USB BLE dongles are often hci1 while the Pi built-in is hci0; victron_ble's
        # BaseScanner defaults to BlueZ default adapter. Override via .env:
        #   BLE_ADAPTER=hci1   (or VICTRON_BLE_ADAPTER=hci1)
        # bleak 3.x: 'adapter=' kwarg is deprecated -> bluez={'adapter': ...}
        # (https://github.com/hbldh/bleak/blob/develop/CHANGELOG.rst, v3.0.0)
        self._ble_adapter = (os.getenv("BLE_ADAPTER") or os.getenv("VICTRON_BLE_ADAPTER") or "").strip()
        if self._ble_adapter:
            _module_logger.info(
                "BLE scanner using adapter %s (BLE_ADAPTER / VICTRON_BLE_ADAPTER)",
                self._ble_adapter,
            )
        self.device_handler = DeviceHandler(keys)
        self.victron_mqtt_handler = VictronMqttDeviceHandler(user_settings=user_settings)
        self.mqtt_client = mqtt_client
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
        # Instant Readout is advertisement-only. Passive uses BlueZ
        # AdvertisementMonitor. Pi4 onboard HCI is exclusive to this scanner
        # unless BLE_ADAPTER is a different adapter than THEENGS_ADAPTER.
        # BlueZ: one StartDiscovery session per client per adapter
        # https://manpages.ubuntu.com/manpages/noble/man5/org.bluez.Adapter.5.html
        # Passive requires or_patterns:
        # https://bleak.readthedocs.io/en/latest/api/args.html
        # https://github.com/bluez/bluez/blob/master/doc/org.bluez.AdvertisementMonitor.rst
        # Manufacturer Specific Data 0xFF; Victron company id 0x02E1 LE.
        scan_kwargs = {
            "detection_callback": self._detection_callback,
            "scanning_mode": scanning_mode,
        }
        bluez: dict[str, Any] = {}
        if self._ble_adapter:
            bluez["adapter"] = self._ble_adapter
        if scanning_mode == "passive":
            bluez["or_patterns"] = [
                (0, AdvertisementDataType.MANUFACTURER_SPECIFIC_DATA, bytes((0xE1, 0x02))),
            ]
        if bluez:
            scan_kwargs["bluez"] = bluez
        self._scanner = BleakScanner(**scan_kwargs)

    async def start_with_fallback(self) -> bool:
        last_error: BaseException | None = None
        for mode in ("passive", "active"):
            _module_logger.info("Starting BLE scanner scanning_mode=%s", mode)
            try:
                self._rebuild_scanner(mode)
                await asyncio.wait_for(self.start(), timeout=30)
            except TimeoutError:
                _module_logger.error("BLE scanner start timed out after 30s (mode=%s)", mode)
                try:
                    await self.stop()
                except Exception:
                    _module_logger.exception("BLE scanner stop failed after timeout")
                last_error = TimeoutError(f"start timeout mode={mode}")
                continue
            except Exception as exc:
                _module_logger.exception("BLE scanner failed to start (mode=%s)", mode)
                last_error = exc
                continue
            _module_logger.info("BLE scanner started scanning_mode=%s", mode)
            try:
                touch_scanner_ok()
            except OSError as e:
                _module_logger.warning("Cannot touch scanner ok file: %s", e)
            return True
        if last_error is not None:
            _module_logger.error("BLE scanner could not start in passive or active mode")
        return False

    async def start_scanner_with_retry(self) -> None:
        retry_sec = float(os.getenv("BLE_SCANNER_START_RETRY_SEC") or 15)
        while True:
            if await self.start_with_fallback():
                return
            _module_logger.error(
                "BLE scanner start failed; retry in %.0fs. Another BlueZ client "
                "on this adapter can timeout Bleak (StartDiscovery is per client "
                "per adapter: https://manpages.ubuntu.com/manpages/noble/man5/org.bluez.Adapter.5.html). "
                "Pi4 Theengs must not share this HCI; ENABLE_PI4_THEENGS=1 only with "
                "THEENGS_ADAPTER different from BLE_ADAPTER.",
                retry_sec,
            )
            await asyncio.sleep(retry_sec)

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
                _module_logger.warning("System info publish failed: %s", e)
            else:
                if self.mqtt_client.is_connected():
                    try:
                        touch_system_heartbeat()
                    except OSError as e:
                        _module_logger.warning("Cannot touch system heartbeat file: %s", e)
            await asyncio.sleep(self._sys_poll_gap)

    def _detection_callback(self, device: BLEDevice, advertisement: AdvertisementData):
        data = advertisement.manufacturer_data.get(0x02E1)
        if not data or not data.startswith(b"\x10"):
            return
        # Bleak 0.19+ keeps RSSI on AdvertisementData, not BLEDevice.
        # https://bleak.readthedocs.io/en/latest/api/index.html
        # Cache it only for Victron Instant Readout senders: in active-scan
        # fallback every nearby device (phones rotate random addresses) reaches
        # this callback, and caching all of them grew the dict without bound.
        self._last_rssi[device.address] = advertisement.rssi
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

    # victron-ble 0.9.3 BaseScanner._detection_callback calls
    # self.callback(device, data, advertisement) — three arguments. The old
    # two-argument override raised TypeError on every advertisement.
    # https://github.com/keshavdv/victron-ble/blob/v0.9.3/victron_ble/scanner.py
    def callback(
        self,
        ble_device: BLEDevice,
        raw_data: bytes,
        advertisement: AdvertisementData | None = None,
    ):
        try:
            self._callback_inner(ble_device, raw_data, advertisement)
        except Exception:
            _module_logger.exception("Victron BLE publish failed for %s", ble_device.address)

    def _callback_inner(
        self,
        ble_device: BLEDevice,
        raw_data: bytes,
        advertisement: AdvertisementData | None = None,
    ):
        now = time.monotonic()
        # Prefer RSSI from the AdvertisementData victron-ble hands us; fall back
        # to the value cached in _detection_callback.
        rssi = getattr(advertisement, "rssi", None)
        if rssi is None:
            rssi = self._last_rssi.get(ble_device.address)
        # Rate-limit noisy debug
        if _module_logger.isEnabledFor(logging.DEBUG):
            _module_logger.debug("BLE payload from %s: %s", ble_device.address.lower(), raw_data.hex())
        if generic := self.device_handler.get_generic_device(ble_device, raw_data):
            last = self._last_pub.get(ble_device.address, 0.0)
            if (now - last) >= self._pub_gap:
                self._last_pub[ble_device.address] = now
                if self.victron_mqtt_handler.publish(
                    ble_device=ble_device,
                    raw_data=raw_data,
                    generic_device=generic,
                    rssi=rssi,
                    mqtt_client=self.mqtt_client,
                ):
                    try:
                        touch_ble_publish_heartbeat()
                    except OSError as e:
                        _module_logger.warning("Cannot touch BLE publish heartbeat file: %s", e)
                else:
                    _module_logger.warning(
                        "Instant Readout MQTT publish failed for %s; BLE publish heartbeat not updated",
                        ble_device.address,
                    )
            else:
                # Occasionally log that we skipped (throttled)
                lw = self._last_warn.get(ble_device.address, 0.0)
                if (now - lw) >= self._log_gap:
                    self._last_warn[ble_device.address] = now
                    _module_logger.info(
                        "Throttled publish for %s (gap %.1fs)",
                        ble_device.address,
                        self._pub_gap,
                    )
        else:
            lw = self._last_warn.get(ble_device.address + ":unsupported", 0.0)
            if (now - lw) >= self._log_gap:
                self._last_warn[ble_device.address + ":unsupported"] = now
                _module_logger.warning("Unsupported: %s (%s)", ble_device.name, ble_device.address)


def main() -> None:
    # Logging level: from env LOG_LEVEL or default INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    try:
        level = getattr(logging, log_level, logging.INFO)
    except Exception:
        level = logging.INFO
    logging.basicConfig(level=level)
    logger = logging.getLogger(__name__)

    # Drop stale scanner_ok from a previous crash before BLE starts again.
    scanner_ok_path = os.getenv("BLE_SCANNER_OK_FILE", "/tmp/victron_ble2mqtt.scanner_ok")
    try:
        remove_file(scanner_ok_path)
    except OSError as e:
        _module_logger.warning("Cannot remove scanner ok file %s: %s", scanner_ok_path, e)

    # Load production settings (override/victron_ble2mqtt/user_settings*.py)
    user_settings = get_settings()

    # Build device keys list for the DeviceHandler
    keys = _settings_to_keys(user_settings)
    logger.info("victron_ble2mqtt starting with %d device entries", len(keys))

    # Fail fast with a clear message instead of running with missing secrets.
    errors = _required_secret_errors(user_settings, keys)
    if errors:
        for err in errors:
            logger.critical("Missing required configuration: %s", err)
        raise SystemExit("victron_ble2mqtt: missing required configuration: " + "; ".join(errors))

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

    # asyncio keeps only weak references to tasks: hold them here.
    # https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
    background: set[asyncio.Task] = set()

    async def _run():
        scanner = MqttPublisher(keys=keys, user_settings=user_settings, mqtt_client=paho)
        # System-info in the background; do not block BLE start on iwconfig.
        background.add(asyncio.create_task(scanner.periodic_system_info_publish()))
        await scanner.start_scanner_with_retry()

    def _startup_done(task: asyncio.Task) -> None:
        # A crash during startup used to leave the loop running with nothing
        # scanning (only the healthcheck noticed, minutes later). Stop instead so
        # the container restarts right away.
        if not task.cancelled() and task.exception() is not None:
            _module_logger.critical("victron_ble2mqtt startup failed", exc_info=task.exception())
            loop.stop()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    run_task = loop.create_task(_run())
    background.add(run_task)
    run_task.add_done_callback(_startup_done)
    loop.run_forever()
    if not run_task.cancelled() and run_task.done() and run_task.exception() is not None:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
