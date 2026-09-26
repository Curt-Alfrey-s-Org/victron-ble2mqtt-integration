#!/usr/bin/env python3
"""Create editable load-name and normal/dump helpers for each H5082 socket.

Official websocket helpers:
  input_text/create
  input_select/create
  https://developers.home-assistant.io/docs/api/websocket/

Does not print the token. Skips helpers that already exist.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENERGY = ROOT / "scripts" / "save_solar_plant_energy_prefs.py"
SUFFIXES = ("2f9d", "3013", "3ec9", "82fb", "9607", "c061", "c38d", "cf79")
SIDES = ("left", "right")


def _energy():
    spec = importlib.util.spec_from_file_location("energy", ENERGY)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {ENERGY}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    energy = _energy()
    token = energy.load_token(None)
    ws = energy.ws_connect(os.environ.get("HA_URL", "http://127.0.0.1:8123"))
    hello = energy.recv_text(ws)
    if hello.get("type") != "auth_required":
        raise SystemExit("expected auth_required")
    energy.send_frame(
        ws,
        energy.OP_TEXT,
        json.dumps({"type": "auth", "access_token": token}).encode(),
    )
    if energy.recv_text(ws).get("type") != "auth_ok":
        raise SystemExit("auth failed")
    existing = energy.ws_call(ws, 1, {"type": "config/entity_registry/list"})
    have = set()
    if isinstance(existing, list):
        have = {row.get("entity_id") for row in existing if isinstance(row, dict)}
    elif isinstance(existing, dict):
        have = {row.get("entity_id") for row in existing.get("entities") or [] if isinstance(row, dict)}
    msg_id = 2

    def create(payload: dict, entity_id: str) -> None:
        nonlocal msg_id
        if entity_id in have:
            print("SKIP", entity_id)
            return
        try:
            result = energy.ws_call(ws, msg_id, payload)
        except RuntimeError as exc:
            print("SKIP", payload["name"], str(exc).split(" failed: ", 1)[-1])
        else:
            print("CREATED", payload["name"], result.get("id") or result)
        msg_id += 1

    for suffix in SUFFIXES:
        label = suffix.upper()
        where = {
            "type": "input_text/create",
            "name": f"H5082 {label} location",
            "initial": "",
            "min": 0,
            "max": 64,
            "icon": "mdi:map-marker",
        }
        create(where, f"input_text.h5082_{suffix}_location")
    for suffix in SUFFIXES:
        for side in SIDES:
            label = suffix.upper()
            text_name = f"H5082 {label} {side} load"
            select_name = f"H5082 {label} {side} use"
            create(
                {
                    "type": "input_text/create",
                    "name": text_name,
                    "initial": "",
                    "min": 0,
                    "max": 64,
                    "icon": "mdi:tag-text",
                },
                f"input_text.h5082_{suffix}_{side}_load",
            )
            create(
                {
                    "type": "input_select/create",
                    "name": select_name,
                    "options": ["normal", "dump"],
                    "initial": "normal",
                    "icon": "mdi:toggle-switch",
                },
                f"input_select.h5082_{suffix}_{side}_use",
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
