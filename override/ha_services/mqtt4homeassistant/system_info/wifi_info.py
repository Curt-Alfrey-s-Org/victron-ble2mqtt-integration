def get_wifi_infos():
    # If iwconfig/iw aren't available, return nothing (no crash, no spam).
    # This path is not loaded at runtime: ha_services is a regular site-packages
    # package, so PYTHONPATH overlay cannot replace wifi_info.py. Pi host metrics
    # still call the installed module; Victron BLE keeps the event loop free via
    # asyncio.to_thread in override/victron_ble2mqtt/__main__.py.
    return []
