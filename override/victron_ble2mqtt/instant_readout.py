"""Instant Readout de-dupe vs Home Assistant MQTT state.

keshavdv/victron-ble 0.9.2 drops identical manufacturer payloads forever
(_seen_data). MQTT sensor state is undefined after an HA restart unless a new
publish arrives (or the publisher retained the last value).

https://github.com/keshavdv/victron-ble/blob/v0.9.2/victron_ble/scanner.py
https://www.home-assistant.io/integrations/sensor.mqtt/
"""


def prepare_seen_data_for_republish(
    *,
    payload: bytes,
    seen_data: set[bytes],
    last_pub: float,
    now: float,
    pub_gap: float,
) -> bool:
    """Return True if BaseScanner should handle this Instant Readout payload.

    When True, ``payload`` is discarded from ``seen_data`` so upstream
    ``_detection_callback`` will not skip an unchanged advertisement.
    """
    if (now - last_pub) < pub_gap:
        return False
    seen_data.discard(payload)
    return True
