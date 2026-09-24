"""Validate Solar plant HA package and Lovelace YAML (device-native policy)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "config" / "packages" / "solar_plant.yaml"
DASHBOARD = ROOT / "config" / "dashboards" / "solar-plant.yaml"
INSTALL = ROOT / "scripts" / "install_solar_plant_ha.sh"
DOCS = ROOT / "docs" / "SOLAR_HA_DASHBOARD.md"
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
)


def _load(path: Path) -> object:
    assert path.is_file(), f"missing {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_package_device_native_only() -> None:
    data = _load(PACKAGE)
    assert isinstance(data, dict)
    assert data.get("template") is None
    rest_blocks = data.get("rest") or []
    assert rest_blocks
    nws = rest_blocks[0]
    assert "api.weather.gov/alerts/active?point=36.32,-82.12" in nws["resource"]
    integrations = data.get("sensor") or []
    sources = {b["source"] for b in integrations if isinstance(b, dict) and "source" in b}
    assert "sensor.solar_controller_solar" in sources
    assert "sensor.sungold_sph302480a_load_power" in sources
    assert "sensor.em16_b3_power" in sources
    assert not any("site_" in s for s in sources)
    meters = data.get("utility_meter") or {}
    assert "sungold_load_today" in meters
    assert "site_solar_today" not in meters


def test_dashboard_no_computed_site_entities() -> None:
    text = DASHBOARD.read_text(encoding="utf-8")
    for frag in FORBIDDEN_ENTITY_FRAGMENTS:
        assert frag not in text, f"forbidden fragment in dashboard: {frag}"
    assert "Quick meters" in text
    assert "Site totals" not in text
    data = _load(DASHBOARD)
    now_view = data["views"][0]
    assert now_view["title"] == "Now"


def test_device_policy_doc() -> None:
    text = DEVICE_POLICY.read_text(encoding="utf-8")
    assert "device-native" in text.lower()
    assert "site_source_power" in text


def test_docs_and_install_script_exist() -> None:
    text = DOCS.read_text(encoding="utf-8")
    assert "device-native" in text.lower() or "Device-native" in text
    assert "Quick meters" in text
    script = INSTALL.read_text(encoding="utf-8")
    assert "check_config" in script
    assert "docker restart homeassistant" in script
