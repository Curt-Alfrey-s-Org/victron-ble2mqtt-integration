#!/usr/bin/env python3
"""Create or update Site solar as a storage Lovelace dashboard.

Official:
  https://www.home-assistant.io/dashboards/dashboards/#creating-a-new-dashboard
  https://github.com/home-assistant/core/blob/master/homeassistant/components/lovelace/dashboard.py
  lovelace/dashboards/create (mode storage)
  https://github.com/home-assistant/core/blob/master/homeassistant/components/lovelace/websocket.py
  lovelace/config/save
  https://developers.home-assistant.io/docs/api/websocket/

Does not register mode: yaml. Token is never printed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ENERGY_MOD = ROOT / "scripts" / "save_solar_plant_energy_prefs.py"
SEED = ROOT / "config" / "dashboards" / "solar-plant.yaml"
URL_PATH = "site-solar"
TITLE = "Site solar"
ICON = "mdi:solar-power"


def _energy():
    spec = importlib.util.spec_from_file_location("save_solar_plant_energy_prefs", ENERGY_MOD)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {ENERGY_MOD}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_seed_config(path: Path = SEED) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data.get("views"):
        raise ValueError(f"{path} must be a Lovelace config with views")
    return data


def create_dashboard_payload() -> dict[str, Any]:
    return {
        "type": "lovelace/dashboards/create",
        "url_path": URL_PATH,
        "title": TITLE,
        "icon": ICON,
        "show_in_sidebar": True,
        "require_admin": True,
        "mode": "storage",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Save Site solar storage dashboard over HA websocket")
    parser.add_argument("--url", default=os.environ.get("HA_URL", "http://192.168.0.105:8123"))
    parser.add_argument("--token-file", type=Path, default=None)
    args = parser.parse_args(argv)
    energy = _energy()
    token = energy.load_token(args.token_file)
    config = load_seed_config()
    ws = energy.ws_connect(args.url)
    try:
        hello = energy.recv_text(ws)
        if hello.get("type") != "auth_required":
            raise RuntimeError(f"expected auth_required, got {hello.get('type')}")
        energy.send_frame(
            ws,
            energy.OP_TEXT,
            json.dumps({"type": "auth", "access_token": token}).encode("utf-8"),
        )
        auth = energy.recv_text(ws)
        if auth.get("type") != "auth_ok":
            raise RuntimeError("HA websocket auth failed")
        listed = energy.ws_call(ws, 1, {"type": "lovelace/dashboards/list"})
        if not isinstance(listed, list):
            listed = []
        paths = {row.get("url_path") for row in listed if isinstance(row, dict)}
        if URL_PATH not in paths:
            energy.ws_call(ws, 2, create_dashboard_payload())
            print(f"[site-solar] created storage dashboard {URL_PATH}")
        else:
            print(f"[site-solar] storage dashboard {URL_PATH} already exists")
        energy.ws_call(
            ws,
            3,
            {
                "type": "lovelace/config/save",
                "url_path": URL_PATH,
                "config": config,
            },
        )
        print(f"[site-solar] saved {len(config.get('views') or [])} views; open /{URL_PATH}")
    finally:
        try:
            energy.send_frame(ws, energy.OP_CLOSE, b"")
        except OSError:
            pass
        ws.sock.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
