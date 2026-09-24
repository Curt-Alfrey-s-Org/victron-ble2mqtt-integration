"""Site EM16 live wrappers for A3/B3."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "config" / "packages" / "solar_em16_live.yaml"
DASH = ROOT / "config" / "dashboards" / "solar-plant.yaml"


def test_em16_live_package() -> None:
    text = PKG.read_text(encoding="utf-8")
    assert "site_em16_a3_power" in text
    assert "sungold_sph302480a_grid_voltage" in text


def test_dashboard_uses_site_em16() -> None:
    blob = DASH.read_text(encoding="utf-8")
    assert "sensor.site_em16_a3_power" in blob
    assert "sensor.em16_a3_power" not in blob.split("History")[0]
