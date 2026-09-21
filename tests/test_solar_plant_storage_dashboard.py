"""Site solar storage dashboard seed (no live HA)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "scripts" / "save_solar_plant_storage_dashboard.py"


def _load():
    spec = importlib.util.spec_from_file_location("save_solar_plant_storage_dashboard", MOD)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_storage_dashboard_create_is_not_yaml_mode() -> None:
    module = _load()
    payload = module.create_dashboard_payload()
    assert payload["type"] == "lovelace/dashboards/create"
    assert payload["url_path"] == "site-solar"
    assert payload["mode"] == "storage"
    assert payload["show_in_sidebar"] is True
    assert "yaml" not in payload["mode"]


def test_seed_config_has_leftover_live_tiles() -> None:
    module = _load()
    config = module.load_seed_config()
    blob = str(config)
    assert "sensor.site_solar_power" in blob
    assert "sensor.t2_ku_jumper_power" in blob
    assert "sensor.ku_unmetered_pv_est_power" in blob
    assert "input_boolean.dump_control_enabled" in blob
    assert "input_number.dump_site_confirm_s" in blob
    assert "timer.dump_plug_1_cooldown" in blob
    assert "sensor.dump_bus_load_sph" in blob
    assert "binary_sensor.dump_load_exceeds_solar" in blob
    assert "input_text.dump_notify_service" in blob
    assert "sensor.site_solar_today" in blob
    assert "switch.sim_ac_plug_1" in blob
    assert "sensor.nws_watauga_lake_alerts" in blob
    assert "climate.417373300314" in blob
    assert "KMRX_loop.gif" in blob
    assert config["views"][0].get("type") == "sections"
