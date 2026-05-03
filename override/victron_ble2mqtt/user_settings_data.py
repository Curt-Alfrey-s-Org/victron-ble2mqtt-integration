"""
user_settings.py

All sensitive values are read from environment variables.
- MQTT creds:  MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASSWORD
- Adv keys:    ADVKEY_<NAME_SLUG>  or  ADVKEY_<MAC_NO_COLONS_UPPER>

Examples (in your env files):
  MQTT_HOST=192.168.0.123
  MQTT_PORT=1883
  MQTT_USER=victron
  MQTT_PASSWORD=yourRealPassword

  ADVKEY_BATTERY_1=<32-hex>
  ADVKEY_SOLAR_CONTROLLER=<32-hex>
  ADVKEY_BATTERY_2=<32-hex>
"""

import os
import re

# MQTT Configuration (secrets via env)
mqtt_host = os.getenv("MQTT_HOST", "localhost")
mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
mqtt_username = os.getenv("MQTT_USER", "")
mqtt_password = os.getenv("MQTT_PASSWORD", "")  # <- NO hardcoded secret

# List of Victron BLE devices to monitor (no secrets here)
# ADVKEY_* bind by name slug: ADVKEY_BATTERY_1, ADVKEY_BATTERY_2, ADVKEY_SOLAR_CONTROLLER
# (keep these `name` values aligned with .env unless you also add ADVKEY_<MAC> per device).
devices = [
    {
        # Physical battery 1 (SmartShunt) — CB:0D:C2:0A:AE:0F
        "mac": "cb:0d:c2:0a:ae:0f",
        "type": "SmartShunt",
        "name": "Battery 1",
        "precision": {
            "voltage": 2,
            "current": 3,
            "power": 2,
            "soc": 1,
            "consumed_ah": 1,
            "midpoint_voltage": 2,
            "midpoint_shift": 2,
            "midpoint_shift_percent": 2,
            "remaining_mins": 0
        },
    },
    {
        # Victron BLE dongle / MPPT (solar charger) — D7:69:EB:1F:F8:3D
        "mac": "d7:69:eb:1f:f8:3d",
        "type": "BlueSolar",
        "name": "Solar-controller",
    },
    {
        # Physical battery 2 (SmartShunt) — D4:EF:FB:B3:D7:0C
        "mac": "d4:ef:fb:b3:d7:0c",
        "type": "SmartShunt",
        "name": "Battery 2",
    },
]

# Inject advertisement keys from env:
#  - Preferred: ADVKEY_<NAME_SLUG>  (e.g., ADVKEY_BATTERY_1)
#  - Fallback:  ADVKEY_<MAC_WITHOUT_COLONS_UPPER>  (e.g., ADVKEY_D4EFFBB3D70C)
def _slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", (s or "").strip()).strip("_").upper()

for d in devices:
    name = d.get("name") or d.get("type") or ""
    mac  = (d.get("mac") or "").replace(":", "").upper()
    key = os.getenv("ADVKEY_" + _slug(name)) or (os.getenv("ADVKEY_" + mac) if mac else None)
    if key:
        d["advertisement_key"] = key

# Optional: Set the logging level
log_level = os.getenv("LOG_LEVEL", "INFO")
