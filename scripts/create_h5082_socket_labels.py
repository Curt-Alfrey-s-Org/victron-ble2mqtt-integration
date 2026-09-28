#!/usr/bin/env python3
"""Create editable load-name and normal/dump helpers for each H5082 socket.

Official websocket helpers:
  input_text/create, input_text/list, input_text/update
  input_select/create, input_select/list, input_select/update
  https://developers.home-assistant.io/docs/api/websocket/
  Collection update replaces the stored item:
  https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/collection.py

Why no `initial`: a UI/storage input_text or input_select that has `initial` in
.storage/input_text / .storage/input_select is put back to that value at EVERY
Home Assistant restart; the value you typed is not restored
(homeassistant/components/input_text/__init__.py and input_select/__init__.py:
async_added_to_hass returns early when an initial value is set). The first version of
this script created every helper with initial "" / "normal", which is why Where, Load
and Use reset to blank / normal after each restart.

Default run (safe to repeat, never changes a value you set):
  * creates only helpers that are missing, without `initial` (new text helpers are set
    to "" once, right after creation, so they do not show "unknown");
  * removes `initial` from the existing H5082 storage helpers (name, icon, options,
    min/max are kept exactly as stored; the current value is not touched).
Pass --no-strip-initial to skip the second step, --dry-run to only report.

Does not print the token.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

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


def helper_payloads() -> list[tuple[dict[str, Any], str]]:
    """(create payload, entity_id) for every H5082 helper. Names set the entity ids;
    do not change them. No payload carries `initial`."""
    out: list[tuple[dict[str, Any], str]] = []
    for suffix in SUFFIXES:
        label = suffix.upper()
        out.append(
            (
                {
                    "type": "input_text/create",
                    "name": f"H5082 {label} location",
                    "min": 0,
                    "max": 64,
                    "icon": "mdi:map-marker",
                },
                f"input_text.h5082_{suffix}_location",
            )
        )
    for suffix in SUFFIXES:
        for side in SIDES:
            label = suffix.upper()
            out.append(
                (
                    {
                        "type": "input_text/create",
                        "name": f"H5082 {label} {side} load",
                        "min": 0,
                        "max": 64,
                        "icon": "mdi:tag-text",
                    },
                    f"input_text.h5082_{suffix}_{side}_load",
                )
            )
            out.append(
                (
                    {
                        "type": "input_select/create",
                        "name": f"H5082 {label} {side} use",
                        # First option is what a brand-new select starts on: normal.
                        "options": ["normal", "dump"],
                        "icon": "mdi:toggle-switch",
                    },
                    f"input_select.h5082_{suffix}_{side}_use",
                )
            )
    return out


def managed_entity_ids() -> set[str]:
    return {eid for _payload, eid in helper_payloads()}


def strip_initial_update(domain: str, item: dict[str, Any]) -> dict[str, Any] | None:
    """Websocket update body that keeps every stored field except `initial`.

    Returns None when the item has no `initial` (nothing to do)."""
    if "initial" not in item or "id" not in item:
        return None
    body: dict[str, Any] = {"type": f"{domain}/update", f"{domain}_id": item["id"]}
    for key, value in item.items():
        if key in ("id", "initial"):
            continue
        body[key] = value
    return body


def _registry_map(rows: Any) -> dict[tuple[str, str], str]:
    """(platform, unique_id) -> entity_id from config/entity_registry/list."""
    if isinstance(rows, dict):
        rows = rows.get("entities") or []
    out: dict[tuple[str, str], str] = {}
    for row in rows or []:
        if isinstance(row, dict) and row.get("unique_id") and row.get("entity_id"):
            out[(str(row.get("platform")), str(row["unique_id"]))] = str(row["entity_id"])
    return out


class _Client:
    def __init__(self, url: str, token_file: Path | None) -> None:
        self.energy = _energy()
        token = self.energy.load_token(token_file)
        self.ws = self.energy.ws_connect(url)
        self.msg_id = 0
        if self.energy.recv_text(self.ws).get("type") != "auth_required":
            raise SystemExit("expected auth_required")
        self.energy.send_frame(
            self.ws,
            self.energy.OP_TEXT,
            json.dumps({"type": "auth", "access_token": token}).encode(),
        )
        if self.energy.recv_text(self.ws).get("type") != "auth_ok":
            raise SystemExit("auth failed")

    def call(self, payload: dict[str, Any]) -> Any:
        self.msg_id += 1
        return self.energy.ws_call(self.ws, self.msg_id, payload)


def create_missing(client: _Client, have: set[str], dry_run: bool) -> None:
    for payload, entity_id in helper_payloads():
        if entity_id in have:
            print("SKIP", entity_id, "(exists)")
            continue
        if dry_run:
            print("WOULD CREATE", entity_id)
            continue
        try:
            result = client.call(payload)
        except RuntimeError as exc:
            print("SKIP", payload["name"], str(exc).split(" failed: ", 1)[-1])
            continue
        print("CREATED", payload["name"], (result or {}).get("id") or result)
        if payload["type"] != "input_text/create":
            continue
        try:
            client.call(
                {
                    "type": "call_service",
                    "domain": "input_text",
                    "service": "set_value",
                    "service_data": {"value": ""},
                    "target": {"entity_id": entity_id},
                }
            )
        except RuntimeError as exc:
            print("WARN could not blank", entity_id, str(exc).split(" failed: ", 1)[-1])


def strip_initials(client: _Client, reg: dict[tuple[str, str], str], dry_run: bool) -> int:
    managed = managed_entity_ids()
    stripped = 0
    for domain in ("input_text", "input_select"):
        items = client.call({"type": f"{domain}/list"})
        for item in items if isinstance(items, list) else []:
            body = strip_initial_update(domain, item)
            if body is None:
                continue
            entity_id = reg.get((domain, str(item.get("id"))), f"{domain}.{item.get('id')}")
            if entity_id not in managed:
                print("LEAVE", entity_id, "has initial (not an H5082 helper; not changed)")
            elif dry_run:
                print("WOULD STRIP initial", entity_id, repr(item.get("initial")))
            else:
                client.call(body)
                stripped += 1
                print("STRIPPED initial", entity_id, repr(item.get("initial")))
    return stripped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--url", default=os.environ.get("HA_URL", "http://127.0.0.1:8123"))
    parser.add_argument("--token-file", type=Path, default=None)
    parser.add_argument(
        "--no-strip-initial",
        action="store_true",
        help="do not remove `initial` from existing H5082 storage helpers",
    )
    parser.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    args = parser.parse_args(argv)

    client = _Client(args.url, args.token_file)
    reg = _registry_map(client.call({"type": "config/entity_registry/list"}))
    create_missing(client, set(reg.values()), args.dry_run)
    if args.no_strip_initial:
        return 0
    stripped = strip_initials(client, reg, args.dry_run)
    print(f"done: removed initial from {stripped} helper(s); values were not changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
