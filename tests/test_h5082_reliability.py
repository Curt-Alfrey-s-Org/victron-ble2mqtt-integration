"""H5082 bridge reliability: retry, per-plug latest-wins, reconnect, QoS (no BlueZ, no broker)."""

from __future__ import annotations

import asyncio
import types
from unittest.mock import Mock

import pytest

govee_main = pytest.importorskip("govee_h5082.__main__")
from govee_h5082.mqtt_bridge import (  # noqa: E402
    PLUGS,
    command_bytes,
    discovery_payload,
    iter_switches,
    state_topic,
)

A = PLUGS[0][0]  # 2F9D
B = PLUGS[1][0]  # 3013
NO_KEY_ADDR = PLUGS[7][0]  # C38D (no key on the Pi)
TOKEN = "00112233445566778899aabbccddeeff"


class FakeWorld:
    """Scripted BLE: per-address failure queues and a record of every call."""

    def __init__(self) -> None:
        self.find_calls: list[tuple[str, dict]] = []
        self.connect_calls: list[str] = []
        self.writes: list[tuple[str, bytes]] = []
        self.clients: list[FakeClient] = []
        self.connect_fail: dict[str, list[Exception]] = {}
        self.write_fail: dict[str, list[Exception]] = {}
        self.write_gate: dict[str, asyncio.Event] = {}
        self.connecting = 0
        self.max_connecting = 0


class FakeClient:
    def __init__(self, world: FakeWorld, device, disconnected_callback=None, timeout=None, bluez=None):
        self.world = world
        self.address = device.address
        self.cb = disconnected_callback
        self.timeout = timeout
        self.bluez = bluez
        self.is_connected = False
        self.notify = None
        world.clients.append(self)

    async def connect(self):
        w = self.world
        w.connect_calls.append(self.address)
        w.connecting += 1
        w.max_connecting = max(w.max_connecting, w.connecting)
        try:
            await asyncio.sleep(0.01)
            fails = w.connect_fail.get(self.address) or []
            if fails:
                raise fails.pop(0)
            self.is_connected = True
        finally:
            w.connecting -= 1

    async def disconnect(self):
        self.is_connected = False

    async def start_notify(self, _uuid, cb):
        self.notify = cb

    async def write_gatt_char(self, _uuid, data):
        w = self.world
        w.writes.append((self.address, bytes(data)))
        if data[1] == 0xB2:  # auth
            self.notify(None, bytearray([0x33, 0xB2]))
            return
        gate = w.write_gate.get(self.address)
        if gate is not None:
            await gate.wait()
        fails = w.write_fail.get(self.address) or []
        if fails:
            raise fails.pop(0)
        self.notify(None, bytearray([0x33, 0x01]))

    def drop(self):
        """The plug went away (out of range / power cut)."""
        self.is_connected = False
        if self.cb:
            self.cb(self)


@pytest.fixture
def world(monkeypatch):
    w = FakeWorld()

    class Scanner:
        @staticmethod
        async def find_device_by_address(address, timeout=10.0, **kwargs):
            w.find_calls.append((address, kwargs))
            return types.SimpleNamespace(address=address)

    monkeypatch.setattr(govee_main, "_bleak_scanner_cls", lambda: Scanner)
    monkeypatch.setattr(
        govee_main, "_bleak_client_cls", lambda: lambda *a, **k: FakeClient(w, *a, **k)
    )
    monkeypatch.setattr(govee_main, "RETRY_BACKOFF_S", (0.0, 0.0))
    return w


@pytest.fixture
def bridge(monkeypatch):
    monkeypatch.setenv("MQTT_HOST", "broker.invalid")
    monkeypatch.setenv("MQTT_USER", "u")
    monkeypatch.setenv("MQTT_PASSWORD", "p")
    for name in ("H5082_RSSI_ONLY", "H5082_PLUGS", "H5082_LISTENER", "H5082_ADAPTER"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(govee_main, "load_keys", lambda: {A: TOKEN, B: TOKEN})
    br = govee_main.Bridge()
    br._client = Mock()
    br._client.is_connected.return_value = True
    return br


def _published(br, address, side):
    topic = state_topic(address, side)
    return [c.args[1] for c in br._client.publish.call_args_list if c.args[0] == topic]


async def _drain(br):
    for _ in range(200):
        await asyncio.sleep(0)
        busy = [t for t in br._workers.values() if not t.done()]
        if not busy:
            return
        # Workers linger on an idle wait; stop once nothing is pending.
        if not br._desired and all(w.is_set() is False for w in br._wake.values()):
            await asyncio.sleep(0.05)
            if not br._desired:
                return
    raise AssertionError("workers did not settle")


def _cmds(world, address):
    return [d for a, d in world.writes if a == address and d[1] != 0xB2]


def _auths(world, address):
    return [d for a, d in world.writes if a == address and d[1] == 0xB2]


def test_discovery_asks_for_qos_1():
    address, name, side, label = next(iter_switches())
    assert discovery_payload(address, name, side, label)["qos"] == 1


def test_set_subscription_is_qos_1(bridge):
    bridge.publish_config()
    bridge._client.subscribe.assert_called_with("govee/h5082/+/+/set", qos=1)


def test_retry_then_success_publishes_new_state(world, bridge, capsys):
    async def run():
        bridge._state[(A, "left")] = False
        world.write_fail[A] = [OSError("ATT error 0x0e"), TimeoutError("no ack")]
        await bridge.command(A, "left", True)
        await _drain(bridge)

    asyncio.run(run())
    out = capsys.readouterr().out
    assert _cmds(world, A) == [command_bytes("left", True)] * 3
    assert _published(bridge, A, "left")[-1] == "ON"
    assert "OSError: ATT error 0x0e" in out  # real exception text is logged
    assert "SET 2F9D left ON try 3" in out
    assert "SET_FAIL" not in out


def test_all_retries_fail_reverts_to_last_known_state(world, bridge, capsys):
    async def run():
        bridge._state[(A, "right")] = False
        world.connect_fail[A] = [OSError("br-connection-canceled")] * 3
        await bridge.command(A, "right", True)
        await _drain(bridge)

    asyncio.run(run())
    out = capsys.readouterr().out
    assert len(world.connect_calls) == govee_main.RETRIES
    assert _published(bridge, A, "right") == ["OFF"]
    assert "SET_FAIL 2F9D right ON" in out
    assert "br-connection-canceled" in out
    # A failed connect forgets the cached device, so every try looks it up again.
    assert len(world.find_calls) == govee_main.RETRIES


def test_latest_command_wins_per_socket(world, bridge):
    async def run():
        gate = asyncio.Event()
        world.write_gate[A] = gate
        await bridge.command(A, "left", True)
        await asyncio.sleep(0.05)  # first ON is in flight
        for want in (False, True, False):
            await bridge.command(A, "left", want)
        gate.set()
        await _drain(bridge)

    asyncio.run(run())
    assert _cmds(world, A) == [command_bytes("left", True), command_bytes("left", False)]
    assert _published(bridge, A, "left")[-1] == "OFF"


def test_plugs_do_not_wait_on_each_other(world, bridge):
    async def run():
        gate = asyncio.Event()
        world.write_gate[A] = gate  # plug A hangs mid-command
        await bridge.command(A, "left", True)
        await bridge.command(B, "right", True)
        for _ in range(100):
            await asyncio.sleep(0.01)
            if _published(bridge, B, "right"):
                break
        b_done_while_a_blocked = _published(bridge, B, "right") == ["ON"]
        gate.set()
        await _drain(bridge)
        return b_done_while_a_blocked

    assert asyncio.run(run())
    assert world.max_connecting == 1  # connection attempts on hci1 stay serialized


def test_link_is_reused_and_reconnects_after_drop(world, bridge):
    async def run():
        await bridge.command(A, "left", True)
        await _drain(bridge)
        await bridge.command(A, "right", True)
        await _drain(bridge)
        assert len(world.connect_calls) == 1
        assert len(_auths(world, A)) == 1  # login once per connection
        world.clients[-1].drop()
        await bridge.command(A, "left", False)
        await _drain(bridge)

    asyncio.run(run())
    assert len(world.connect_calls) == 2
    assert len(_auths(world, A)) == 2
    # BLEDevice resolved once on hci1 and cached across the reconnect.
    assert world.find_calls == [(A, {"bluez": {"adapter": "hci1"}})]
    assert world.clients[0].bluez == {"adapter": "hci1"}
    assert _published(bridge, A, "left")[-1] == "OFF"


def test_idle_link_is_closed(world, bridge, monkeypatch):
    monkeypatch.setattr(govee_main, "IDLE_DISCONNECT_S", 0.05)

    async def run():
        await bridge.command(A, "left", True)
        for _ in range(100):
            await asyncio.sleep(0.01)
            if A not in bridge._workers:
                break

    asyncio.run(run())
    assert not world.clients[-1].is_connected
    assert A not in bridge._workers


def test_no_key_plug_is_skipped(world, bridge, capsys):
    async def run():
        bridge._state[(NO_KEY_ADDR, "left")] = True
        await bridge.command(NO_KEY_ADDR, "left", False)
        await _drain(bridge)

    asyncio.run(run())
    assert world.connect_calls == [] and world.find_calls == []
    assert _published(bridge, NO_KEY_ADDR, "left") == ["ON"]
    assert "NO_KEY C38D left" in capsys.readouterr().out


def test_on_message_logs_command_exceptions(bridge, capsys, monkeypatch):
    async def boom(*_args):
        raise RuntimeError("worker exploded")

    monkeypatch.setattr(bridge, "command", boom)

    async def run():
        bridge._loop = asyncio.get_running_loop()
        msg = types.SimpleNamespace(topic=f"govee/h5082/{A.replace(':', '').lower()}/left/set", payload=b"ON")
        await asyncio.to_thread(bridge._on_message, None, None, msg)
        await asyncio.sleep(0.05)

    asyncio.run(run())
    assert "TASK_ERROR command 2F9D left RuntimeError: worker exploded" in capsys.readouterr().out


def test_on_message_ignores_garbage_payload(bridge, capsys):
    bridge._loop = Mock()
    msg = types.SimpleNamespace(topic=f"govee/h5082/{A.replace(':', '').lower()}/left/set", payload=b"toggle")
    bridge._on_message(None, None, msg)
    assert "BAD_PAYLOAD" in capsys.readouterr().out
