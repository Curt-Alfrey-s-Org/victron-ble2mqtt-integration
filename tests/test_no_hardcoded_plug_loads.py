"""No hard-coded plug loads or locations (2026-09-28).

What is plugged into each H5082 socket and where each plug sits change over time, so
the repo must never write them down. They are the operator's HA helpers
`input_text.h5082_<id>_location` (Where) and `input_text.h5082_<id>_<side>_load`
(Load). The dashboard and the Dump control logbook lines read them live and fall back
to the plug id + side. Plug ids and MAC addresses are hardware facts and are fine.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from govee_h5082.mqtt_bridge import PLUGS

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "config" / "dashboards" / "solar-plant.yaml"
DUMP_PKG = ROOT / "config" / "packages" / "dump_control.yaml"
LABELS = ROOT / "scripts" / "create_h5082_socket_labels.py"
DOCS = ROOT / "docs"

PLUG_IDS = sorted(name[-4:].lower() for _addr, name in PLUGS)

# Load / location words that must never appear as fixed text next to the plugs.
# (\b word boundaries; "shed" is deliberately absent: it is the dump verb.)
FORBIDDEN = re.compile(
    r"\b("
    r"pi ?4|pi ?5 supply|pi supply|raspberry|feeds the pi|powers the pi|"
    r"heaters?|water heater|fridge|refrigerator|freezer|pump|fans?|vent|"
    r"a/c|air ?con\w*|dehumidifier|kettle|microwave|router|modem|tv|computer|laptop|"
    r"lights?|leds?|trailer|bedroom|bathroom|kitchen|garage|office|living room|"
    r"shop|barn|cabin|porch|basement"
    r")\b",
    re.IGNORECASE,
)


def _strings(node, path=""):
    """Every string value (and key path) in a parsed YAML tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _strings(value, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def _seed() -> dict:
    return yaml.safe_load(SEED.read_text(encoding="utf-8"))


def _pkg() -> dict:
    return yaml.safe_load(DUMP_PKG.read_text(encoding="utf-8"))


def _plug_sections():
    """Now/History sections that show H5082 plugs or dump settings."""
    for view in _seed()["views"]:
        for section in view.get("sections") or []:
            blob = json.dumps(section)
            if "h5082" in blob or "dump_" in blob:
                yield section


def test_dashboard_seed_has_no_hardcoded_load_or_location() -> None:
    hits = []
    for path, text in _strings(_seed().get("button_card_templates", {}), "button_card_templates"):
        hits += [(path, m.group(0)) for m in FORBIDDEN.finditer(text)]
    for section in _plug_sections():
        heading = next((c.get("heading") for c in section["cards"] if c.get("type") == "heading"), "?")
        for path, text in _strings(section, heading):
            hits += [(path, m.group(0)) for m in FORBIDDEN.finditer(text)]
    assert not hits, f"hard-coded load / location text in the dashboard seed: {hits}"


def test_dump_package_names_and_messages_have_no_hardcoded_load_or_location() -> None:
    hits = []
    for path, text in _strings(_pkg()):
        hits += [(path, m.group(0)) for m in FORBIDDEN.finditer(text)]
    assert not hits, f"hard-coded load / location text in dump_control.yaml: {hits}"


def test_dump_package_helper_names_are_plug_id_and_side_only() -> None:
    data = _pkg()
    for domain in ("input_select", "timer"):
        for key, cfg in data[domain].items():
            if not key.startswith("h5082_"):
                continue
            assert re.match(r"^[0-9A-F]{4} (left|right) ", cfg["name"]), (key, cfg["name"])


def test_plug_name_cards_are_titled_by_plug_id_only() -> None:
    titles = []
    for section in _plug_sections():
        for card in section["cards"]:
            if card.get("type") == "entities" and any(
                "_location" in json.dumps(e) for e in card.get("entities", [])
            ):
                titles.append(card.get("title"))
    assert sorted(str(t).lower() for t in titles) == PLUG_IDS, titles


def test_socket_rows_are_named_from_live_where_and_load() -> None:
    cards = {}
    for section in _plug_sections():
        for card in section["cards"]:
            if card.get("type") == "custom:auto-entities" and "template" in card.get("filter", {}):
                cards[card["card"]["title"]] = card
    for title, kind, count in (("Socket Use", "use", 16), ("Socket inverter", "inverter", 16)):
        card = cards[title]
        tpl = card["filter"]["template"]
        assert "'input_text.h5082_' ~ s ~ '_load'" in tpl, title
        assert "'input_text.h5082_' ~ p ~ '_location'" in tpl, title
        ids = re.findall(r"'(input_select\.h5082_[0-9a-f]{4}_(?:left|right)_" + kind + r")'", tpl)
        assert len(ids) == count, (title, ids)
        # Fallback when Load is blank: plug id + side, never a fixed name.
        assert "p | upper ~ ' ' ~ s[5:]" in tpl, title
        assert "entities" not in card, title  # no fixed per-row names


def test_live_name_cards_read_where_and_load() -> None:
    contents = [
        c.get("content", "")
        for section in _plug_sections()
        for c in section["cards"]
        if c.get("type") == "markdown" and "{%" in c.get("content", "")
    ]
    assert any("sensor.dump_next_plug" in c and "_load')" in c for c in contents)
    table = next(c for c in contents if "| Plug | Where | Left load | Right load |" in c)
    for plug in PLUG_IDS:
        for eid in (f"input_text.h5082_{plug}_location", f"input_text.h5082_{plug}_left_load",
                    f"input_text.h5082_{plug}_right_load"):
            assert eid in table, eid


def test_every_socket_logbook_line_starts_with_the_live_name() -> None:
    text = DUMP_PKG.read_text(encoding="utf-8")
    assert "- &socket_label" in text
    label_tpl = text.split("- &socket_label", 1)[1].split("- action:", 1)[0]
    assert "'input_text.h5082_' ~ sock ~ '_load'" in label_tpl
    assert "'input_text.h5082_' ~ p ~ '_location'" in label_tpl
    found = 0

    def walk(node, auto_id):
        nonlocal found
        if isinstance(node, dict):
            if node.get("action") == "logbook.log" and not node["data"]["entity_id"].startswith("script."):
                found += 1
                assert node["data"]["message"].startswith("{{ label }}: "), auto_id
            for value in node.values():
                walk(value, auto_id)
        elif isinstance(node, list):
            for value in node:
                walk(value, auto_id)

    for auto in _pkg()["automation dump_load"]:
        walk(auto["actions"], auto["id"])
    assert found >= 13


def test_label_script_and_bridge_carry_no_load_or_location() -> None:
    text = LABELS.read_text(encoding="utf-8")
    code = re.sub(r'"""[\s\S]*?"""', "", text)  # docstrings explain history; code must not
    assert not FORBIDDEN.search(code), FORBIDDEN.search(code)
    for _addr, name in PLUGS:
        assert re.fullmatch(r"ihoment_H5082_[0-9A-F]{4}", name), name


@pytest.mark.parametrize("path", sorted((DOCS / "site-solar").glob("*.md")), ids=lambda p: p.name)
def test_help_docs_do_not_tie_a_real_plug_id_to_a_load(path: Path) -> None:
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        ids = [p for p in PLUG_IDS if re.search(rf"\b{p}\b", line, re.IGNORECASE)]
        if ids and FORBIDDEN.search(line):
            pytest.fail(f"{path.name}:{n} ties {ids} to {FORBIDDEN.search(line).group(0)!r}: {line}")


def test_no_doc_claims_a_plug_powers_the_pi() -> None:
    claim = re.compile(r"pi supply|feeds the pi|powers the pi|socket feeding the pi", re.IGNORECASE)
    hits = []
    for path in [*DOCS.rglob("*.md"), ROOT / "NEXT_STEPS.md", SEED, DUMP_PKG]:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if claim.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{n}")
    assert not hits, hits
