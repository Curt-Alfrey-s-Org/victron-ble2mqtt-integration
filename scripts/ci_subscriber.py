"""CI helper: subscribe to a single MQTT topic and write payload to a temp file.

Usage: set env MQTT_HOST (default localhost), and run. Exits after first message or timeout.
"""
import os
import time
from threading import Event

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')
TOPIC = os.getenv('CI_MQTT_TOPIC', 'victron/test')
OUTFILE = os.getenv('CI_MQTT_OUT', '/tmp/ci_mqtt_received.txt')
TIMEOUT = int(os.getenv('CI_MQTT_TIMEOUT', '10'))

received = Event()
payload = None


def on_connect(client, userdata, flags, rc):
    client.subscribe(TOPIC)


def on_message(client, userdata, msg):
    global payload
    payload = msg.payload.decode(errors='ignore')
    with open(OUTFILE, 'w') as f:
        f.write(payload)
    received.set()


client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_HOST, 1883, 60)
client.loop_start()

ok = received.wait(timeout=TIMEOUT)
client.loop_stop()
client.disconnect()

if not ok:
    print('No message received within timeout')
    raise SystemExit(1)

print('Wrote payload to', OUTFILE)
