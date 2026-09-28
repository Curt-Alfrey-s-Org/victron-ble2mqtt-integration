"""Run the H5082 MQTT bridge. See mqtt_bridge.py for the protocol."""

from __future__ import annotations

import asyncio
import os
import re
import time

import paho.mqtt.client as mqtt
from dbus_fast import BusType, Variant
from dbus_fast.aio import MessageBus

from govee_h5082.mqtt_bridge import (
    AVAIL_LEGACY,
    PLUGS,
    RECV_UUID,
    SEND_UUID,
    auth_packet,
    avail_topic,
    command_bytes,
    discovery_payload,
    discovery_topic,
    dumps,
    iter_switches,
    key_file_problem,
    key_path,
    load_keys,
    owner_topic,
    parse_owned,
    payload_for,
    rssi_discovery_payload,
    rssi_discovery_topic,
    rssi_topic,
    socket_on,
    state_topic,
)

MAC_HEX_LEN = 12
OWNER_TOPIC_PARTS = 4  # govee/h5082/<mac>/owner
AVAIL = AVAIL_LEGACY  # kept for callers; a per-host bridge uses Bridge._avail
HOLD_S = 20
# Poll every 10 s; re-read the BlueZ object tree every RESCAN_EVERY polls (~60 s).
RESCAN_EVERY = 6

# GATT timing (unchanged from the one-shot client): connect 20 s, auth reply 8 s,
# command reply 8 s. FIND_TIMEOUT_S is the address lookup the old
# BleakClient(address) did inside its 20 s connect when BlueZ had no device object.
CONNECT_TIMEOUT_S = 20
ACK_TIMEOUT_S = 8
FIND_TIMEOUT_S = 20
# A failed command is tried RETRIES times in total, sleeping RETRY_BACKOFF_S between.
RETRIES = 3
RETRY_BACKOFF_S = (1.0, 2.0)
# Keep a plug's GATT link open this long after its last command so bursts (dump
# staging, retries, left+right) reuse one login. 0 keeps links open until they drop.
# The plug does not advertise while connected, so a link held forever would hide
# button presses and RSSI ("heard by") for that plug.
IDLE_DISCONNECT_S = float(os.environ.get("H5082_IDLE_DISCONNECT_S", "120"))


def _bleak_client_cls():
    from bleak import BleakClient

    return BleakClient


def _bleak_scanner_cls():
    from bleak import BleakScanner

    return BleakScanner


def _short(address: str) -> str:
    return address[-5:].replace(":", "")


def _log_task_error(what: str):
    """Done-callback for futures/tasks: log exceptions instead of dropping them."""

    def _done(fut) -> None:
        if fut.cancelled():
            return
        exc = fut.exception()
        if exc is not None:
            print(f"TASK_ERROR {what} {type(exc).__name__}: {exc}", flush=True)

    return _done


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


class PlugLink:
    """One persistent GATT link per plug: resolve once, connect, log in once, reuse.

    Connection attempts on the shared adapter are serialized by ``adapter_lock``;
    writes on an established link are not, so plugs do not wait on each other.
    """

    def __init__(self, address: str, adapter: str, token: str, adapter_lock: asyncio.Lock) -> None:
        self.address = address
        self.adapter = adapter
        self._token = token
        self._adapter_lock = adapter_lock
        self.device = None  # cached BLEDevice from BleakScanner.find_device_by_address
        self.client = None
        self.authed = False
        self.connects = 0
        self._ready_auth = asyncio.Event()
        self._ready_set = asyncio.Event()

    @property
    def connected(self) -> bool:
        client = self.client
        return client is not None and bool(client.is_connected) and self.authed

    def _on_disconnect(self, client) -> None:
        if client is self.client:
            self.client = None
            self.authed = False
            print(f"LINK_DROP {_short(self.address)}", flush=True)

    def _on_notify(self, _char, data: bytearray) -> None:
        if len(data) < 2 or data[0] != 0x33:
            return
        if data[1] == 0xB2:
            self._ready_auth.set()
        elif data[1] == 0x01:
            self._ready_set.set()

    async def _resolve(self):
        if self.device is None:
            device = await _bleak_scanner_cls().find_device_by_address(
                self.address, timeout=FIND_TIMEOUT_S, bluez={"adapter": self.adapter}
            )
            if device is None:
                raise LookupError(f"{self.address} not seen on {self.adapter} in {FIND_TIMEOUT_S}s")
            self.device = device
        return self.device

    async def ensure(self) -> None:
        """Connect and log in unless the link is already up."""
        if self.connected:
            return
        await self.close()
        async with self._adapter_lock:
            device = await self._resolve()
            client = _bleak_client_cls()(
                device,
                disconnected_callback=self._on_disconnect,
                timeout=CONNECT_TIMEOUT_S,
                bluez={"adapter": self.adapter},
            )
            try:
                await client.connect()
            except BaseException:
                # Stale BlueZ object or plug moved: look it up again next attempt.
                self.device = None
                await _quiet_disconnect(client)
                raise
        self.connects += 1
        try:
            self._ready_auth.clear()
            await client.start_notify(RECV_UUID, self._on_notify)
            await client.write_gatt_char(SEND_UUID, auth_packet(self._token))
            await asyncio.wait_for(self._ready_auth.wait(), timeout=ACK_TIMEOUT_S)
        except BaseException:
            await _quiet_disconnect(client)
            raise
        self.client = client
        self.authed = True
        print(f"LINK_UP {_short(self.address)}", flush=True)

    async def send(self, side: str, turn_on: bool) -> None:
        await self.ensure()
        client = self.client
        if client is None:  # dropped between login and write
            raise ConnectionError(f"{self.address} link dropped before write")
        self._ready_set.clear()
        await client.write_gatt_char(SEND_UUID, command_bytes(side, turn_on))
        await asyncio.wait_for(self._ready_set.wait(), timeout=ACK_TIMEOUT_S)

    async def close(self) -> None:
        client, self.client, self.authed = self.client, None, False
        if client is not None:
            await _quiet_disconnect(client)


async def _quiet_disconnect(client) -> None:
    try:
        if client.is_connected:
            await client.disconnect()
    except Exception as exc:
        print(f"DISCONNECT_ERR {type(exc).__name__}: {exc}", flush=True)


class Bridge:
    def __init__(self) -> None:
        self._adapter = os.environ.get("H5082_ADAPTER", "hci1")
        self._listener = os.environ.get("H5082_LISTENER", "pi4")
        self._rssi_only = os.environ.get("H5082_RSSI_ONLY", "") == "1"
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", self._listener):
            raise SystemExit(f"H5082_LISTENER {self._listener!r}: use a short host id such as pi4 or pi5")
        if self._listener == "pi4" and self._adapter != "hci1":
            raise SystemExit("pi4 listener uses hci1 only (hci0 is Victron)")
        if not re.fullmatch(r"hci[0-9]+", self._adapter):
            raise SystemExit(f"H5082_ADAPTER {self._adapter!r}: expected hciN")
        # Plug ownership. Unset = legacy single bridge (every plug, legacy availability
        # topic), allowed only on the Pi 4 so a second Pi can never grab every plug.
        try:
            owned = parse_owned(os.environ.get("H5082_PLUGS"))
        except ValueError as exc:
            raise SystemExit(f"H5082_PLUGS: {exc}") from None
        self._per_host = owned is not None
        if not self._per_host and not self._rssi_only and self._listener != "pi4":
            raise SystemExit(
                f"H5082_PLUGS is required on {self._listener} (for example H5082_PLUGS=82FB "
                "in /home/n4s1/.config/h5082-bridge.env); see docs/H5082_MULTI_BRIDGE.md"
            )
        self._owned: set[str] = {address for address, _name in PLUGS} if owned is None else owned
        self._avail = avail_topic(self._listener if self._per_host else None)
        host = os.environ.get("MQTT_HOST", "")
        user = os.environ.get("MQTT_USER") or os.environ.get("MQTT_USERNAME", "")
        password = os.environ.get("MQTT_PASSWORD", "")
        port = int(os.environ.get("MQTT_PORT", "1883"))
        if not host or not user or not password:
            raise SystemExit("MQTT_HOST, MQTT_USER, and MQTT_PASSWORD are required")
        self._keys = load_keys()
        self._key_problem = key_file_problem(key_path()) if not self._rssi_only else None
        self._state: dict[tuple[str, str], bool] = {}
        self._hold: dict[tuple[str, str], float] = {}
        self._paths: dict[str, str] = {}
        # Latest requested state per socket; a newer command replaces an older one.
        self._desired: dict[tuple[str, str], bool] = {}
        self._workers: dict[str, asyncio.Task] = {}
        self._wake: dict[str, asyncio.Event] = {}
        self._links: dict[str, PlugLink] = {}
        self._adapter_lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.username_pw_set(user, password)
        if not self._rssi_only:
            self._client.will_set(self._avail, "offline", qos=1, retain=True)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._host = host
        self._port = port

    def publish_state(self, address: str, side: str, on: bool) -> None:
        self._state[(address, side)] = on
        if not self._client.is_connected():
            return
        self._client.publish(state_topic(address, side), payload_for(on), qos=1, retain=True)

    def publish_rssi(self, address: str, rssi: int) -> None:
        if not self._client.is_connected():
            return
        self._client.publish(rssi_topic(address, self._listener), str(rssi), retain=False)

    def owns(self, address: str) -> bool:
        # Legacy (no allowlist): everything, exactly as before (unknown -> NO_KEY).
        return not self._per_host or address.upper() in self._owned

    def owned_plugs(self) -> list[tuple[str, str]]:
        return [(address, name) for address, name in PLUGS if address in self._owned]

    def describe(self) -> str:
        ids = " ".join(_short(address) for address, _name in self.owned_plugs()) or "none"
        mode = "per-host" if self._per_host else "all (no H5082_PLUGS)"
        return f"OWNS {ids} listener={self._listener} adapter={self._adapter} mode={mode}"

    def publish_config(self) -> None:
        if not self._rssi_only:
            self._client.publish(self._avail, "online", qos=1, retain=True)
        count = 0
        for address, name in PLUGS:
            self._client.publish(
                rssi_discovery_topic(address, self._listener),
                dumps(rssi_discovery_payload(address, name, self._listener)),
                retain=True,
            )
            count += 1
        if not self._rssi_only:
            # Only the owner publishes a plug's switch config, so each socket keeps one
            # HA entity whose availability follows the Pi that actually drives it.
            for address, name, side, side_name in iter_switches(self.owned_plugs()):
                payload = discovery_payload(address, name, side, side_name, self._avail)
                self._client.publish(discovery_topic(address, side), dumps(payload), qos=1, retain=True)
                cached = self._state.get((address, side))
                if cached is not None:
                    self.publish_state(address, side, cached)
            self._client.subscribe("govee/h5082/+/+/set", qos=1)
            if self._per_host:
                for address, _name in self.owned_plugs():
                    self._client.publish(owner_topic(address), self._listener, qos=1, retain=True)
                self._client.subscribe("govee/h5082/+/owner", qos=1)
        print(f"DISCOVERY {count} listener={self._listener}", flush=True)

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties) -> None:
        if getattr(reason_code, "is_failure", False):
            print(f"MQTT_FAIL {reason_code}", flush=True)
            return
        print("MQTT_OK", flush=True)
        self.publish_config()

    def note_owner_claim(self, mac: str, host: str) -> None:
        """Another bridge's retained claim: warn on a clash, drop our own stale claim."""
        if len(mac) != MAC_HEX_LEN or not host:
            return
        address = ":".join(mac[i : i + 2] for i in range(0, MAC_HEX_LEN, 2)).upper()
        if self.owns(address) and host != self._listener:
            print(
                f"OWNER_CONFLICT {_short(address)} also claimed by {host}; remove it from "
                f"H5082_PLUGS on one Pi",
                flush=True,
            )
        elif not self.owns(address) and host == self._listener:
            # We owned it before a restart with a new allowlist: release the claim.
            self._client.publish(owner_topic(address), "", qos=1, retain=True)
            print(f"OWNER_RELEASE {_short(address)}", flush=True)

    def _on_message(self, _client, _userdata, message) -> None:
        parts = message.topic.split("/")
        if len(parts) == OWNER_TOPIC_PARTS and parts[3] == "owner":
            self.note_owner_claim(parts[2], message.payload.decode("utf-8", "replace").strip())
            return
        if len(parts) != 5 or parts[4] != "set":
            return
        mac = parts[2]
        side = parts[3]
        if side not in ("left", "right"):
            return
        address = ":".join(mac[i : i + 2] for i in range(0, 12, 2)).upper()
        if not self.owns(address):
            # Another Pi's bridge owns this plug; never touch it from here.
            print(f"NOT_OWNER {_short(address)} {side}", flush=True)
            return
        text = message.payload.decode("utf-8", "replace").strip().upper()
        if text not in ("ON", "OFF"):
            print(f"BAD_PAYLOAD {_short(address)} {side} {text[:16]!r}", flush=True)
            return
        loop = self._loop
        if loop is None:
            print(f"NOT_READY {_short(address)} {side}", flush=True)
            return
        future = asyncio.run_coroutine_threadsafe(self.command(address, side, text == "ON"), loop)
        future.add_done_callback(_log_task_error(f"command {_short(address)} {side}"))

    async def command(self, address: str, side: str, turn_on: bool) -> None:
        if not self.owns(address):
            print(f"NOT_OWNER {_short(address)} {side}", flush=True)
            return
        token = self._keys.get(address)
        if not token:
            print(f"NO_KEY {_short(address)} {side}", flush=True)
            current = self._state.get((address, side))
            if current is not None:
                self.publish_state(address, side, current)
            return
        self._desired[(address, side)] = turn_on
        self._wake.setdefault(address, asyncio.Event()).set()
        worker = self._workers.get(address)
        if worker is None or worker.done():
            task = asyncio.create_task(self._plug_worker(address, token))
            task.add_done_callback(_log_task_error(f"worker {_short(address)}"))
            self._workers[address] = task

    def _link(self, address: str, token: str) -> PlugLink:
        link = self._links.get(address)
        if link is None:
            link = PlugLink(address, self._adapter, token, self._adapter_lock)
            self._links[address] = link
        return link

    async def _plug_worker(self, address: str, token: str) -> None:
        """Apply the latest desired state for each socket of one plug, then linger."""
        link = self._link(address, token)
        wake = self._wake.setdefault(address, asyncio.Event())
        try:
            while True:
                wake.clear()
                pending = [
                    (side, self._desired.pop((address, side)))
                    for side in ("left", "right")
                    if (address, side) in self._desired
                ]
                if pending:
                    for side, want in pending:
                        await self._apply(link, address, side, want)
                    continue
                if not link.connected:
                    return
                if IDLE_DISCONNECT_S <= 0:
                    await wake.wait()
                    continue
                try:
                    await asyncio.wait_for(wake.wait(), timeout=IDLE_DISCONNECT_S)
                except asyncio.TimeoutError:
                    if any(key[0] == address for key in self._desired):
                        continue
                    await link.close()
                    print(f"LINK_IDLE {_short(address)}", flush=True)
                    if any(key[0] == address for key in self._desired):
                        continue  # a command arrived while closing
                    return
        finally:
            if self._workers.get(address) is asyncio.current_task():
                self._workers.pop(address, None)

    async def _apply(self, link: PlugLink, address: str, side: str, turn_on: bool) -> bool:
        tag = f"{_short(address)} {side}"
        for attempt in range(1, RETRIES + 1):
            if attempt > 1 and (address, side) in self._desired:
                print(f"SUPERSEDED {tag} {payload_for(turn_on)}", flush=True)
                return False
            try:
                await link.send(side, turn_on)
            except Exception as exc:
                print(
                    f"GATT {tag} {payload_for(turn_on)} try {attempt}/{RETRIES} "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )
                await link.close()
                if attempt < RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF_S[min(attempt, len(RETRY_BACKOFF_S)) - 1])
                continue
            self._hold[(address, side)] = time.monotonic() + HOLD_S
            self.publish_state(address, side, turn_on)
            extra = f" try {attempt}" if attempt > 1 else ""
            print(f"SET {tag} {payload_for(turn_on)}{extra}", flush=True)
            return True
        if (address, side) in self._desired:
            print(f"SUPERSEDED {tag} {payload_for(turn_on)}", flush=True)
            return False
        current = self._state.get((address, side))
        if current is not None:
            self.publish_state(address, side, current)
        print(f"SET_FAIL {tag} {payload_for(turn_on)}", flush=True)
        return False

    def note_advertisement(self, address: str, last: int) -> None:
        address = address.upper()
        if not self.owns(address):
            return  # the owning Pi publishes this plug's state
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
            if not str(path).startswith(f"/org/bluez/{self._adapter}/dev_"):
                continue
            dev = ifaces.get("org.bluez.Device1")
            if not dev:
                continue
            address = str(unwrap(dev.get("Address") or "")).upper()
            if address not in wanted:
                continue
            paths[address] = str(path)
            rssi = unwrap(dev.get("RSSI"))
            if isinstance(rssi, int):
                self.publish_rssi(address, rssi)
            last = mfr_last(dev.get("ManufacturerData"))
            if last is not None and not self._rssi_only:
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
                    props = proxy.get_interface("org.freedesktop.DBus.Properties")
                    try:
                        rssi = unwrap(await props.call_get("org.bluez.Device1", "RSSI"))
                    except Exception:
                        rssi = None
                    if isinstance(rssi, int):
                        self.publish_rssi(address, rssi)
                    if self._rssi_only:
                        continue
                    raw = await props.call_get("org.bluez.Device1", "ManufacturerData")
                except Exception:
                    continue
                last = mfr_last(raw)
                if last is not None:
                    self.note_advertisement(address, last)
            await asyncio.sleep(10)

    def startup_report(self) -> None:
        print(self.describe(), flush=True)
        if self._rssi_only:
            return
        if self._key_problem:
            print(f"KEY_FILE {key_path()} {self._key_problem}", flush=True)
        for address, _name in self.owned_plugs():
            if address not in self._keys:
                print(f"NO_KEY_OWNED {_short(address)} (copy its line into {key_path()})", flush=True)

    async def run(self) -> None:
        self.startup_report()
        self._loop = asyncio.get_running_loop()
        self._client.connect(self._host, self._port)
        self._client.loop_start()
        try:
            await self.watch()
        finally:
            for task in list(self._workers.values()):
                task.cancel()
            for link in list(self._links.values()):
                await link.close()
            if not self._rssi_only:
                self._client.publish(self._avail, "offline", qos=1, retain=True)
            self._client.loop_stop()
            self._client.disconnect()


def main() -> None:
    asyncio.run(Bridge().run())


if __name__ == "__main__":
    main()
