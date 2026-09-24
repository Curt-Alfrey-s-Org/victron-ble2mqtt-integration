"""KU combined estimate package and dashboard tile."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "config" / "packages" / "solar_ku_estimates.yaml"
DASH = ROOT / "config" / "dashboards" / "solar-plant.yaml"


def test_ku_est_package_exists() -> None:
    text = PKG.read_text(encoding="utf-8")
    assert "ku_pwm_mppt_combined_est_power" in text
    assert "t2_ku_jumper_power" in text


def test_now_view_has_ku_est_tile() -> None:
    blob = DASH.read_text(encoding="utf-8")
    assert "sensor.ku_pwm_mppt_combined_est_power" in blob
    assert "PWM+MPPT est" in blob
