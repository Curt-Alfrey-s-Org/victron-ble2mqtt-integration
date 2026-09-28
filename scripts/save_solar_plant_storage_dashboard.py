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

NON-DESTRUCTIVE BY DEFAULT (2026-09-28). This script used to overwrite /site-solar
with the repo seed every time it ran, wiping cards you moved or edited in the UI.
Now it:
  1. always backs up the live dashboard config first (git-ignored folder, default
     <repo>/.backups/site-solar/<stamp>-before-seed/dashboard-site-solar.json);
  2. creates the dashboard and saves the seed only when /site-solar has no saved
     config yet;
  3. otherwise REFUSES and exits 3, unless you pass --force.
--dry-run shows what would happen and writes nothing to HA.
Undo a --force: python3 scripts/site_solar_settings.py restore --from <folder> --dashboard
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "config" / "dashboards" / "solar-plant.yaml"
SETTINGS_MOD = ROOT / "scripts" / "site_solar_settings.py"
URL_PATH = "site-solar"
TITLE = "Site solar"
ICON = "mdi:solar-power"
EXIT_REFUSED = 3


def _settings():
    spec = importlib.util.spec_from_file_location("site_solar_settings", SETTINGS_MOD)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {SETTINGS_MOD}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def decide(live: dict[str, Any] | None, seed: dict[str, Any], force: bool) -> str:
    """What to do with the seed: 'save' (nothing saved yet or --force),
    'same' (live already equals the seed) or 'refuse' (live has edits, no --force)."""
    if live is None or not live.get("views"):
        return "save"
    if live == seed:
        return "same"
    return "save" if force else "refuse"


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
    parser = argparse.ArgumentParser(
        description="Save the repo Site solar seed as a storage dashboard (refuses to "
        "overwrite an existing dashboard without --force)"
    )
    parser.add_argument("--url", default=os.environ.get("HA_URL", "http://192.168.0.105:8123"))
    parser.add_argument("--token-file", type=Path, default=None)
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite the live /site-solar config (it is backed up first)",
    )
    parser.add_argument("--dry-run", action="store_true", help="report only; write nothing to HA")
    parser.add_argument(
        "--backup-dir", default=None, help="backup root (see site_solar_settings.py)"
    )
    args = parser.parse_args(argv)
    settings = _settings()
    config = load_seed_config()
    session = settings.Session(args.url, args.token_file)
    try:
        listed = session.call({"type": "lovelace/dashboards/list"})
        if not isinstance(listed, list):
            listed = []
        paths = {row.get("url_path") for row in listed if isinstance(row, dict)}
        exists = URL_PATH in paths
        live = settings.fetch_dashboard(session, URL_PATH) if exists else None
        if live is not None:
            root = settings.backup_root(args.backup_dir)
            folder = settings.new_backup_dir(root, "before-seed")
            settings.write_json(folder / settings.DASHBOARD_FILE, live)
            print(f"[site-solar] backed up live dashboard -> {folder / settings.DASHBOARD_FILE}")
        action = decide(live, config, args.force)
        if action == "same":
            print(f"[site-solar] /{URL_PATH} already matches the repo seed; nothing to do")
            return 0
        if action == "refuse":
            print(
                f"[site-solar] REFUSED: /{URL_PATH} already has a saved config (your UI edits).\n"
                "  Nothing was changed. Your current config was backed up above.\n"
                "  To replace it with the repo seed anyway, rerun with --force.\n"
                "  To save your settings instead: python3 scripts/site_solar_settings.py export",
                file=sys.stderr,
            )
            return EXIT_REFUSED
        if args.dry_run:
            verb = "create and save" if not exists else "overwrite"
            print(
                f"[site-solar] dry run: would {verb} /{URL_PATH} with {len(config['views'])} seed views"
            )
            return 0
        if not exists:
            session.call(create_dashboard_payload())
            print(f"[site-solar] created storage dashboard {URL_PATH}")
        session.call({"type": "lovelace/config/save", "url_path": URL_PATH, "config": config})
        print(f"[site-solar] saved {len(config.get('views') or [])} views; open /{URL_PATH}")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
