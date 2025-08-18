# NOTE: Example template for PUBLIC repo.
# HOW TO USE IN PRODUCTION:
#   1) Copy the relevant contents from this file into:
#        victron_ble2mqtt/user_settings.py
#   2) Do NOT hardcode secrets here; keep MQTT_* and ADVKEY_* in your .env files.
#   3) This example file is not used at runtime.


"""
user_settings.example.py

This file replaces the deprecated TOML configuration.
Copy this file to: `victron_ble2mqtt/user_settings.py` and edit as needed.
"""

# MQTT Configuration
mqtt_host = "localhost"
mqtt_port = 1883
mqtt_username = "your-username"
mqtt_password = "your-password"

# List of Victron BLE devices to monitor
devices = [
    {
        "mac": "XX:XX:XX:XX:XX:XX",  # Replace with actual MAC
        "type": "SmartShunt",
        "name": "Battery 1",
        "advertisement_key": "your_advertisement_key"
    },
    {
        "mac": "YY:YY:YY:YY:YY:YY",  # Replace with actual MAC
        "type": "BlueSolar",
        "name": "Solar 1",
        "advertisement_key": "your_advertisement_key"
    }
]

# Optional: Set the logging level
log_level = "INFO"
