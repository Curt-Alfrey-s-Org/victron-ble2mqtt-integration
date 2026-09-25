import types
from pathlib import Path
from unittest.mock import Mock

from paho.mqtt.client import MQTTMessageInfo
from paho.mqtt.enums import MQTTErrorCode


class _FakeMainMqttDevice:
    """Avoid ha-services psutil temperature probes in unit tests."""

    def __init__(self, **kwargs):
        pass

    def poll_and_publish(self, *_args, **_kwargs):
        return None


def test_calc_midpoint_shift_and_percent():
    from victron_ble2mqtt.mqtt import calc_midpoint_shift, calc_midpoint_shift_percent

    assert calc_midpoint_shift(100, 50) == 0.0
    assert round(calc_midpoint_shift(26.7, 13.2), 3) == 0.15

    assert calc_midpoint_shift_percent(100, 50) == 0.0
    assert round(calc_midpoint_shift_percent(26.7, 13.2), 3) == 1.124
    assert calc_midpoint_shift_percent(100, 51) == 2.0


def test_victron_mqtt_device_handler_publish_uses_handler_map(monkeypatch):
    """Verify VictronMqttDeviceHandler creates a handler and calls its publish method.
    We patch `get_handler` to return a DummyHandler class that records publish calls.
    """
    import victron_ble2mqtt
    from victron_ble2mqtt.mqtt import VictronMqttDeviceHandler
    from victron_ble2mqtt.user_settings import UserSettings

    calls = {}

    class DummyHandler:
        def __init__(self, *, ble_device, main_mqtt_device, victron_device, mqtt_client, user_settings):
            self.ble_device = ble_device
            self.main_mqtt_device = main_mqtt_device
            self.victron_device = victron_device
            self.mqtt_client = mqtt_client
            self.user_settings = user_settings
            calls['constructed'] = True

        def publish(self, *, data_dict, rssi):
            calls['published'] = True
            calls['data_dict'] = data_dict
            calls['rssi'] = rssi
            return True

    # Patch get_handler where publish() resolves it (implementation lives under override/).
    monkeypatch.setattr('override.victron_ble2mqtt.mqtt.get_handler', lambda victron_device: DummyHandler)
    monkeypatch.setattr('override.victron_ble2mqtt.mqtt.MainMqttDevice', _FakeMainMqttDevice)

    us = UserSettings()
    handler = VictronMqttDeviceHandler(user_settings=us)

    # Create a fake BLEDevice-like object
    FakeBLE = types.SimpleNamespace(address='AA:BB:CC:DD:EE:FF', name='FAKE')

    # Create a fake generic_device with a victron_device type and a parse() method
    class FakeGenericDevice:
        def __init__(self):
            self.victron_device = object()

        def parse(self, raw_data: bytes):
            return {'model_name': 'FAKE', 'voltage': 12.3}

    fake_generic = FakeGenericDevice()
    fake_mqtt_client = Mock()

    assert handler.publish(
        ble_device=FakeBLE,
        raw_data=b'\x01\x02',
        generic_device=fake_generic,
        rssi=-70,
        mqtt_client=fake_mqtt_client,
    ) is True
    assert calls.get('constructed') is True
    assert calls.get('published') is True
    assert calls.get('data_dict') == {'model_name': 'FAKE', 'voltage': 12.3}
    assert calls.get('rssi') == -70


def test_mqtt_publish_results_ok_requires_success_rc():
    from override.victron_ble2mqtt.mqtt import _mqtt_publish_results_ok

    ok_info = MQTTMessageInfo(mid=1)
    ok_info.rc = MQTTErrorCode.MQTT_ERR_SUCCESS
    bad_info = MQTTMessageInfo(mid=2)
    bad_info.rc = MQTTErrorCode.MQTT_ERR_NO_CONN

    assert _mqtt_publish_results_ok((None, ok_info)) is True
    assert _mqtt_publish_results_ok((ok_info, ok_info)) is True
    assert _mqtt_publish_results_ok((None, bad_info)) is False
    assert _mqtt_publish_results_ok((None, None)) is False


def test_victron_mqtt_device_handler_publish_returns_false_on_handler_failure(monkeypatch):
    from victron_ble2mqtt.mqtt import VictronMqttDeviceHandler
    from victron_ble2mqtt.user_settings import UserSettings

    class FailingHandler:
        def __init__(self, **kwargs):
            pass

        def publish(self, *, data_dict, rssi):
            return False

    monkeypatch.setattr('override.victron_ble2mqtt.mqtt.get_handler', lambda victron_device: FailingHandler)
    monkeypatch.setattr('override.victron_ble2mqtt.mqtt.MainMqttDevice', _FakeMainMqttDevice)

    handler = VictronMqttDeviceHandler(user_settings=UserSettings())

    FakeBLE = types.SimpleNamespace(address='AA:BB:CC:DD:EE:FF', name='FAKE')

    class FakeGenericDevice:
        def __init__(self):
            self.victron_device = object()

        def parse(self, raw_data: bytes):
            return {'model_name': 'FAKE', 'voltage': 12.3}

    assert handler.publish(
        ble_device=FakeBLE,
        raw_data=b'\x01\x02',
        generic_device=FakeGenericDevice(),
        rssi=-70,
        mqtt_client=Mock(),
    ) is False


def test_main_imports_override_mqtt():
    """Entrypoint must load sibling mqtt.py, not /app/victron_ble2mqtt/mqtt.py."""
    src = (Path(__file__).resolve().parents[1] / "override/victron_ble2mqtt/__main__.py").read_text(
        encoding="utf-8"
    )
    assert "from .mqtt import VictronMqttDeviceHandler" in src
    assert "from victron_ble2mqtt.mqtt import VictronMqttDeviceHandler" not in src
    assert "from .instant_readout import prepare_seen_data_for_republish" in src
    # victron-ble 0.9.3 calls callback(device, data, advertisement); the old
    # two-argument override raised TypeError on every advertisement.
    assert "def callback(self, ble_device: BLEDevice, raw_data: bytes):" not in src
    assert "raw_data: bytes,\n        advertisement: AdvertisementData | None = None," in src
    assert "advertisement.rssi" in src
    assert "asyncio.to_thread" in src
    assert "or_patterns" in src
    assert "MANUFACTURER_SPECIFIC_DATA" in src
    assert "BLE scanner started" in src
    assert "touch_scanner_ok" in src
    assert "touch_ble_publish_heartbeat" in src
    assert "BLE publish heartbeat not updated" in src
    assert "prepare_seen_data_for_republish" in src


def test_compose_sets_pythonsafepath():
    src = (Path(__file__).resolve().parents[1] / "docker-compose.victron.yml").read_text(
        encoding="utf-8"
    )
    assert "PYTHONSAFEPATH=1" in src
    assert "SYSTEM_POLL_THROTTLE_SEC=${SYSTEM_POLL_THROTTLE_SEC:-60}" in src
    assert "BLE_PUBLISH_MAX_AGE_SEC=${BLE_PUBLISH_MAX_AGE_SEC:-600}" in src
    assert "from victron_ble2mqtt.liveness import check" in src


def test_victronconnect_sensor_names():
    """MQTT discovery names follow VictronConnect readout wording; uids stay stable."""
    src = (Path(__file__).resolve().parents[1] / "override/victron_ble2mqtt/mqtt.py").read_text(
        encoding="utf-8"
    )
    assert 'name="Battery voltage"' in src
    assert 'name="Battery current"' in src
    assert 'name="State of charge"' in src
    assert 'name="Consumed Ah"' in src
    assert 'name="Time remaining"' in src
    assert 'name="Aux input reading"' in src
    assert 'name="Midpoint voltage"' in src
    assert 'name="Midpoint voltage deviation"' in src
    assert 'name="Solar power"' in src
    assert 'name="Solar yield"' in src
    assert 'name="Battery state"' in src
    assert 'name="Load output"' in src
    assert 'name="Load output power"' in src
    assert 'uid="voltage"' in src
    assert 'uid="soc"' in src
    assert 'uid="yield_today"' in src
    assert 'name="Auxiliary Mode"' not in src
    assert 'name="Charge State"' not in src
    assert 'name="Yield Today"' not in src
    assert "poll_and_publish" not in src
    assert "sensor.retain = True" in src
