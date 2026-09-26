"""H5082 MQTT discovery publishes two sockets and never includes a key."""

from govee_h5082.mqtt_bridge import (
    LEFT_ON,
    PLUGS,
    auth_packet,
    command_bytes,
    discovery_payload,
    dumps,
    iter_switches,
    socket_on,
)


def test_two_switches_per_plug():
    rows = list(iter_switches())
    assert len(rows) == 16
    assert len({address for address, _name, _side, _label in rows}) == 8


def test_state_bits_match_h5082():
    assert socket_on(0) == {"left": False, "right": False}
    assert socket_on(1) == {"left": False, "right": True}
    assert socket_on(2) == {"left": True, "right": False}
    assert socket_on(3) == {"left": True, "right": True}


def test_discovery_has_command_and_state_and_no_key():
    secret = "00112233445566778899aabbccddeeff"
    address, name, side, label = next(iter_switches())
    payload = discovery_payload(address, name, side, label)
    text = dumps(payload)
    assert secret not in text
    assert payload["command_topic"].endswith("/set")
    assert payload["state_topic"].endswith("/state")
    assert payload["object_id"].startswith("h5082_")
    assert payload["device"]["model"] == "H5082"
    assert len(list(iter_switches(PLUGS[:1]))) == 2


def test_command_bytes_are_the_h5082_messages():
    assert command_bytes("left", True) == LEFT_ON
    packet = auth_packet("00112233445566778899aabbccddeeff")
    assert len(packet) == 20
    assert packet[0:2] == bytes.fromhex("33b2")
    checksum = 0
    for byte in packet[:-1]:
        checksum ^= byte
    assert packet[-1] == checksum & 0xFF
