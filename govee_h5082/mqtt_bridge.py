"""Publish H5082 sockets to Home Assistant over MQTT.

Command bytes and the advertisement state bits are the virtuald/govee-ble-plugs
H5082 procedure (Left/Right on and off, manufacturer-data last byte). The bridge
does not invent a second protocol. Keys stay in the Pi key file and are never
logged. hci0 is the Victron adapter and is never opened.
"""

from __future__ import annotations

import json
import os
from typing import Iterable

ADAPTER = "hci1"
KEY_PATH = "/home/n4s1/.govee-h5082-keys"
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


def discovery_payload(address: str, name: str, side: str, side_name: str) -> dict:
    ident = f"h5082_{mac_id(address)}"
    return {
        "name": side_name,
        "object_id": f"h5082_{suffix(address)}_{side}",
        "unique_id": f"{ident}_{side}",
        "command_topic": command_topic(address, side),
        "state_topic": state_topic(address, side),
        "availability_topic": "govee/h5082/bridge/status",
        "payload_available": "online",
        "payload_not_available": "offline",
        "payload_on": "ON",
        "payload_off": "OFF",
        "state_on": "ON",
        "state_off": "OFF",
        "device_class": "outlet",
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


def load_keys(path: str = KEY_PATH) -> dict[str, str]:
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
