#!/usr/bin/env python3
"""Decide whether Pi4 Theengs may start on this host.

BlueZ Adapter StartDiscovery: each client may hold one discovery session per
adapter. StopDiscovery releases only that client's session; discovery continues
until every client has stopped.
https://manpages.ubuntu.com/manpages/noble/man5/org.bluez.Adapter.5.html

Theengs Gateway documents --adapter and --blacklist; sharing one adapter with
victron_ble2mqtt is not.
https://gateway.theengs.io/use/use.html

Exit 0: Pi4 Theengs may start (ENABLE_PI4_THEENGS=1 and HCI names differ).
Exit 1: do not start; tear down leftover pi4-theengs (Compose --profile down).
https://docs.docker.com/compose/how-tos/profiles/
"""
from __future__ import annotations

import os
import sys

DEFAULT_ADAPTER = "hci0"


def normalize_adapter(name: str | None) -> str:
    value = (name or "").strip().lower()
    return value or DEFAULT_ADAPTER


def may_start_pi4_theengs(
    enable_pi4_theengs: str | None,
    ble_adapter: str | None,
    theengs_adapter: str | None,
) -> tuple[bool, str]:
    """Return (ok, reason). ok True only when flag is 1 and adapters differ."""
    flag = (enable_pi4_theengs or "0").strip()
    if flag != "1":
        return (
            False,
            "ENABLE_PI4_THEENGS is not 1; onboard HCI stays exclusive to victron_ble2mqtt",
        )
    victron = normalize_adapter(ble_adapter)
    theengs = normalize_adapter(theengs_adapter)
    if victron == theengs:
        return (
            False,
            (
                f"ENABLE_PI4_THEENGS=1 but THEENGS_ADAPTER={theengs} matches "
                f"BLE_ADAPTER={victron}; BlueZ one StartDiscovery session per "
                "client per adapter"
            ),
        )
    return (
        True,
        f"ENABLE_PI4_THEENGS=1 and adapters differ (Victron {victron}, Theengs {theengs})",
    )


def main(argv: list[str] | None = None) -> int:
    del argv
    ok, reason = may_start_pi4_theengs(
        os.environ.get("ENABLE_PI4_THEENGS"),
        os.environ.get("BLE_ADAPTER") or os.environ.get("VICTRON_BLE_ADAPTER"),
        os.environ.get("THEENGS_ADAPTER"),
    )
    print(reason)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
