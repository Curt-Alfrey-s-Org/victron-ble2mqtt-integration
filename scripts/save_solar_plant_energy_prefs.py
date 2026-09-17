#!/usr/bin/env python3
"""Apply Solar plant Energy sources via Home Assistant energy/save_prefs.

Official:
  https://developers.home-assistant.io/docs/api/websocket/
  https://github.com/home-assistant/core/blob/master/homeassistant/components/energy/websocket_api.py
WebSocket frames: RFC 6455 https://www.rfc-editor.org/rfc/rfc6455.html#section-5.2

Does not add grid, carbon/Electricity Maps, gas, water, or KU equal-share solar.
Token is never printed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import struct
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
OP_TEXT = 0x1
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

# Canonical Energy prefs for this site (docs/SOLAR_HA_DASHBOARD.md).
ENERGY_SOURCES: list[dict[str, Any]] = [
    {
        "type": "solar",
        "stat_energy_from": "sensor.t2_mppt_energy_kwh",
        "stat_rate": "sensor.solar_controller_solar",
        "config_entry_solar_forecast": None,
        "name": "T2 MPPT",
    },
    {
        "type": "battery",
        "stat_energy_from": "sensor.battery_1_discharge_energy_kwh",
        "stat_energy_to": "sensor.battery_1_charge_energy_kwh",
        "stat_soc": "sensor.battery_1_state_of_charge",
        "power_config": {
            "stat_rate_from": "sensor.battery_1_discharge_power",
            "stat_rate_to": "sensor.battery_1_charge_power",
        },
        "name": "Battery 1 T2",
    },
    {
        "type": "battery",
        "stat_energy_from": "sensor.battery_2_discharge_energy_kwh",
        "stat_energy_to": "sensor.battery_2_charge_energy_kwh",
        "stat_soc": "sensor.battery_2_state_of_charge",
        "power_config": {
            "stat_rate_from": "sensor.battery_2_discharge_power",
            "stat_rate_to": "sensor.battery_2_charge_power",
        },
        "name": "Battery 2 KU",
    },
]

DEVICE_CONSUMPTION: list[dict[str, Any]] = [
    {
        "stat_consumption": "sensor.em16_a3_energy_kwh",
        "stat_rate": "sensor.trailer_outlet_power",
        "name": "Trailer A/C",
    },
    {
        "stat_consumption": "sensor.sungold_load_energy_kwh",
        "stat_rate": "sensor.sungold_sph302480a_load_power",
        "name": "Sungold A/C out",
    },
    {
        "stat_consumption": "sensor.sim_dump_energy_kwh",
        "stat_rate": "sensor.sim_dump_load_power",
        "name": "Sim dump",
    },
]


def energy_save_payload() -> dict[str, Any]:
    """Body for energy/save_prefs (id/type added by the WS client)."""
    return {
        "energy_sources": ENERGY_SOURCES,
        "device_consumption": DEVICE_CONSUMPTION,
        "device_consumption_water": [],
    }


class _Ws:
    def __init__(self, sock: socket.socket, leftover: bytes = b"") -> None:
        self.sock = sock
        self.buf = bytearray(leftover)

    def recvexact(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(max(n - len(self.buf), 4096))
            if not chunk:
                raise ConnectionError("websocket closed")
            self.buf.extend(chunk)
        out = bytes(self.buf[:n])
        del self.buf[:n]
        return out


def _mask(payload: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % 4] for i, b in enumerate(payload))


def send_frame(ws: _Ws, opcode: int, payload: bytes) -> None:
    key = os.urandom(4)
    masked = _mask(payload, key)
    header = bytearray()
    header.append(0x80 | opcode)
    n = len(payload)
    if n < 126:
        header.append(0x80 | n)
    elif n < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", n))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", n))
    header.extend(key)
    ws.sock.sendall(header + masked)


def recv_frame(ws: _Ws) -> tuple[int, bytes]:
    hdr = ws.recvexact(2)
    opcode = hdr[0] & 0x0F
    masked = bool(hdr[1] & 0x80)
    length = hdr[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", ws.recvexact(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", ws.recvexact(8))[0]
    mask = ws.recvexact(4) if masked else b""
    payload = ws.recvexact(length)
    if masked:
        payload = _mask(payload, mask)
    return opcode, payload


def recv_text(ws: _Ws) -> dict[str, Any]:
    while True:
        opcode, payload = recv_frame(ws)
        if opcode == OP_PING:
            send_frame(ws, OP_PONG, payload)
            continue
        if opcode == OP_CLOSE:
            raise ConnectionError("websocket close")
        if opcode != OP_TEXT:
            continue
        return json.loads(payload.decode("utf-8"))


def ws_connect(url: str, timeout: float = 20) -> _Ws:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "ws"):
        raise ValueError("HA_URL must be http:// or ws:// (LAN HTTP)")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8123
    sock = socket.create_connection((host, port), timeout=timeout)
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    req = (
        f"GET /api/websocket HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    )
    sock.sendall(req.encode("ascii"))
    raw = b""
    while b"\r\n\r\n" not in raw:
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("no websocket handshake")
        raw += chunk
    head, _, leftover = raw.partition(b"\r\n\r\n")
    status = head.split(b"\r\n", 1)[0]
    if b"101" not in status:
        raise ConnectionError(f"websocket upgrade failed: {status!r}")
    expect = base64.b64encode(hashlib.sha1((key + WS_GUID).encode("ascii")).digest())
    if expect not in head:
        raise ConnectionError("Sec-WebSocket-Accept mismatch")
    return _Ws(sock, leftover)


def ws_call(ws: _Ws, msg_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body["id"] = msg_id
    send_frame(ws, OP_TEXT, json.dumps(body).encode("utf-8"))
    while True:
        reply = recv_text(ws)
        if reply.get("id") != msg_id:
            continue
        if not reply.get("success"):
            err = reply.get("error") or {}
            raise RuntimeError(
                f"{payload.get('type')} failed: {err.get('code')} {err.get('message')}"
            )
        return reply.get("result") or {}


def load_token(token_file: Path | None) -> str:
    env = os.environ.get("HA_TOKEN", "").strip()
    if env:
        return env
    path_raw = os.environ.get("HA_TOKEN_FILE", "").strip()
    path = token_file or (Path(path_raw) if path_raw else None)
    if path is None:
        raise SystemExit("Set HA_TOKEN or HA_TOKEN_FILE (long-lived token, not in git)")
    return path.read_text(encoding="utf-8").strip()


def summarize(prefs: dict[str, Any]) -> None:
    print("energy_sources:")
    for src in prefs.get("energy_sources") or []:
        print(" ", src.get("type"), src.get("name") or "", src.get("stat_energy_from") or "")
    print("device_consumption:")
    for dev in prefs.get("device_consumption") or []:
        print(" ", dev.get("name"), dev.get("stat_consumption"), dev.get("stat_rate"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Save Solar plant Energy prefs over HA websocket")
    parser.add_argument("--url", default=os.environ.get("HA_URL", "http://192.168.0.105:8123"))
    parser.add_argument("--token-file", type=Path, default=None)
    args = parser.parse_args(argv)
    token = load_token(args.token_file)
    ws = ws_connect(args.url)
    try:
        hello = recv_text(ws)
        if hello.get("type") != "auth_required":
            raise RuntimeError(f"expected auth_required, got {hello.get('type')}")
        send_frame(
            ws,
            OP_TEXT,
            json.dumps({"type": "auth", "access_token": token}).encode("utf-8"),
        )
        auth = recv_text(ws)
        if auth.get("type") != "auth_ok":
            raise RuntimeError("HA websocket auth failed")
        saved = ws_call(ws, 1, {"type": "energy/save_prefs", **energy_save_payload()})
        summarize(saved)
        ws_call(ws, 2, {"type": "energy/validate"})
        print("energy/validate ok")
    finally:
        try:
            send_frame(ws, OP_CLOSE, b"")
        except OSError:
            pass
        ws.sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
