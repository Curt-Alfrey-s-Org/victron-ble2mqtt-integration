"""
user_settings.example.py

This file replaces the deprecated TOML configuration.
Copy this file to: `victron_ble2mqtt/user_settings.py` and edit as needed.
"""

# MQTT Configuration
mqtt_host = "localhost"
mqtt_port = 1883
mqtt_username = "victron"
mqtt_password = "abc123"

# List of Victron BLE devices to monitor
devices = [
    {
        "mac": "d4:ef:fb:b3:d7:0c",  # Replace with actual MAC
        "type": "SmartShunt-T2",
        "name": "Battery 1",
        "advertisement_key": "296fda27259660db2caaac64c8f3be5e2"
    },
    {
        "mac": "d7:69:eb:1f:f8:3d",  # Replace with actual MAC
        "type": "BlueSolar",
        "name": "Solar-controller",
        "advertisement_key": "560ed0313eaf939c53b20fe911f3e5e8"
    },
    {
        "mac": "cb:0d:c2:0a:ae:0f",  # Replace with actual MAC
        "type": "SmartShunt-KU",
        "name": "Battery 2",
        "advertisement_key": "5f8c4f5346ea7934c4ef87bd1bd0734c"
    },
]

# Optional: Set the logging level
log_level = "INFO"
