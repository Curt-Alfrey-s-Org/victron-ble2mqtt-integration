"""Solar plant HA history purge entity list (no live HA)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HIST = ROOT / "scripts" / "solar_plant_history_entities.py"


def _load():
    spec = importlib.util.spec_from_file_location("solar_plant_history_entities", HIST)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_merge_includes_site_solar_and_excludes_nws() -> None:
    mod = _load()
    ids = mod.merge_purge_entity_ids(
        [
            "sensor.site_solar_power",
            "sensor.nws_watauga_lake_alerts",
            "sensor.417373300314_humidity",
            "sensor.sungold_sph302480a_load_power",
            "sensor.battery_1_power",
        ]
    )
    assert "sensor.site_solar_power" in ids
    assert "sensor.sungold_sph302480a_load_power" in ids
    assert "sensor.nws_watauga_lake_alerts" not in ids
    assert "sensor.417373300314_humidity" not in ids


def test_package_energy_helpers_in_static_list() -> None:
    mod = _load()
    static = set(mod.SOLAR_PLANT_PACKAGE_ENTITY_IDS)
    assert "sensor.site_solar_energy_kwh" in static
    assert "sensor.sungold_load_energy_kwh" in static
    assert "sensor.em16_a3_energy_kwh" in static
