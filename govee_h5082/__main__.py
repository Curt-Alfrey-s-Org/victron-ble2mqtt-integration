"""Run the H5082 MQTT bridge. See mqtt_bridge.py for the protocol."""

from __future__ import annotations

import asyncio
import os
import time

import paho.mqtt.client as mqtt
from bleak import BleakClient
from dbus_fast import BusType, Variant
from dbus_fast.aio import MessageBus

from govee_h5082.mqtt_bridge import (
    ADAPTER,
    PLUGS,
    RECV_UUID,
    SEND_UUID,
    auth_packet,
    command_bytes,
    command_topic,
    discovery_payload,
    discovery_topic,
    dumps,
    iter_switches,
    load_keys,
    payload_for,
    socket_on,
    state_topic,
)

AVAIL = "govee/h5082/bridge/status"
HOLD_S = 20
# Poll every 10 s; re-read the BlueZ object tree every RESCAN_EVERY polls (~60 s).
RESCAN_EVERY = 6


def unwrap(value):
    if isinstance(value, Variant):
        return unwrap(value.value)
    return value


def mfr_last(mfr) -> int | None:
    mfr = unwrap(mfr)
    if not isinstance(mfr, dict):
        return None
    for raw in mfr.values():
        data = unwrap(raw)
        if isinstance(data, (bytes, bytearray)) and data:
            return data[-1]
        if isinstance(data, list) and data:
            return int(data[-1])
    return None


class Bridge:
    def __init__(self) -> None:
        if ADAPTER != "hci1":
            raise SystemExit("refusing adapter other than hci1")
        host = os.environ.get("MQTT_HOST", "")
        user = os.environ.get("MQTT_USER", "")
        password = os.environ.get("MQTT_PASSWORD", "")
        port = int(os.environ.get("MQTT_PORT", "1883"))
        if not host or not user or not password:
            raise SystemExit("MQTT_HOST, MQTT_USER, and MQTT_PASSWORD are required")
        self._keys = load_keys()
        self._state: dict[tuple[str, str], bool] = {}
        self._hold: dict[tuple[str, str], float] = {}
        self._paths: dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.username_pw_set(user, password)
        self._client.will_set(AVAIL, "offline", retain=True)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._host = host
        self._port = port

    def publish_state(self, address: str, side: str, on: bool) -> None:
        self._state[(address, side)] = on
        if not self._client.is_connected():
            return
        self._client.publish(state_topic(address, side), payload_for(on), retain=True)

    def publish_config(self) -> None:
        self._client.publish(AVAIL, "online", retain=True)
        count = 0
        for address, name, side, side_name in iter_switches():
            payload = discovery_payload(address, name, side, side_name)
            self._client.publish(discovery_topic(address, side), dumps(payload), retain=True)
            count += 1
            cached = self._state.get((address, side))
            if cached is not None:
                self.publish_state(address, side, cached)
        self._client.subscribe("govee/h5082/+/+/set")
        print(f"DISCOVERY {count}", flush=True)

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties) -> None:
        if getattr(reason_code, "is_failure", False):
            print(f"MQTT_FAIL {reason_code}", flush=True)
            return
        print("MQTT_OK", flush=True)
        self.publish_config()

    def _on_message(self, _client, _userdata, message) -> None:
        parts = message.topic.split("/")
        if len(parts) != 5 or parts[4] != "set":
            return
        mac = parts[2]
        side = parts[3]
        if side not in ("left", "right"):
            return
        address = ":".join(mac[i : i + 2] for i in range(0, 12, 2)).upper()
        turn_on = message.payload.decode("utf-8", "replace").strip().upper() == "ON"
        loop = self._loop
        if loop is None:
            return
        asyncio.run_coroutine_threadsafe(self.command(address, side, turn_on), loop)

    async def command(self, address: str, side: str, turn_on: bool) -> None:
        token = self._keys.get(address)
        if not token:
            print(f"NO_KEY {address[-5:].replace(':', '')} {side}", flush=True)
            current = self._state.get((address, side))
            if current is not None:
                self.publish_state(address, side, current)
            return
        async with self._lock:
            ok = await self._gatt(address, side, turn_on, token)
        if ok:
            self._hold[(address, side)] = time.monotonic() + HOLD_S
            self.publish_state(address, side, turn_on)
            print(f"SET {address[-5:].replace(':', '')} {side} {payload_for(turn_on)}", flush=True)
        else:
            current = self._state.get((address, side))
            if current is not None:
                self.publish_state(address, side, current)
            print(f"SET_FAIL {address[-5:].replace(':', '')} {side}", flush=True)

    async def _gatt(self, address: str, side: str, turn_on: bool, token: str) -> bool:
        client = BleakClient(address, timeout=20, bluez={"adapter": ADAPTER})
        try:
            await client.connect()
            ready_auth = asyncio.Event()
            ready_set = asyncio.Event()

            def on_notify(_char, data: bytearray) -> None:
                if len(data) < 2 or data[0] != 0x33:
                    return
                if data[1] == 0xB2:
                    ready_auth.set()
                elif data[1] == 0x01:
                    ready_set.set()

            await client.start_notify(RECV_UUID, on_notify)
            await client.write_gatt_char(SEND_UUID, auth_packet(token))
            await asyncio.wait_for(ready_auth.wait(), timeout=8)
            await client.write_gatt_char(SEND_UUID, command_bytes(side, turn_on))
            await asyncio.wait_for(ready_set.wait(), timeout=8)
            return True
        except Exception as exc:
            print(f"GATT {type(exc).__name__}", flush=True)
            return False
        finally:
            if client.is_connected:
                try:
                    await client.disconnect()
                except Exception:
                    pass

    def note_advertisement(self, address: str, last: int) -> None:
        address = address.upper()
        now = time.monotonic()
        for side, on in socket_on(last).items():
            if self._hold.get((address, side), 0) > now:
                continue
            if self._state.get((address, side)) is on and (address, side) in self._state:
                continue
            self.publish_state(address, side, on)
            print(f"STATE {address[-5:].replace(':', '')} {side} {payload_for(on)}", flush=True)

    async def discover(self, bus) -> None:
        """(Re)map plug addresses to their BlueZ object paths on ADAPTER.

        Run at start and every RESCAN_EVERY polls: a plug that was out of range
        (not yet in BlueZ) at start, or whose object BlueZ removed and re-created
        (bluetoothd restart, cache expiry), was otherwise never watched again.
        """
        intro = await bus.introspect("org.bluez", "/")
        root = bus.get_proxy_object("org.bluez", "/", intro)
        objects = await root.get_interface("org.freedesktop.DBus.ObjectManager").call_get_managed_objects()
        wanted = {item[0] for item in PLUGS}
        paths: dict[str, str] = {}
        for path, ifaces in objects.items():
            if not str(path).startswith(f"/org/bluez/{ADAPTER}/dev_"):
                continue
            dev = ifaces.get("org.bluez.Device1")
            if not dev:
                continue
            address = str(unwrap(dev.get("Address") or "")).upper()
            if address not in wanted:
                continue
            paths[address] = str(path)
            last = mfr_last(dev.get("ManufacturerData"))
            if last is not None:
                self.note_advertisement(address, last)
        self._paths = paths

    async def watch(self) -> None:
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        await self.discover(bus)
        polls = 0
        while True:
            polls += 1
            if polls % RESCAN_EVERY == 0:
                try:
                    await self.discover(bus)
                except Exception as exc:
                    print(f"DISCOVER {type(exc).__name__}", flush=True)
            for address, path in list(self._paths.items()):
                try:
                    node = await bus.introspect("org.bluez", path)
                    proxy = bus.get_proxy_object("org.bluez", path, node)
                    raw = await proxy.get_interface("org.freedesktop.DBus.Properties").call_get(
                        "org.bluez.Device1", "ManufacturerData"
                    )
                except Exception:
                    continue
                last = mfr_last(raw)
                if last is not None:
                    self.note_advertisement(address, last)
            await asyncio.sleep(10)

    async def run(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._client.connect(self._host, self._port)
        self._client.loop_start()
        try:
            await self.watch()
        finally:
            self._client.publish(AVAIL, "offline", retain=True)
            self._client.loop_stop()
            self._client.disconnect()


def main() -> None:
    asyncio.run(Bridge().run())


if __name__ == "__main__":
    main()
