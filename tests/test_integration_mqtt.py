import time
from threading import Event

def test_mqtt_broker_publish_subscribe():
    """Integration: ensure a local MQTT broker accepts publishes and delivers messages.

    This test requires a Mosquitto broker running on localhost:1883. The CI job will
    start a Mosquitto service for this purpose.
    """
    import paho.mqtt.client as mqtt
    from paho.mqtt.enums import CallbackAPIVersion

    received = Event()
    payloads = []

    def on_message(client, userdata, msg):
        payloads.append(msg.payload.decode())
        received.set()

    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    client.on_message = on_message

    client.connect('localhost', 1883, 60)
    client.loop_start()

    # Ensure subscription is registered before publishing
    client.subscribe('victron/test')
    time.sleep(0.2)
    client.publish('victron/test', payload='integration-ok', qos=0)

    # Wait up to 5s for message to be received
    ok = received.wait(timeout=5.0)

    client.loop_stop()
    client.disconnect()

    assert ok is True
    assert 'integration-ok' in payloads
