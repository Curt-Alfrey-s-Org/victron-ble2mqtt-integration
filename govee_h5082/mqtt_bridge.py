"""Publish H5082 sockets to Home Assistant over MQTT.

Command bytes and the advertisement state bits are the virtuald/govee-ble-plugs
H5082 procedure (Left/Right on and off, manufacturer-data last byte). The bridge
does not invent a second protocol. Keys stay in the Pi key file and are never
logged. On the Pi 4, hci0 is the Victron adapter and is never opened.

Several bridges (one per Pi) may share the broker. Each one owns only the plugs in
its allowlist (H5082_PLUGS, from a host file outside git); HA keeps one entity per
socket because every owner uses the same command / state / discovery topics. Only
the availability topic is per host, so a Pi going down greys out only its plugs.
"""

from __future__ import annotations

import json
import os
import re
import stat
from collections.abc import Iterable

ADAPTER = "hci1"
KEY_PATH = "/home/n4s1/.govee-h5082-keys"
# One bridge owning every plug (the Pi 4 before per-host ownership). Kept when no
# allowlist is set so an unchanged Pi 4 publishes exactly what it did before.
AVAIL_LEGACY = "govee/h5082/bridge/status"
SEND_UUID = "00010203-0405-0607-0809-0a0b0c0d2b11"
RECV_UUID = "00010203-0405-0607-0809-0a0b0c0d2b10"

# Exact payloads from GoveePlugH5082.
LEFT_ON = bytes.fromhex("3301220000000000000000000000000000000010")
LEFT_OFF = bytes.fromhex("3301200000000000000000000000000000000012")
RIGHT_ON = bytes.fromhex("3301110000000000000000000000000000000023")
RIGHT_OFF = bytes.fromhex("3301100000000000000000000000000000000022")

PLUGS = (
    ("D4:13:68:3A:2F:9D", "ihoment_H5082_2F9D"),
    ("D4:13:68:3A:30:13", "ihoment_H5082_3013"),
    ("D4:13:68:4A:3E:C9", "ihoment_H5082_3EC9"),
    ("D4:13:68:3D:96:07", "ihoment_H5082_9607"),
    ("D4:13:68:60:CF:79", "ihoment_H5082_CF79"),
    ("D4:13:68:61:82:FB", "ihoment_H5082_82FB"),
    ("D4:13:68:61:C0:61", "ihoment_H5082_C061"),
    ("D4:13:68:61:C3:8D", "ihoment_H5082_C38D"),
)

SIDES = (("left", 0, "Left"), ("right", 1, "Right"))


def sign(data: bytes) -> int:
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum & 0xFF


def auth_packet(token_hex: str) -> bytes:
    packet = bytearray([0x33, 0xB2]) + bytearray.fromhex(token_hex).ljust(17, b"\0")
    packet.append(sign(packet))
    return bytes(packet)


def command_bytes(side: str, turn_on: bool) -> bytes:
    table = {
        ("left", True): LEFT_ON,
        ("left", False): LEFT_OFF,
        ("right", True): RIGHT_ON,
        ("right", False): RIGHT_OFF,
    }
    return table[(side, turn_on)]


def socket_on(last: int) -> dict[str, bool]:
    """H5082 advertisement: bit 0x2 is left, bit 0x1 is right."""
    return {"left": (last & 0x2) == 0x2, "right": (last & 0x1) == 0x1}


def mac_id(address: str) -> str:
    return address.replace(":", "").lower()


def suffix(address: str) -> str:
    return address[-5:].replace(":", "").lower()


def state_topic(address: str, side: str) -> str:
    return f"govee/h5082/{mac_id(address)}/{side}/state"


def command_topic(address: str, side: str) -> str:
    return f"govee/h5082/{mac_id(address)}/{side}/set"


def discovery_topic(address: str, side: str) -> str:
    return f"homeassistant/switch/h5082_{suffix(address)}_{side}/config"


def payload_for(on: bool) -> str:
    return "ON" if on else "OFF"


def avail_topic(host: str | None) -> str:
    """Bridge availability: legacy single topic, or one per owning host."""
    return f"govee/h5082/bridge/{host}/status" if host else AVAIL_LEGACY


def owner_topic(address: str) -> str:
    """Retained claim: which host's bridge owns this plug (payload = host id)."""
    return f"govee/h5082/{mac_id(address)}/owner"


def discovery_payload(
    address: str, name: str, side: str, side_name: str, availability_topic: str = AVAIL_LEGACY
) -> dict:
    ident = f"h5082_{mac_id(address)}"
    return {
        "name": side_name,
        "object_id": f"h5082_{suffix(address)}_{side}",
        "unique_id": f"{ident}_{side}",
        "command_topic": command_topic(address, side),
        "state_topic": state_topic(address, side),
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
        "payload_on": "ON",
        "payload_off": "OFF",
        "state_on": "ON",
        "state_off": "OFF",
        "device_class": "outlet",
        "qos": 1,
        "device": {
            "identifiers": [ident],
            "name": name,
            "manufacturer": "Govee",
            "model": "H5082",
            "connections": [["mac", address]],
        },
    }


def iter_switches(plugs: Iterable[tuple[str, str]] = PLUGS):
    for address, name in plugs:
        for side, _port, side_name in SIDES:
            yield address, name, side, side_name


def key_path() -> str:
    """Key file: H5082_KEY_PATH, else the Pi default. Never inside the repo."""
    return os.environ.get("H5082_KEY_PATH") or KEY_PATH


def key_file_problem(path: str) -> str | None:
    """Why the key file is unsafe (readable by group/others), or None."""
    try:
        mode = os.stat(path).st_mode
    except FileNotFoundError:
        return "missing"
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        return f"mode {stat.S_IMODE(mode):o}, want 600"
    return None


def parse_owned(value: str | None, plugs: Iterable[tuple[str, str]] = PLUGS) -> set[str] | None:
    """H5082_PLUGS -> owned plug addresses.

    Unset / blank -> None (legacy: this bridge owns every plug). "all" -> every plug.
    Otherwise plug ids (last 4 hex of the MAC, e.g. "82FB") or full MACs, separated by
    commas or spaces; "none" owns nothing (RSSI only). An unknown id is an error, so a
    typo cannot silently drop a plug.
    """
    if value is None or not value.strip():
        return None
    plugs = tuple(plugs)
    words = [w for w in re.split(r"[\s,]+", value.strip()) if w]
    if [w.lower() for w in words] == ["all"]:
        return {address for address, _name in plugs}
    if [w.lower() for w in words] == ["none"]:
        return set()
    by_id = {address.replace(":", "")[-4:].upper(): address for address, _name in plugs}
    by_mac = {address.upper(): address for address, _name in plugs}
    owned: set[str] = set()
    for word in words:
        address = by_id.get(word.upper()) or by_mac.get(word.upper())
        if address is None:
            raise ValueError(f"unknown H5082 plug {word!r} (known: {', '.join(sorted(by_id))})")
        owned.add(address)
    return owned


def load_keys(path: str | None = None) -> dict[str, str]:
    path = path or key_path()
    found: dict[str, str] = {}
    if not os.path.exists(path):
        return found
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) >= 3 and len(parts[-1]) >= 16:
                found[parts[0].upper()] = parts[-1]
    return found


def dumps(payload: dict) -> str:
    return json.dumps(payload, separators=(",", ":"))


def rssi_topic(address: str, listener: str) -> str:
    return f"govee/h5082/{mac_id(address)}/rssi/{listener}"


def rssi_discovery_topic(address: str, listener: str) -> str:
    return f"homeassistant/sensor/h5082_{suffix(address)}_rssi_{listener}/config"


def rssi_discovery_payload(address: str, name: str, listener: str) -> dict:
    ident = f"h5082_{mac_id(address)}"
    return {
        "name": f"RSSI {listener}",
        "object_id": f"h5082_{suffix(address)}_rssi_{listener}",
        "unique_id": f"{ident}_rssi_{listener}",
        "state_topic": rssi_topic(address, listener),
        "device_class": "signal_strength",
        "unit_of_measurement": "dBm",
        "expire_after": 90,
        "device": {
            "identifiers": [ident],
            "name": name,
            "manufacturer": "Govee",
            "model": "H5082",
            "connections": [["mac", address]],
        },
    }


def pick_owner(samples: dict[str, int]) -> str | None:
    """Closest radio wins (highest RSSI). On a tie, pi5 then ha-105 then pi4."""
    if not samples:
        return None
    rank = {"pi5": 0, "ha-105": 1, "pi4": 2}
    return max(samples, key=lambda name: (samples[name], -rank.get(name, 9)))
