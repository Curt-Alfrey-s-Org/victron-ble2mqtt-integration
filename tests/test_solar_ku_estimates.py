"""Deprecated KU estimate package, and the paired meter on the Now view."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "config" / "packages" / "solar_ku_estimates.yaml"
DASH = ROOT / "config" / "dashboards" / "solar-plant.yaml"


def test_ku_est_package_exists() -> None:
    text = PKG.read_text(encoding="utf-8")
    assert "ku_pwm_mppt_combined_est_power" in text
    assert "t2_ku_jumper_power" in text


def test_now_view_shows_paired_ku_meter_not_retired_pwm_tile() -> None:
    """Site solar Now shows the paired 75/15. The PWM+MPPT est tile was retired 2026-10-02."""
    blob = DASH.read_text(encoding="utf-8")
    assert "heading: KU 24 V" in blob
    assert "sensor.solar_controller_solar" in blob
    assert "sensor.ku_pwm_mppt_combined_est_power" not in blob
    assert "PWM+MPPT est" not in blob
