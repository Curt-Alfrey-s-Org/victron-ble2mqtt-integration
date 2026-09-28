#!/usr/bin/env python3
"""Save and restore your live Site solar settings (run on .105).

  export   write the live helper values, the helper definitions and the live
           /site-solar dashboard config to a dated folder (default
           <repo>/.backups/site-solar/<YYYYmmdd-HHMMSS>/, git-ignored)
  restore  put helper values and/or the dashboard back from such a folder
  list     show the saved folders

Examples (token from HA_TOKEN or HA_TOKEN_FILE, never printed):
  HA_TOKEN_FILE=~/.ha_token python3 scripts/site_solar_settings.py export
  HA_TOKEN_FILE=~/.ha_token python3 scripts/site_solar_settings.py restore --from LATEST --helpers --dry-run
  HA_TOKEN_FILE=~/.ha_token python3 scripts/site_solar_settings.py restore --from LATEST --helpers
  HA_TOKEN_FILE=~/.ha_token python3 scripts/site_solar_settings.py restore --from LATEST --dashboard

restore always takes a fresh export first, so a restore can itself be undone.
Helper values are written with the normal HA actions (input_text.set_value,
input_select.select_option, input_number.set_value, input_boolean.turn_on/off), so
they show in the logbook as coming from this token's user.

Official:
  https://developers.home-assistant.io/docs/api/websocket/ (get_states, call_service)
  lovelace/config and lovelace/config/save:
  https://github.com/home-assistant/core/blob/dev/homeassistant/components/lovelace/websocket.py
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENERGY_MOD = ROOT / "scripts" / "save_solar_plant_energy_prefs.py"
URL_PATH = "site-solar"
DEFAULT_BACKUP_ROOT = ROOT / ".backups" / "site-solar"

HELPERS_FILE = "helpers.json"
DEFINITIONS_FILE = "helper-definitions.json"
DASHBOARD_FILE = "dashboard-site-solar.json"
DASHBOARDS_LIST_FILE = "dashboards.json"

# Every helper a person sets for Site solar / dump control.
HELPER_PATTERNS = (
    re.compile(r"^input_text\.h5082_[0-9a-f]{4}_(location|left_load|right_load)$"),
    re.compile(r"^input_select\.h5082_[0-9a-f]{4}_(left|right)_(use|inverter)$"),
    re.compile(r"^input_number\.dump_[a-z0-9_]+$"),
    re.compile(r"^input_boolean\.dump_[a-z0-9_]+$"),
    re.compile(r"^input_text\.dump_[a-z0-9_]+$"),
)


def _energy():
    spec = importlib.util.spec_from_file_location("save_solar_plant_energy_prefs", ENERGY_MOD)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {ENERGY_MOD}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def backup_root(override: str | Path | None = None) -> Path:
    if override:
        return Path(override).expanduser()
    env = os.environ.get("SITE_SOLAR_BACKUP_DIR", "").strip()
    return Path(env).expanduser() if env else DEFAULT_BACKUP_ROOT


def new_backup_dir(root: Path, label: str = "") -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = root / (stamp + (f"-{label}" if label else ""))
    n = 1
    while path.exists():
        n += 1
        path = root / f"{stamp}{'-' + label if label else ''}-{n}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def resolve_backup_dir(root: Path, name: str) -> Path:
    if name == "LATEST":
        dirs = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
        if not dirs:
            raise SystemExit(f"no backups under {root}")
        return dirs[-1]
    path = Path(name).expanduser()
    if not path.is_absolute() and not path.exists():
        path = root / name
    if not path.is_dir():
        raise SystemExit(f"backup folder not found: {path}")
    return path


def is_site_solar_helper(entity_id: str) -> bool:
    return any(p.match(entity_id) for p in HELPER_PATTERNS)


def select_helper_states(states: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in states:
        eid = str(row.get("entity_id", ""))
        if not is_site_solar_helper(eid):
            continue
        attrs = row.get("attributes") or {}
        out[eid] = {
            "state": row.get("state"),
            "friendly_name": attrs.get("friendly_name"),
            "options": attrs.get("options"),
            "min": attrs.get("min"),
            "max": attrs.get("max"),
            "editable": attrs.get("editable"),
            "last_changed": row.get("last_changed"),
        }
    return dict(sorted(out.items()))


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def restore_action(entity_id: str, saved: dict[str, Any], live: dict[str, Any] | None):
    """(domain, service, service_data) that puts `saved` back, or None to skip."""
    value = saved.get("state")
    if value in (None, "unknown", "unavailable") or (live or {}).get("state") == value:
        return None
    domain = entity_id.split(".", 1)[0]
    options = (live or {}).get("options") or saved.get("options") or []
    action = None
    if domain == "input_text":
        action = ("input_text", "set_value", {"value": value})
    elif domain == "input_select" and (not options or value in options):
        action = ("input_select", "select_option", {"option": value})
    elif domain == "input_number" and _num(value) is not None:
        action = ("input_number", "set_value", {"value": _num(value)})
    elif domain == "input_boolean" and value in ("on", "off"):
        action = ("input_boolean", "turn_on" if value == "on" else "turn_off", {})
    return action


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


class Session:
    """Authenticated HA websocket session (reuses the stdlib client in
    save_solar_plant_energy_prefs.py)."""

    def __init__(self, url: str, token_file: Path | None) -> None:
        self.energy = _energy()
        token = self.energy.load_token(token_file)
        self.ws = self.energy.ws_connect(url)
        self.msg_id = 0
        hello = self.energy.recv_text(self.ws)
        if hello.get("type") != "auth_required":
            raise RuntimeError(f"expected auth_required, got {hello.get('type')}")
        self.energy.send_frame(
            self.ws,
            self.energy.OP_TEXT,
            json.dumps({"type": "auth", "access_token": token}).encode("utf-8"),
        )
        if self.energy.recv_text(self.ws).get("type") != "auth_ok":
            raise RuntimeError("HA websocket auth failed")

    def call(self, payload: dict[str, Any]) -> Any:
        self.msg_id += 1
        return self.energy.ws_call(self.ws, self.msg_id, payload)

    def close(self) -> None:
        try:
            self.energy.send_frame(self.ws, self.energy.OP_CLOSE, b"")
        except OSError:
            pass
        self.ws.sock.close()


def fetch_dashboard(session: Session, url_path: str = URL_PATH) -> dict[str, Any] | None:
    """Live storage dashboard config, or None when it has never been saved."""
    try:
        config = session.call({"type": "lovelace/config", "url_path": url_path, "force": False})
    except RuntimeError as exc:
        if "config_not_found" in str(exc):
            return None
        raise
    return config if isinstance(config, dict) and config else None


def export(session: Session, root: Path, label: str = "") -> Path:
    out = new_backup_dir(root, label)
    states = session.call({"type": "get_states"})
    helpers = select_helper_states(states if isinstance(states, list) else [])
    write_json(out / HELPERS_FILE, helpers)
    definitions: dict[str, Any] = {}
    for domain in ("input_text", "input_select", "input_number", "input_boolean"):
        try:
            definitions[domain] = session.call({"type": f"{domain}/list"})
        except RuntimeError as exc:
            definitions[domain] = {"error": str(exc)}
    write_json(out / DEFINITIONS_FILE, definitions)
    try:
        write_json(out / DASHBOARDS_LIST_FILE, session.call({"type": "lovelace/dashboards/list"}))
    except RuntimeError as exc:
        print("WARN dashboards list:", exc)
    dash = fetch_dashboard(session)
    if dash is not None:
        write_json(out / DASHBOARD_FILE, dash)
        views = len(dash.get("views") or [])
        print(f"[site-solar] saved live dashboard ({views} views) -> {out / DASHBOARD_FILE}")
    else:
        print("[site-solar] no saved /site-solar dashboard config on HA (nothing to back up)")
    print(f"[site-solar] saved {len(helpers)} helper values -> {out / HELPERS_FILE}")
    return out


def restore(  # noqa: PLR0913 - keyword-only switches
    session: Session,
    src: Path,
    root: Path,
    *,
    helpers: bool,
    dashboard: bool,
    dry_run: bool,
) -> int:
    if not dry_run:
        pre = export(session, root, label="pre-restore")
        print(f"[site-solar] current settings saved first -> {pre}")
    changed = 0
    if helpers:
        saved = json.loads((src / HELPERS_FILE).read_text(encoding="utf-8"))
        states = session.call({"type": "get_states"})
        live = select_helper_states(states if isinstance(states, list) else [])
        for eid, row in saved.items():
            if eid not in live:
                print("MISSING", eid, "(helper does not exist now; not restored)")
                continue
            action = restore_action(eid, row, live.get(eid))
            if action is None:
                continue
            domain, service, data = action
            shown = data.get("value", data.get("option", service))
            if dry_run:
                print("WOULD SET", eid, repr(live[eid].get("state")), "->", repr(shown))
                continue
            session.call(
                {
                    "type": "call_service",
                    "domain": domain,
                    "service": service,
                    "service_data": data,
                    "target": {"entity_id": eid},
                }
            )
            changed += 1
            print("SET", eid, "->", repr(shown))
    if dashboard:
        path = src / DASHBOARD_FILE
        if not path.is_file():
            raise SystemExit(f"{path} missing: that backup has no dashboard")
        config = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(config, dict) or not config.get("views"):
            raise SystemExit(f"{path} is not a Lovelace config with views")
        if dry_run:
            print(f"WOULD SAVE dashboard /{URL_PATH} from {path} ({len(config['views'])} views)")
        else:
            session.call({"type": "lovelace/config/save", "url_path": URL_PATH, "config": config})
            changed += 1
            print(f"[site-solar] restored dashboard /{URL_PATH} from {path}")
    print(f"[site-solar] restore {'dry run' if dry_run else 'done'}: {changed} change(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export / restore live Site solar helper values and dashboard"
    )
    parser.add_argument("--url", default=os.environ.get("HA_URL", "http://127.0.0.1:8123"))
    parser.add_argument("--token-file", type=Path, default=None)
    parser.add_argument(
        "--backup-dir",
        default=None,
        help=f"backup root (default $SITE_SOLAR_BACKUP_DIR or {DEFAULT_BACKUP_ROOT})",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    exp = sub.add_parser("export", help="save live helper values + dashboard")
    exp.add_argument("--label", default="", help="suffix for the folder name")
    res = sub.add_parser("restore", help="put saved values / dashboard back")
    res.add_argument("--from", dest="src", required=True, help="folder, folder name or LATEST")
    res.add_argument("--helpers", action="store_true", help="restore helper values")
    res.add_argument("--dashboard", action="store_true", help="restore /site-solar dashboard")
    res.add_argument("--dry-run", action="store_true", help="show what would change")
    sub.add_parser("list", help="list saved folders")
    args = parser.parse_args(argv)
    root = backup_root(args.backup_dir)

    if args.cmd == "list":
        for p in sorted(root.iterdir()) if root.is_dir() else []:
            if p.is_dir():
                print(p.name, " ".join(sorted(f.name for f in p.iterdir())))
        return 0
    if args.cmd == "restore" and not (args.helpers or args.dashboard):
        parser.error("restore needs --helpers and/or --dashboard")

    session = Session(args.url, args.token_file)
    try:
        if args.cmd == "export":
            export(session, root, args.label)
            return 0
        src = resolve_backup_dir(root, args.src)
        return restore(
            session,
            src,
            root,
            helpers=args.helpers,
            dashboard=args.dashboard,
            dry_run=args.dry_run,
        )
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
