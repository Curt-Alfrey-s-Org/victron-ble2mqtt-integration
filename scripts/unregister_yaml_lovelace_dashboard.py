#!/usr/bin/env python3
"""Remove a named YAML Lovelace dashboard from configuration.yaml.

Official YAML dashboards use mode: yaml and are not rearranged in the UI:
https://www.home-assistant.io/dashboards/dashboards/#adding-yaml-dashboards

Storage-mode dashboards are created under Settings > Dashboards.
This script only strips a YAML dashboard key. It does not touch packages.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def unregister_yaml_dashboard(text: str, dash_id: str = "solar-plant") -> str:
    """Return configuration.yaml text without dash_id under lovelace.dashboards."""
    if not re.match(r"^[a-z0-9-]+$", dash_id):
        raise ValueError("dash_id must be a Lovelace URL key (hyphenated)")
    # Only this key plus its 6-space children. Sibling dashboards are also
    # indented 4 spaces (official YAML dashboards example).
    entry = re.compile(
        rf"(?m)^    {re.escape(dash_id)}:\n" r"(?: {6,}.+\n)*"
    )
    out, _n = entry.subn("", text, count=1)
    empty = re.compile(r"(?m)^lovelace:\n  dashboards:\n(?![ \t])")
    out, _n2 = empty.subn("", out, count=1)
    return out


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: unregister_yaml_lovelace_dashboard.py CONFIG.yaml [dash-id]", file=sys.stderr)
        return 2
    path = Path(argv[1])
    dash_id = argv[2] if len(argv) > 2 else "solar-plant"
    old = path.read_text(encoding="utf-8")
    new = unregister_yaml_dashboard(old, dash_id)
    if new == old:
        print(f"[unregister] no YAML dashboard {dash_id} in {path}")
        return 0
    path.write_text(new, encoding="utf-8")
    print(f"[unregister] removed YAML dashboard {dash_id} from {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
