import types
from threading import Event
from unittest.mock import patch

import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.enums import CallbackAPIVersion

from victron_ble2mqtt.mqtt import VictronMqttDeviceHandler
from victron_ble2mqtt.user_settings import UserSettings

pytestmark = pytest.mark.usefixtures("ensure_mqtt_broker")


def _mqtt_reason_ok(reason_code) -> bool:
    """CONNACK/SUBACK success. ReasonCode.is_failure is True for values >= 0x80."""
    is_failure = getattr(reason_code, "is_failure", None)
    if isinstance(is_failure, bool):
        return not is_failure
    try:
        return int(reason_code) < 0x80
    except (TypeError, ValueError):
        return False


def _reason_codes(reason_codes):
    if isinstance(reason_codes, (list, tuple)):
        return reason_codes
    return (reason_codes,)


def _mqtt_client(on_connect, on_subscribe=None, on_message=None):
    """Connect and start the network loop. Caller waits on the callback events."""
    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    if on_subscribe is not None:
        client.on_subscribe = on_subscribe
    if on_message is not None:
        client.on_message = on_message
    client.connect('localhost', 1883, 60)
    client.loop_start()
    return client


def test_victron_handler_publishes_to_broker():
    """Integration test: VictronMqttDeviceHandler publishes fallback sensor state.

    Requires Mosquitto on localhost:1883 (CI starts it). FallbackHandler does not
    call poll_and_publish; it publishes RSSI and parsed fields other than model_name.
    This fake device therefore emits state payloads -55 and 12.34.
    """
    received = Event()
    messages = []
    subscribed = Event()
    publisher_connected = Event()

    def on_connect(client, userdata, flags, reason_code, properties=None):
        # subscribe() before CONNACK returns MQTT_ERR_NO_CONN and is not queued.
        if _mqtt_reason_ok(reason_code):
            client.subscribe('#')

    def on_subscribe(client, userdata, mid, reason_codes, properties=None):
        codes = _reason_codes(reason_codes)
        if codes and all(_mqtt_reason_ok(code) for code in codes):
            subscribed.set()

    def on_message(client, userdata, msg):
        messages.append((msg.topic, msg.payload.decode(errors='ignore')))
        received.set()

    def on_publisher_connect(client, userdata, flags, reason_code, properties=None):
        if _mqtt_reason_ok(reason_code):
            publisher_connected.set()

    sub = _mqtt_client(on_connect, on_subscribe, on_message)
    client = None
    published = False
    ok = False
    try:
        assert subscribed.wait(timeout=5.0), 'subscriber did not receive SUBACK before publish'
        handler = VictronMqttDeviceHandler(user_settings=UserSettings())
        client = _mqtt_client(on_publisher_connect)
        assert publisher_connected.wait(timeout=5.0), 'publisher client did not receive CONNACK'
        # poll_and_publish is the system-info loop, not device state.
        with patch.object(handler.main_mqtt_device, 'poll_and_publish', lambda *_a, **_k: None):
            published = handler.publish(
                ble_device=types.SimpleNamespace(address='AA:BB:CC:11:22:33', name='FAKE'),
                raw_data=b'\x00\x01',
                generic_device=_FakeGeneric(),
                rssi=-55,
                mqtt_client=client,
            )
        ok = received.wait(timeout=5.0)
    finally:
        if client is not None:
            client.loop_stop()
            client.disconnect()
        sub.loop_stop()
        sub.disconnect()

    assert published is True
    assert ok is True, 'No MQTT messages seen from VictronMqttDeviceHandler'
    assert len(messages) > 0
    assert any(payload in ('-55', '12.34') for _topic, payload in messages)


class _FakeGeneric:
    def __init__(self):
        # Plain object: not a BatteryMonitor or SolarCharger, so FallbackHandler is used.
        self.victron_device = object()

    def parse(self, raw_data):
        return {'model_name': 'FAKE', 'voltage': 12.34}
