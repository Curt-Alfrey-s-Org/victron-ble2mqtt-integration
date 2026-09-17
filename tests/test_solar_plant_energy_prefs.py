"""Solar plant Energy prefs payload (no live HA)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "scripts" / "save_solar_plant_energy_prefs.py"


def _load():
    spec = importlib.util.spec_from_file_location("save_solar_plant_energy_prefs", MOD)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_energy_prefs_have_no_grid_or_ku_share_solar() -> None:
    module = _load()
    payload = module.energy_save_payload()
    types = [row["type"] for row in payload["energy_sources"]]
    assert types == ["solar", "battery", "battery"]
    solar = payload["energy_sources"][0]
    assert solar["stat_energy_from"] == "sensor.t2_mppt_energy_kwh"
    assert solar["stat_rate"] == "sensor.solar_controller_solar"
    assert payload["device_consumption_water"] == []
    consumption = {row["stat_consumption"] for row in payload["device_consumption"]}
    assert "sensor.em16_a3_energy_kwh" in consumption
    assert "sensor.sungold_load_energy_kwh" in consumption
    assert "sensor.sim_dump_energy_kwh" in consumption
    rates = {row["stat_rate"] for row in payload["device_consumption"]}
    assert "sensor.trailer_outlet_power" in rates
    assert "sensor.em16_a3_power" not in rates
    assert "sensor.ku_charger_equal_share_power" not in rates
