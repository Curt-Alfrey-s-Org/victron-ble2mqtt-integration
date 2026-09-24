"""Validate Solar plant HA package and Lovelace YAML (device-native, no duplicate tiles)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "config" / "packages" / "solar_plant.yaml"
DASHBOARD = ROOT / "config" / "dashboards" / "solar-plant.yaml"
DEVICE_POLICY = ROOT / "docs" / "SOLAR_DEVICE_SENSORS_ONLY.md"

FORBIDDEN_ENTITY_FRAGMENTS = (
    "site_solar",
    "site_charge",
    "site_source",
    "site_total_load",
    "site_load_",
    "victron_pack_charge",
    "sungold_cart_charge",
    "ku_stack_load",
    "sph_ac_in_unmatched",
    "t2_ku_jumper",
    "trailer_outlet",
    "ku_unmetered",
    "ku_charger_equal",
    "ku_renogy_ac_load",
    "sungold_cart_to_load",
    "solar_component_losses",
    "t2_mppt_conversion_loss",
    "sungold_conversion_loss",
    "sungold_uti_va",
    "sungold_ac_out_va",
    "sungold_load_today",
    "sim_dump_load_power",
    "dump_surplus_w",
    "dump_bus_load",
)


def _load(path: Path) -> object:
    assert path.is_file(), f"missing {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _now_tile_entities(dashboard: dict) -> list[str]:
    now = next(v for v in dashboard["views"] if v.get("path") == "now")
    out: list[str] = []
    for section in now.get("sections") or []:
        for card in section.get("cards") or []:
            if card.get("type") == "tile" and card.get("entity"):
                out.append(str(card["entity"]))
    return out


def test_package_device_native_only() -> None:
    data = _load(PACKAGE)
    assert isinstance(data, dict)
    assert data.get("template") is None
    assert data.get("sensor") is None
    assert data.get("utility_meter") is None
    rest_blocks = data.get("rest") or []
    assert rest_blocks
    nws = rest_blocks[0]
    assert "api.weather.gov/alerts/active?point=36.32,-82.12" in nws["resource"]


def test_dashboard_no_computed_site_entities() -> None:
    text = DASHBOARD.read_text(encoding="utf-8")
    for frag in FORBIDDEN_ENTITY_FRAGMENTS:
        assert frag not in text, f"forbidden fragment in dashboard: {frag}"
    assert "Quick meters" not in text
    assert "Instant W" not in text


def test_now_view_tile_entities_unique() -> None:
    data = _load(DASHBOARD)
    tiles = _now_tile_entities(data)
    assert tiles, "expected tile entities on Now view"
    assert len(tiles) == len(set(tiles)), f"duplicate tile entities: {tiles}"


def test_device_policy_doc() -> None:
    text = DEVICE_POLICY.read_text(encoding="utf-8")
    assert "device-native" in text.lower()
    assert "once" in text.lower() or "duplicate" in text.lower()
