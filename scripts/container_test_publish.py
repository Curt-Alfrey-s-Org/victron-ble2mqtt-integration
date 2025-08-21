"""Run inside the built container (with the repo mounted at /work).

This script publishes a single test message to the broker (topic `victron/test`).
"""
import os
import time
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')

client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
client.connect(MQTT_HOST, 1883, 60)
client.loop_start()

# Give broker a small moment
time.sleep(0.2)
client.publish('victron/test', payload='integration-ok', qos=0)

time.sleep(0.2)
client.loop_stop()
client.disconnect()
print('published')
