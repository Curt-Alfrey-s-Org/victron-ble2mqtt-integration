"""Container liveness probe for victron_ble2mqtt.

Used by Docker HEALTHCHECK and Compose healthcheck. Does not call MQTT.
File mtimes via os.path.getmtime; age via time.time (stdlib).
https://docs.python.org/3/library/os.path.html#os.path.getmtime
https://docs.python.org/3/library/time.html#time.time
"""

import os
import time

# Defaults documented for operators; paths resolved from env on each call.
_DEFAULT_HEARTBEAT = "/tmp/victron_ble2mqtt.heartbeat"
_DEFAULT_SCANNER_OK = "/tmp/victron_ble2mqtt.scanner_ok"
_DEFAULT_BLE_PUBLISH = "/tmp/victron_ble2mqtt.ble_publish"


def _heartbeat_path() -> str:
    return os.getenv("HEARTBEAT_FILE", _DEFAULT_HEARTBEAT)


def _scanner_ok_path() -> str:
    return os.getenv("BLE_SCANNER_OK_FILE", _DEFAULT_SCANNER_OK)


def _ble_publish_path() -> str:
    return os.getenv("BLE_PUBLISH_HEARTBEAT_FILE", _DEFAULT_BLE_PUBLISH)


# Re-export default path names for __main__ (scanner ok unlink at startup).
BLE_SCANNER_OK_FILE = _DEFAULT_SCANNER_OK


def touch_file(path: str) -> None:
    """Create or update mtime on a liveness marker file."""
    with open(path, "a", encoding="utf-8"):
        os.utime(path, None)


def remove_file(path: str) -> None:
    """Remove a liveness marker if present (ignore missing)."""
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def touch_system_heartbeat(path: str | None = None) -> None:
    touch_file(path or _heartbeat_path())


def touch_scanner_ok(path: str | None = None) -> None:
    touch_file(path or _scanner_ok_path())


def touch_ble_publish_heartbeat(path: str | None = None) -> None:
    touch_file(path or _ble_publish_path())


def _mtime_age_sec(path: str) -> float | None:
    if not os.path.exists(path):
        return None
    return time.time() - os.path.getmtime(path)


def check() -> int:
    """Return 0 if healthy, 1 if unhealthy (for healthcheck SystemExit)."""
    poll_sec = float(os.getenv("SYSTEM_POLL_THROTTLE_SEC") or 60)
    system_max_age = 20 * poll_sec + 60

    system_age = _mtime_age_sec(_heartbeat_path())
    if system_age is None or system_age > system_max_age:
        return 1

    if not os.path.exists(_scanner_ok_path()):
        return 1

    ble_max_age = float(os.getenv("BLE_PUBLISH_MAX_AGE_SEC") or 600)
    ble_age = _mtime_age_sec(_ble_publish_path())
    if ble_age is None or ble_age > ble_max_age:
        return 1

    return 0
