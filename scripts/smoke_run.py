"""Quick smoke script: imports settings and prints a short summary.
This is safe to run locally and doesn't start BLE or MQTT.
"""
from victron_ble2mqtt.user_settings import UserSettings


def main() -> None:
    s = UserSettings()
    print("MQTT host:", s.mqtt.host)
    print("Devices:", [d.mac for d in s.devices])


if __name__ == "__main__":
    main()
