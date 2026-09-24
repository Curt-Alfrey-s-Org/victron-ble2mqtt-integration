#!/usr/bin/env python3
"""Sync merged flows + solarComputed settings to nodered-data (systemd user service)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path("/home/ansible/victron-ble2mqtt-integration")
DATA = ROOT / "nodered-data"
SETTINGS = DATA / "settings.js"
MERGED = Path("/tmp/nodered-flows-merged.json")

SETTINGS_TEXT = """module.exports = {
    flowFile: "flows.json",
    flowFilePretty: true,
    adminRoot: "/",
    adminAuth: (function () {
        var user = process.env.NR_ADMIN_USER;
        var hash = process.env.NR_ADMIN_PASSWORD_HASH;
        if (!user || !hash) {
            return undefined;
        }
        return {
            type: "credentials",
            users: [{
                username: user,
                password: hash,
                permissions: "*"
            }]
        };
    })(),
    functionGlobalContext: {
        solarComputed: (function () {
            try {
                return require("%s");
            } catch (e) {
                return {};
            }
        })(),
        haToken: process.env.HA_LONG_LIVED_TOKEN || "",
        haBaseUrl: process.env.HA_BASE_URL || "http://127.0.0.1:8123"
    },
    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false
        }
    }
};
""" % (
    str(ROOT / "scripts" / "nodered_solar_computed.js").replace("\\", "\\\\")
)


def main() -> int:
    subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "merge_nodered_flows.py"),
            str(MERGED),
            str(ROOT / "flows" / "solar_plant_diagram.json"),
            str(ROOT / "flows" / "solar_computed_meters.json"),
        ],
        check=True,
    )
    DATA.joinpath("flows.json").write_bytes(MERGED.read_bytes())
    SETTINGS.write_text(SETTINGS_TEXT, encoding="utf-8")
    print("synced flows.json and settings.js to", DATA)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
