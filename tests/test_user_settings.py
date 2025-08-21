def test_user_settings_default_importable():
    import sys, os
    repo = os.path.abspath('.')
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from victron_ble2mqtt.user_settings import UserSettings
    from victron_ble2mqtt import user_settings_data

    s = UserSettings()
    assert s.mqtt.host == getattr(user_settings_data, 'mqtt_host', 'localhost')
    assert isinstance(s.devices, list)
