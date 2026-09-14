import types
from pathlib import Path
from unittest.mock import Mock

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

    # Patch get_handler where publish() resolves it (implementation lives under override/).
    monkeypatch.setattr('override.victron_ble2mqtt.mqtt.get_handler', lambda victron_device: DummyHandler)

    us = UserSettings()
    handler = VictronMqttDeviceHandler(user_settings=us)
    # CI / dev hosts often lack `iwconfig`; skip system-info side effects in unit tests.
    monkeypatch.setattr(handler.main_mqtt_device, "poll_and_publish", lambda *_a, **_k: None)

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

    # Call publish; this should construct a DummyHandler and then call its publish
    handler.publish(
        ble_device=FakeBLE,
        raw_data=b'\x01\x02',
        generic_device=fake_generic,
        rssi=-70,
        mqtt_client=fake_mqtt_client,
    )

    assert calls.get('constructed') is True
    assert calls.get('published') is True
    assert calls.get('data_dict') == {'model_name': 'FAKE', 'voltage': 12.3}
    assert calls.get('rssi') == -70


def test_main_imports_override_mqtt():
    """Entrypoint must load sibling mqtt.py, not /app/victron_ble2mqtt/mqtt.py."""
    src = (Path(__file__).resolve().parents[1] / "override/victron_ble2mqtt/__main__.py").read_text(
        encoding="utf-8"
    )
    assert "from .mqtt import VictronMqttDeviceHandler" in src
    assert "from victron_ble2mqtt.mqtt import VictronMqttDeviceHandler" not in src
    assert "from .instant_readout import prepare_seen_data_for_republish" in src
    assert "def callback(self, ble_device: BLEDevice, raw_data: bytes):" in src
    assert "advertisement.rssi" in src
    assert "asyncio.to_thread" in src
    assert 'scanning_mode": scanning_mode' in src or "scanning_mode=scanning_mode" in src
    assert "BLE scanner started" in src
    assert "prepare_seen_data_for_republish" in src


def test_compose_sets_pythonsafepath():
    src = (Path(__file__).resolve().parents[1] / "docker-compose.victron.yml").read_text(
        encoding="utf-8"
    )
    assert "PYTHONSAFEPATH=1" in src
    assert "SYSTEM_POLL_THROTTLE_SEC=${SYSTEM_POLL_THROTTLE_SEC:-60}" in src


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
