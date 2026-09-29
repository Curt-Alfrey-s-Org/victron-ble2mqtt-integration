"""Solar tab -> Site solar merge tooling (compare by entities, add only missing cards)."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "config" / "dashboards" / "solar-plant.yaml"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses look the module up by name
    spec.loader.exec_module(mod)
    return mod


cmp = _load("compare_solar_tab")
settings = _load("site_solar_settings")

LIVE_TILE = "sensor.solar_controller_charge_state"  # tile on Now > T2 24 V
HISTORY_ONLY = "sensor.solar_controller_battery"  # only in a History graph
NEW_A = "sensor.solar_controller_device_rssi"  # not on Site solar
NEW_B = "sensor.battery_1_consumed_ah_example"


def _solar_export() -> dict:
    """Shaped like lovelace.dashboard_solar: one sections view, device headings, tiles."""
    tile = lambda e: {"type": "tile", "entity": e, "name": {"type": "entity"}}  # noqa: E731
    return {
        "url_path": "dashboard-solar",
        "title": "Solar",
        "config": {
            "views": [
                {
                    "title": "Solar",
                    "type": "sections",
                    "badges": [{"type": "entity", "entity": "sensor.battery_1_state_of_charge"}],
                    "sections": [
                        {
                            "type": "grid",
                            "cards": [
                                {"type": "heading", "heading": "BlueSolar MPPT 75/15"},
                                tile(LIVE_TILE),
                                tile(NEW_A),
                                tile(HISTORY_ONLY),
                            ],
                        },
                        {
                            "type": "grid",
                            "cards": [
                                {"type": "heading", "heading": "Battery 1"},
                                {
                                    "type": "vertical-stack",
                                    "cards": [
                                        {"type": "entities", "entities": [LIVE_TILE, {"entity": NEW_B}]},
                                    ],
                                },
                                {"type": "markdown", "content": "Old Solar note"},
                            ],
                        },
                        {
                            "type": "grid",
                            "cards": [
                                {"type": "heading", "heading": "Plugs"},
                                tile("sensor.h5082_82fb_rssi_pi5"),
                            ],
                        },
                    ],
                }
            ]
        },
    }


def _rows():
    return cmp.classify(_solar_export()["config"], cmp.load_config(SEED))


def _by_entity(rows):
    return {tuple(r.card.entities): r for r in rows}


def test_cards_are_compared_by_entities():
    rows = _by_entity(_rows())
    assert rows[("sensor.battery_1_state_of_charge",)].status == "on-site-solar"  # Now badge
    live = rows[(LIVE_TILE,)]
    assert live.status == "on-site-solar"
    assert any("T2 24 V" in w for w in live.where)
    assert rows[(NEW_A,)].status == "missing"
    assert rows[(HISTORY_ONLY,)].status == "history-only"
    partly = rows[(LIVE_TILE, NEW_B)]  # found inside a vertical-stack
    assert partly.status == "partly" and partly.missing == [NEW_B]
    assert rows[()].status == "no-entities"
    assert rows[("sensor.h5082_82fb_rssi_pi5",)].status == "needs-decision"


def test_globs_and_templates_count_as_on_site_solar():
    # Plugs are shown through auto-entities globs on Site solar.
    index = cmp.site_index(cmp.load_config(SEED))
    assert index.locate("switch.ihoment_h5082_82fb_left")
    # An excluded glob does not count as shown.
    assert "timer.h5082_*_hold" not in {pattern for pattern, _kind, _where in index.globs}


def test_markdown_table_lists_every_card_and_totals():
    table = cmp.markdown_table(_rows())
    rows = [ln for ln in table.splitlines() if ln.startswith("| ") and not ln.startswith("| # ")]
    assert len(rows) == 7  # 7 Solar cards (badge included), headings are not cards
    assert "Totals: on-site-solar 2, history-only 1, partly 1, missing 1, no-entities 1, needs-decision 1" in table
    assert f"Missing: `{NEW_B}`" in table


def test_apply_adds_only_missing_cards_in_a_new_view(tmp_path):
    seed = tmp_path / "solar-plant.yaml"
    shutil.copy(SEED, seed)
    before = yaml.safe_load(seed.read_text(encoding="utf-8"))
    msg = cmp.apply(seed, _rows())
    assert "added view 'Solar tab'" in msg and "4 cards" in msg
    after = yaml.safe_load(seed.read_text(encoding="utf-8"))
    assert after["views"][:-1] == before["views"]  # existing layout untouched
    assert {k: v for k, v in after.items() if k != "views"} == {k: v for k, v in before.items() if k != "views"}
    view = after["views"][-1]
    assert (view["title"], view["path"], view["type"]) == ("Solar tab", "solar-tab", "sections")
    shown = json.dumps(view)
    assert NEW_A in shown and HISTORY_ONLY in shown and NEW_B in shown
    assert LIVE_TILE not in shown  # already on Site solar, not copied
    assert "h5082" not in shown and "dump_" not in shown  # plug / dump boxes not copied
    headings = [c["heading"] for s in view["sections"] for c in s["cards"] if c["type"] == "heading"]
    assert headings == ["BlueSolar MPPT 75/15", "Battery 1"]
    assert "initial:" not in seed.read_text(encoding="utf-8")
    # Re-running replaces only the generated view.
    cmp.apply(seed, _rows())
    again = yaml.safe_load(seed.read_text(encoding="utf-8"))
    assert again == after


def test_apply_refuses_a_hand_made_view_with_the_same_path(tmp_path):
    seed = tmp_path / "solar-plant.yaml"
    seed.write_text(
        SEED.read_text(encoding="utf-8") + "  - title: Mine\n    path: solar-tab\n    cards: []\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="hand-made view"):
        cmp.apply(seed, _rows())


def test_apply_keeps_unique_now_view_check_green(tmp_path, monkeypatch):
    seed = tmp_path / "solar-plant.yaml"
    shutil.copy(SEED, seed)
    cmp.apply(seed, _rows())
    unique = _load("check_solar_dashboard_unique")
    monkeypatch.setattr(unique, "DASH", seed)
    assert unique.main() == 0


def test_cli_reads_export_and_writes_table(tmp_path):
    export = tmp_path / "solar-tab.json"
    export.write_text(json.dumps(_solar_export()), encoding="utf-8")
    out = tmp_path / "table.md"
    before = SEED.read_text(encoding="utf-8")
    res = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "compare_solar_tab.py"), str(export), "--markdown", str(out)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Totals:" in res.stdout and out.read_text(encoding="utf-8").startswith("| # |")
    assert SEED.read_text(encoding="utf-8") == before  # read-only without --apply


def test_seed_has_no_solar_tab_view_yet():
    """This PR is plan + tooling only; the cards come after the live export."""
    seed = yaml.safe_load(SEED.read_text(encoding="utf-8"))
    assert [v.get("path") for v in seed["views"]] == ["now", "history"]


# ------------------------------------------------------------ read-only export


class _FakeSession:
    def __init__(self, dashboards, config):
        self.dashboards = dashboards
        self.config = config
        self.calls = []

    def call(self, payload):
        self.calls.append(payload["type"])
        if payload["type"] == "lovelace/dashboards/list":
            return self.dashboards
        if payload["type"] == "lovelace/config":
            assert payload["url_path"] == "dashboard-solar"
            return self.config
        raise AssertionError(payload)


def test_export_dashboard_is_read_only_and_redacts_tokens(tmp_path, capsys):
    config = {
        "views": [
            {
                "title": "Solar",
                "sections": [
                    {
                        "cards": [
                            {"type": "picture", "image": "http://cam.local/snap.jpg?token=abc123&x=1"},
                            {"type": "iframe", "url": "http://x", "api_key": "k-123"},
                            {"type": "tile", "entity": "sensor.solar_controller_solar"},
                        ]
                    }
                ],
            }
        ]
    }
    session = _FakeSession([{"url_path": "dashboard-solar", "title": "Solar", "mode": "storage"}], config)
    out = settings.export_dashboard(session, "dashboard-solar", tmp_path / "solar-tab.json")
    assert session.calls == ["lovelace/dashboards/list", "lovelace/config"]  # no save calls
    data = json.loads(out.read_text(encoding="utf-8"))
    text = json.dumps(data)
    assert "abc123" not in text and "k-123" not in text
    assert "token=<redacted>&x=1" in text
    assert data["url_path"] == "dashboard-solar" and data["config"]["views"][0]["title"] == "Solar"
    assert "redacted a token-like value" in capsys.readouterr().out
    # The compare tool reads the export wrapper directly.
    assert cmp.load_config(out)["views"][0]["title"] == "Solar"


def test_export_dashboard_lists_dashboards_when_url_path_is_wrong(tmp_path, capsys):
    session = _FakeSession([{"url_path": "site-solar", "title": "Site solar", "mode": "storage"}], {})
    with pytest.raises(SystemExit):
        settings.export_dashboard(session, "dashboard-solar", tmp_path / "x.json")
    assert "--url-path site-solar" in capsys.readouterr().out
    assert not (tmp_path / "x.json").exists()


def test_default_export_path_is_in_the_repo():
    assert settings.EXPORTS_DIR == ROOT / "config" / "dashboards" / "exports"
    assert settings.SOLAR_TAB_URL_PATH == "dashboard-solar"
