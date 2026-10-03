from threading import Event

import paho.mqtt.client as mqtt
import pytest
from paho.mqtt.enums import CallbackAPIVersion, MQTTErrorCode

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


def test_mqtt_broker_publish_subscribe():
    """Integration: ensure a local MQTT broker accepts publishes and delivers messages.

    This test requires a Mosquitto broker running on localhost:1883. The CI job will
    start a Mosquitto service for this purpose.
    """
    received = Event()
    subscribed = Event()
    payloads = []

    def on_connect(client, userdata, flags, reason_code, properties=None):
        # subscribe() before CONNACK returns MQTT_ERR_NO_CONN and is not queued.
        if _mqtt_reason_ok(reason_code):
            client.subscribe('victron/test')

    def on_subscribe(client, userdata, mid, reason_codes, properties=None):
        codes = reason_codes if isinstance(reason_codes, (list, tuple)) else (reason_codes,)
        if codes and all(_mqtt_reason_ok(code) for code in codes):
            subscribed.set()

    def on_message(client, userdata, msg):
        payloads.append(msg.payload.decode())
        received.set()

    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_subscribe = on_subscribe
    client.on_message = on_message

    client.connect('localhost', 1883, 60)
    client.loop_start()
    try:
        assert subscribed.wait(timeout=5.0), 'subscriber did not receive SUBACK before publish'
        info = client.publish('victron/test', payload='integration-ok', qos=0)
        assert info.rc == MQTTErrorCode.MQTT_ERR_SUCCESS
        ok = received.wait(timeout=5.0)
    finally:
        client.loop_stop()
        client.disconnect()

    assert ok is True
    assert 'integration-ok' in payloads
