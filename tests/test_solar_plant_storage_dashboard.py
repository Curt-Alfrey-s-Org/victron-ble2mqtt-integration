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
    assert "sensor.ku_unmetered_pv_est_power" not in blob
    assert "input_boolean.dump_control_enabled" in blob
    assert "input_number.dump_site_confirm_s" in blob
    assert "timer.dump_plug_1_cooldown" in blob
    assert "input_text.dump_notify_service" in blob
    assert "switch.ihoment_h5082_82fb_left" in blob
    assert "switch.ihoment_h5082_c38d_right" in blob
    assert "input_text.h5082_82fb_location" in blob
    assert "custom:auto-entities" in blob
    assert "h5082_socket" in blob
    assert config.get("button_card_templates", {}).get("h5082_socket")
    assert "input_text.h5082_82fb_left_load" in blob
    assert "input_select.h5082_2f9d_right_use" in blob
    assert "switch.sim_ac_plug_1" not in blob
    assert "Sim dump plugs" not in blob
    assert "sensor.nws_watauga_lake_alerts" in blob
    assert "climate.417373300314" in blob
    assert "KMRX_loop.gif" in blob
    assert config["views"][0].get("type") == "sections"
    headings = []
    for section in config["views"][0]["sections"]:
        for card in section.get("cards") or []:
            if card.get("type") == "heading":
                headings.append(card.get("heading"))
    assert "KU 24 V" in headings
    assert "sensor.battery_2_power" in blob
