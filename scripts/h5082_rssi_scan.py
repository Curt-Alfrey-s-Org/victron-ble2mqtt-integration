#!/usr/bin/env python3
"""Read-only: how well does this Pi hear each Govee H5082 plug?

    /home/n4s1/govee-ble-venv/bin/python scripts/h5082_rssi_scan.py --adapter hci1 --seconds 30

Scans on one adapter for a while and prints, per plug, how many advertisements were
heard and the best / average RSSI. It never connects, never sends a command and never
reads the key file, so it is safe next to a running bridge. Run it on each Pi and give
each plug to the Pi that hears it best (H5082_PLUGS, see docs/H5082_MULTI_BRIDGE.md).

A plug that a bridge is connected to stops advertising until the link goes idle
(about 2 minutes), so a plug that was just switched may show no samples.
On the Pi 4, hci0 is the Victron adapter; this script refuses to scan there.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from govee_h5082.mqtt_bridge import PLUGS  # noqa: E402


def adapter_kwargs(adapter: str) -> dict:
    """bleak >= 3 takes bluez={"adapter": ...}; older bleak needs adapter=."""
    from importlib.metadata import version  # noqa: PLC0415

    try:
        major = int(version("bleak").split(".")[0])
    except Exception:  # noqa: BLE001 - unknown version: assume current API
        major = 3
    return {"bluez": {"adapter": adapter}} if major >= 3 else {"adapter": adapter}  # noqa: PLR2004

VICTRON_HOSTS = {"pi4"}  # hosts whose hci0 belongs to Victron


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--adapter",
        default=os.environ.get("H5082_ADAPTER"),
        help="BlueZ adapter, e.g. hci1 on the Pi 4 or hci0 on the Pi 5 (default: $H5082_ADAPTER)",
    )
    parser.add_argument("--seconds", type=float, default=20.0, help="scan time (default 20)")
    parser.add_argument(
        "--host",
        default=os.environ.get("H5082_LISTENER") or socket.gethostname(),
        help="host id, used only for the Victron hci0 guard (default: $H5082_LISTENER or hostname)",
    )
    args = parser.parse_args(argv)
    if not args.adapter or not re.fullmatch(r"hci[0-9]+", args.adapter):
        parser.error("--adapter hciN is required (or set H5082_ADAPTER)")
    if args.adapter == "hci0" and args.host in VICTRON_HOSTS:
        parser.error(f"{args.host}: hci0 is the Victron adapter; use --adapter hci1")
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    return args


class Tally:
    def __init__(self) -> None:
        self.samples: dict[str, list[int]] = {address: [] for address, _name in PLUGS}
        self.last_seen: dict[str, float] = {}

    def add(self, address: str, rssi: int | None, when: float) -> None:
        address = address.upper()
        if address in self.samples and rssi is not None:
            self.samples[address].append(int(rssi))
            self.last_seen[address] = when

    def rows(self, now: float) -> list[str]:
        out = [f"{'plug':<6}{'samples':>8}{'best':>6}{'avg':>7}{'last':>7}"]
        for address, _name in PLUGS:
            plug = address.replace(":", "")[-4:]
            got = self.samples[address]
            if not got:
                out.append(f"{plug:<6}{0:>8}{'-':>6}{'-':>7}{'-':>7}")
                continue
            age = f"{now - self.last_seen[address]:.0f}s"
            avg = sum(got) / len(got)
            out.append(f"{plug:<6}{len(got):>8}{max(got):>6}{avg:>7.1f}{age:>7}")
        return out


async def scan(adapter: str, seconds: float) -> Tally:
    from bleak import BleakScanner  # noqa: PLC0415 - only needed on the Pi

    tally = Tally()

    def seen(device, adv) -> None:
        tally.add(device.address, getattr(adv, "rssi", None), time.monotonic())

    async with BleakScanner(detection_callback=seen, **adapter_kwargs(adapter)):
        await asyncio.sleep(seconds)
    return tally


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(f"scanning {args.adapter} for {args.seconds:.0f}s on {args.host} (read-only)", flush=True)
    tally = asyncio.run(scan(args.adapter, args.seconds))
    print("\n".join(tally.rows(time.monotonic())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
