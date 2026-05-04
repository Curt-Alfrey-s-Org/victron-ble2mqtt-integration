import time
from threading import Event
import types
from unittest.mock import patch


def test_victron_handler_publishes_to_broker():
    """Integration test: instantiate VictronMqttDeviceHandler and verify it publishes to the broker.

    This requires a Mosquitto broker running on localhost:1883 (CI provides this service).
    """
    import paho.mqtt.client as mqtt
    from paho.mqtt.enums import CallbackAPIVersion

    # Prepare MQTT subscriber to capture any published messages
    received = Event()
    messages = []

    from threading import Event as _Event
    connected = _Event()
    subscribed = _Event()

    def on_connect(client, userdata, flags, reason_code, properties=None):
        connected.set()
        client.subscribe('#')

    def on_subscribe(client, userdata, mid, reason_codes, properties=None):
        subscribed.set()

    def on_message(client, userdata, msg):
        messages.append((msg.topic, msg.payload.decode(errors='ignore')))
        received.set()

    sub = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    sub.on_message = on_message
    sub.connect('localhost', 1883, 60)
    sub.loop_start()

    sub.subscribe('#')
    time.sleep(0.2)

    # Now create the Victron handler and publish a fake device message
    from victron_ble2mqtt.user_settings import UserSettings
    from victron_ble2mqtt.mqtt import VictronMqttDeviceHandler

    us = UserSettings()
    handler = VictronMqttDeviceHandler(user_settings=us)

    FakeBLE = types.SimpleNamespace(address='AA:BB:CC:11:22:33', name='FAKE')

    class FakeGeneric:
        def __init__(self):
            # Use a plain object for victron_device so handler will use fallback
            self.victron_device = object()

        def parse(self, raw_data):
            return {'model_name': 'FAKE', 'voltage': 12.34}

    fake_generic = FakeGeneric()

    import paho.mqtt.client as mqtt_client
    from paho.mqtt.enums import CallbackAPIVersion as _CAP
    client = mqtt_client.Client(callback_api_version=_CAP.VERSION2)
    client.connect('localhost', 1883, 60)
    client.loop_start()
    time.sleep(0.2)

    # Call publish - this should result in one or more MQTT publishes
    with patch.object(handler.main_mqtt_device, "poll_and_publish", lambda *_a, **_k: None):
        handler.publish(
            ble_device=FakeBLE,
            raw_data=b'\x00\x01',
            generic_device=fake_generic,
            rssi=-55,
            mqtt_client=client,
        )

    # Wait for messages
    ok = received.wait(timeout=5.0)

    client.loop_stop()
    client.disconnect()
    sub.loop_stop()
    sub.disconnect()

    assert ok is True, 'No MQTT messages seen from VictronMqttDeviceHandler'
    assert len(messages) > 0
