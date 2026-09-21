#!/usr/bin/env python3
"""Purge recorder states and long-term statistics for solar plant entities on HA.

Official:
  https://www.home-assistant.io/integrations/recorder/#actions
  https://www.home-assistant.io/actions/recorder/purge_entities/
  homeassistant/components/recorder/websocket_api.py (recorder/clear_statistics)

Requires admin long-lived token (HA_TOKEN or HA_TOKEN_FILE). Destructive: use
--dry-run first, then --apply after deploy of fixed solar_plant.yaml.

Does not change VictronConnect or MQTT device logs -- only Home Assistant DB.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HIST_MOD = ROOT / "scripts" / "solar_plant_history_entities.py"
SAVE_MOD = ROOT / "scripts" / "save_solar_plant_energy_prefs.py"
PURGE_CHUNK = 40


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_save_module():
    return _load_module(SAVE_MOD, "save_solar_plant_energy_prefs")


def _load_hist_module():
    return _load_module(HIST_MOD, "solar_plant_history_entities")


def ha_get_states(url: str, token: str) -> list[str]:
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/states",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        rows = json.loads(resp.read().decode("utf-8"))
    return [row["entity_id"] for row in rows if row.get("entity_id")]


def purge_entities_rest(url: str, token: str, entity_ids: list[str]) -> None:
    """recorder.purge_entities with keep_days 0."""
    for i in range(0, len(entity_ids), PURGE_CHUNK):
        chunk = entity_ids[i : i + PURGE_CHUNK]
        body = json.dumps({"keep_days": 0, "entity_id": chunk}).encode("utf-8")
        req = urllib.request.Request(
            f"{url.rstrip('/')}/api/services/recorder/purge_entities",
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"purge_entities HTTP {exc.code}: {detail}") from exc
        print(f"purge_entities ok ({i + 1}-{i + len(chunk)} of {len(entity_ids)})")


def list_statistic_ids(ws_mod: Any, ws: Any, msg_id: int) -> list[str]:
    result = ws_mod.ws_call(ws, msg_id, {"type": "recorder/list_statistic_ids"})
    if isinstance(result, list):
        return [row["statistic_id"] for row in result if row.get("statistic_id")]
    return []


def statistic_ids_for_entities(
    all_stats: list[str], entity_ids: list[str]
) -> list[str]:
    want = set(entity_ids)
    out = [sid for sid in all_stats if sid in want]
    return sorted(set(out))


def clear_statistics_ws(
    ws_mod: Any, ws: Any, msg_id: int, statistic_ids: list[str]
) -> int:
    """Return next free websocket message id (ids must increase per HA WS API)."""
    for i in range(0, len(statistic_ids), PURGE_CHUNK):
        chunk = statistic_ids[i : i + PURGE_CHUNK]
        ws_mod.ws_call(
            ws,
            msg_id,
            {"type": "recorder/clear_statistics", "statistic_ids": chunk},
        )
        msg_id += 1
        print(
            f"clear_statistics ok ({i + 1}-{i + len(chunk)} of {len(statistic_ids)})"
        )
    return msg_id


def ws_session(ws_mod: Any, url: str, token: str):
    ws = ws_mod.ws_connect(url)
    hello = ws_mod.recv_text(ws)
    if hello.get("type") != "auth_required":
        raise RuntimeError(f"expected auth_required, got {hello.get('type')}")
    ws_mod.send_frame(
        ws,
        ws_mod.OP_TEXT,
        json.dumps({"type": "auth", "access_token": token}).encode("utf-8"),
    )
    auth = ws_mod.recv_text(ws)
    if auth.get("type") != "auth_ok":
        raise RuntimeError("HA websocket auth failed")
    return ws


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Purge HA recorder history for solar plant entities"
    )
    parser.add_argument("--url", default=os.environ.get("HA_URL", "http://192.168.0.105:8123"))
    parser.add_argument("--token-file", type=Path, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List entity count only (default if --apply omitted)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Run purge_entities and clear_statistics",
    )
    args = parser.parse_args(argv)
    if not args.apply:
        args.dry_run = True

    save = _load_save_module()
    hist = _load_hist_module()
    token = save.load_token(args.token_file)

    discovered = ha_get_states(args.url, token)
    entity_ids = hist.merge_purge_entity_ids(discovered)
    print(f"solar purge targets: {len(entity_ids)} entities")
    if args.dry_run:
        for eid in entity_ids:
            print(f"  {eid}")
        print("dry-run only; pass --apply to purge recorder + statistics")
        return 0

    purge_entities_rest(args.url, token, entity_ids)

    ws_mod = save
    ws = ws_session(ws_mod, args.url, token)
    try:
        msg_id = 1
        all_stats = list_statistic_ids(ws_mod, ws, msg_id)
        msg_id += 1
        stat_ids = statistic_ids_for_entities(all_stats, entity_ids)
        print(f"clear_statistics targets: {len(stat_ids)} statistic_ids")
        if stat_ids:
            clear_statistics_ws(ws_mod, ws, msg_id, stat_ids)
        else:
            print("no matching statistic_ids (states purge still ran)")
    finally:
        try:
            ws_mod.send_frame(ws, ws_mod.OP_CLOSE, b"")
        except OSError:
            pass
        ws.sock.close()

    print("done: solar plant HA history purged; new samples start clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
