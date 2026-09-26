"""Review 2026-09-26 regression tests (no BlueZ, no MQTT broker, no HA)."""

from __future__ import annotations

import asyncio
import importlib
import types
from unittest.mock import Mock

import pytest
from victron_ble import scanner as victron_scanner

VICTRON_COMPANY_ID = 0x02E1


@pytest.fixture
def main_mod(monkeypatch):
    mod = importlib.import_module("override.victron_ble2mqtt.__main__")
    monkeypatch.setattr(victron_scanner, "BleakScanner", Mock())
    monkeypatch.setattr(mod, "DeviceHandler", lambda keys: Mock())
    monkeypatch.setattr(mod, "VictronMqttDeviceHandler", lambda *, user_settings: Mock())
    return mod


def test_rssi_cache_ignores_non_victron_devices(main_mod):
    settings = types.SimpleNamespace(mqtt=types.SimpleNamespace())
    pub = main_mod.MqttPublisher(keys=[], user_settings=settings, mqtt_client=Mock())
    for i in range(50):  # e.g. phones rotating random addresses during active scan
        device = types.SimpleNamespace(address=f"7A:00:00:00:00:{i:02X}", name=None)
        pub._detection_callback(device, types.SimpleNamespace(rssi=-80, manufacturer_data={}))
    assert pub._last_rssi == {}


class _FakeIface:
    def __init__(self, objects):
        self._objects = objects

    async def call_get_managed_objects(self):
        return self._objects


class _FakeBus:
    def __init__(self, objects):
        self.objects = objects

    async def introspect(self, _service, _path):
        return None

    def get_proxy_object(self, _service, _path, _node):
        bus = self
        return types.SimpleNamespace(get_interface=lambda _name: _FakeIface(bus.objects))


def _dev(address):
    return {"org.bluez.Device1": {"Address": address, "ManufacturerData": {}}}


def test_h5082_discover_picks_up_plugs_that_appear_later(monkeypatch):
    govee_main = pytest.importorskip("govee_h5082.__main__")
    from govee_h5082.mqtt_bridge import PLUGS

    bridge = object.__new__(govee_main.Bridge)  # no MQTT / key file needed
    bridge._paths = {}
    first, second = PLUGS[0][0], PLUGS[1][0]
    path = lambda a: f"/org/bluez/hci1/dev_{a.replace(':', '_')}"  # noqa: E731
    bus = _FakeBus({path(first): _dev(first)})
    asyncio.run(bridge.discover(bus))
    assert set(bridge._paths) == {first}

    # Second plug shows up in BlueZ later; hci0 devices are still ignored.
    bus.objects[path(second)] = _dev(second)
    bus.objects["/org/bluez/hci0/dev_X"] = _dev(PLUGS[2][0])
    asyncio.run(bridge.discover(bus))
    assert set(bridge._paths) == {first, second}

    # A plug BlueZ dropped is no longer polled.
    del bus.objects[path(first)]
    asyncio.run(bridge.discover(bus))
    assert set(bridge._paths) == {second}
