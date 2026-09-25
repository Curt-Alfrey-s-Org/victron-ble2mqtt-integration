"""Regression tests for the production entrypoint (override/victron_ble2mqtt/__main__.py).

victron-ble 0.9.3 calls ``BaseScanner.callback(device, data, advertisement)``
with three arguments. The production ``MqttPublisher.callback`` used to accept
only two, so every Instant Readout advertisement raised TypeError and nothing
was published. These tests drive the real victron-ble ``_detection_callback``.
"""

import importlib
import inspect
import types
from unittest.mock import Mock

import pytest
from victron_ble import scanner as victron_scanner

VICTRON_COMPANY_ID = 0x02E1


@pytest.fixture
def main_mod(monkeypatch):
    mod = importlib.import_module("override.victron_ble2mqtt.__main__")
    # BaseScanner.__init__ builds a BleakScanner; no BlueZ in unit tests.
    monkeypatch.setattr(victron_scanner, "BleakScanner", Mock())
    monkeypatch.setattr(mod, "touch_ble_publish_heartbeat", lambda: None)
    return mod


def _settings(**mqtt):
    base = {
        "publish_throttle_seconds": 3,
        "log_throttle_seconds": 3,
        "system_poll_throttle_seconds": 60,
        "username": None,
        "user_name": None,
        "password": None,
    }
    base.update(mqtt)
    return types.SimpleNamespace(mqtt=types.SimpleNamespace(**base))


def _publisher(mod, monkeypatch, calls):
    class FakeDeviceHandler:
        def __init__(self, keys):
            pass

        def get_generic_device(self, ble_device, raw_data):
            return object()

    class FakeMqttHandler:
        def __init__(self, *, user_settings):
            pass

        def publish(self, *, ble_device, raw_data, generic_device, rssi, mqtt_client):
            calls.append({"address": ble_device.address, "raw": raw_data, "rssi": rssi})
            return True

    monkeypatch.setattr(mod, "DeviceHandler", FakeDeviceHandler)
    monkeypatch.setattr(mod, "VictronMqttDeviceHandler", FakeMqttHandler)
    return mod.MqttPublisher(keys=[], user_settings=_settings(), mqtt_client=Mock())


def test_callback_signature_matches_victron_ble_base_scanner(main_mod):
    base_params = list(inspect.signature(victron_scanner.BaseScanner.callback).parameters)
    ours = inspect.signature(main_mod.MqttPublisher.callback)
    # Must accept exactly what victron-ble passes positionally.
    ours.bind(None, *(object() for _ in base_params[1:]))


def test_detection_callback_publishes_with_rssi(main_mod, monkeypatch):
    calls = []
    pub = _publisher(main_mod, monkeypatch, calls)
    device = types.SimpleNamespace(address="AA:BB:CC:11:22:33", name="Battery 1")
    payload = b"\x10\x02\xa3\xa3\x00"
    adv = types.SimpleNamespace(rssi=-71, manufacturer_data={VICTRON_COMPANY_ID: payload})

    # Goes through victron-ble's real BaseScanner._detection_callback -> callback(3 args)
    pub._detection_callback(device, adv)

    assert calls == [{"address": "AA:BB:CC:11:22:33", "raw": payload, "rssi": -71}]


def test_detection_callback_ignores_non_instant_readout(main_mod, monkeypatch):
    calls = []
    pub = _publisher(main_mod, monkeypatch, calls)
    device = types.SimpleNamespace(address="AA:BB:CC:11:22:33", name="x")
    adv = types.SimpleNamespace(rssi=-50, manufacturer_data={VICTRON_COMPANY_ID: b"\x01\x02"})
    pub._detection_callback(device, adv)
    assert calls == []


def test_required_secrets_ok(main_mod):
    keys = [{"name": "Battery 1", "type": "SmartShunt", "advertisement_key": "a" * 32}]
    assert main_mod._required_secret_errors(_settings(), keys) == []
    settings = _settings(username="victron", user_name="victron", password="x")
    assert main_mod._required_secret_errors(settings, keys) == []


def test_required_secrets_missing_mqtt_password(main_mod):
    keys = [{"name": "Battery 1", "advertisement_key": "a" * 32}]
    settings = _settings(username="victron", user_name="victron", password="")
    errors = main_mod._required_secret_errors(settings, keys)
    assert len(errors) == 1
    assert "MQTT_PASSWORD" in errors[0]


def test_required_secrets_missing_all_advertisement_keys(main_mod):
    keys = [
        {"name": "Battery 1", "type": "SmartShunt", "advertisement_key": None},
        {"name": "Solar-controller", "type": "BlueSolar", "advertisement_key": ""},
    ]
    errors = main_mod._required_secret_errors(_settings(), keys)
    assert len(errors) == 1
    assert "ADVKEY_BATTERY_1" in errors[0]
    assert "ADVKEY_SOLAR_CONTROLLER" in errors[0]


def test_main_exits_before_connecting_when_secrets_missing(main_mod, monkeypatch, tmp_path):
    monkeypatch.setenv("BLE_SCANNER_OK_FILE", str(tmp_path / "scanner_ok"))
    settings = _settings(username="victron", user_name="victron", password="")
    settings.devices = []
    monkeypatch.setattr(main_mod, "get_settings", lambda: settings)
    connect = Mock(side_effect=AssertionError("must not connect to MQTT"))
    monkeypatch.setattr(main_mod, "_build_mqtt_client", connect)
    with pytest.raises(SystemExit) as exc:
        main_mod.main()
    assert "MQTT_PASSWORD" in str(exc.value)
    connect.assert_not_called()
