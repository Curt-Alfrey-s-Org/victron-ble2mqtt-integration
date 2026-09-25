#!/usr/bin/env bash
# Container entrypoint for victron_ble2mqtt.
#
# Configuration comes from the Python settings under override/victron_ble2mqtt
# (user_settings_data.py holds the device list, no secrets) plus environment
# variables: MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASSWORD and ADVKEY_* keys.
# The app validates required secrets at startup and exits with a clear error
# naming any missing variable (see _required_secret_errors in __main__.py).
#
# The previous version parsed /app/user_settings.example.py (not in the image)
# and wrote /work/victron_ble2mqtt/user_settings.py, which is never imported:
# PYTHONPATH puts the override package first, so that file was dead code.
set -euo pipefail
exec python -m victron_ble2mqtt.__main__
