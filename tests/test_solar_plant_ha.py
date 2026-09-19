"""Validate Solar plant HA package and Lovelace YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "config" / "packages" / "solar_plant.yaml"
DASHBOARD = ROOT / "config" / "dashboards" / "solar-plant.yaml"
INSTALL = ROOT / "scripts" / "install_solar_plant_ha.sh"
DOCS = ROOT / "docs" / "SOLAR_HA_DASHBOARD.md"


def _load(path: Path) -> object:
    assert path.is_file(), f"missing {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_package_pins_jumper_and_ku_share() -> None:
    data = _load(PACKAGE)
    assert isinstance(data, dict)
    sensors = []
    for block in data.get("template") or []:
        sensors.extend(block.get("sensor") or [])
    by_id = {s["default_entity_id"]: s for s in sensors}
    jumper = by_id["sensor.t2_ku_jumper_power"]
    assert "sensor.solar_controller_solar" in jumper["state"]
    assert "sensor.battery_1_power" in jumper["state"]
    share = by_id["sensor.ku_charger_equal_share_power"]
    assert "/ 3" in share["state"]
    ku = by_id["sensor.ku_unmetered_pv_est_power"]
    assert "sensor.battery_2_power" in ku["state"]
    assert "sensor.t2_ku_jumper_power" in ku["state"]
    assert "sensor.trailer_outlet_power" in ku["state"]
    assert by_id["sensor.battery_1_charge_power"]["device_class"] == "power"
    assert by_id["sensor.battery_1_discharge_power"]["device_class"] == "power"
    losses = by_id["sensor.solar_component_losses_power"]
    assert losses["device_class"] == "power"
    assert "sensor.t2_mppt_conversion_loss_power" in losses["state"]
    assert "sensor.sungold_conversion_loss_power" in losses["state"]
    t2_loss = by_id["sensor.t2_mppt_conversion_loss_power"]
    assert "sensor.solar_controller_charging_power" in t2_loss["state"]
    assert "| max" in t2_loss["state"]
    sg_loss = by_id["sensor.sungold_conversion_loss_power"]
    assert "sensor.sungold_sph302480a_charging_power" in sg_loss["state"]


def test_package_has_riemann_integrals() -> None:
    data = _load(PACKAGE)
    platforms = data.get("sensor") or []
    sources = {row["source"] for row in platforms}
    assert "sensor.solar_controller_solar" in sources
    assert "sensor.battery_1_charge_power" in sources
    assert "sensor.trailer_outlet_power" in sources
    assert "sensor.em16_a3_power" not in sources
    assert "sensor.sim_dump_load_power" in sources
    assert "sensor.sungold_sph302480a_load_power" in sources
    assert "sensor.sungold_sph302480a_load_active_power" not in sources
    for row in platforms:
        assert row["platform"] == "integration"
        assert row["method"] == "left"
        assert row["unit_prefix"] == "k"


def _all_cards(nodes: list) -> list:
    out: list = []
    for card in nodes:
        out.append(card)
        nested = card.get("cards")
        if isinstance(nested, list):
            out.extend(_all_cards(nested))
    return out


def test_dashboard_uses_official_cards_only() -> None:
    data = _load(DASHBOARD)
    assert data["title"] == "Solar plant"
    cards = []
    for view in data["views"]:
        cards.extend(_all_cards(view["cards"]))
    types = {c["type"] for c in cards}
    assert "power-sankey" in types
    assert "glance" in types
    assert "gauge" in types
    assert "history-graph" in types
    assert "distribution" in types
    assert "markdown" in types
    assert "thermostat" in types
    assert "weather-forecast" in types
    assert "statistics-graph" in types
    assert "entities" in types
    forbidden = {"custom:", "iframe", "webpage"}
    for card in cards:
        t = card["type"]
        assert not any(t.startswith(p) for p in forbidden)
        assert "picture-elements" not in t
        if t == "history-graph":
            entities = card.get("entities") or []
            assert len(entities) <= 8
    sankey = next(c for c in cards if c["type"] == "power-sankey")
    assert sankey["layout"] == "horizontal"
    assert sankey["collection_key"] == "energy_dashboard"
    thermostat = next(c for c in cards if c["type"] == "thermostat")
    assert thermostat["entity"] == "climate.417373300314"
    assert thermostat["name"] == "Ecobee"
    weather_cards = [c for c in cards if c.get("type") == "weather-forecast"]
    assert len(weather_cards) == 2
    assert {c["entity"] for c in weather_cards} == {"weather.417373300314"}
    assert {c["forecast_type"] for c in weather_cards} == {"daily", "hourly"}
    daily = next(c for c in weather_cards if c["forecast_type"] == "daily")
    assert daily["name"] == "Ecobee outdoor"
    assert daily.get("show_current") is True
    hourly = next(c for c in weather_cards if c["forecast_type"] == "hourly")
    assert hourly.get("show_current") is False
    assert not any(c.get("type") == "glance" and c.get("title") == "Ecobee" for c in cards)
    assert not any(c.get("title") == "Trailer climate" for c in cards)
    assert not any(c.get("title") == "House climate" for c in cards)
    assert not any(c.get("title") == "T2 MPPT extras" for c in cards)
    assert not any(c.get("title") == "T2 shunt extras" for c in cards)
    assert not any(c.get("title") == "KU shunt extras" for c in cards)
    assert not any(c.get("title") == "Sim dump plug W" and c.get("type") == "glance" for c in cards)
    assert not any(c.get("title") == "Sungold status" for c in cards)
    trailer_hygro = next(
        c for c in cards if c.get("type") == "glance" and c.get("title") == "Trailer hygrometer"
    )
    hygro_ids = {e["entity"] for e in trailer_hygro["entities"]}
    assert "sensor.thermo_hygrometer_caaf6f_h5072_75_tempc" in hygro_ids
    dist = next(c for c in cards if c["type"] == "distribution")
    dist_entities = {e["entity"] for e in dist["entities"]}
    assert "sensor.sungold_sph302480a_pv_power" in dist_entities
    assert "sensor.ku_unmetered_pv_est_power" not in dist_entities
    dist_names = {e["name"] for e in dist["entities"]}
    assert "Sungold AC out" in dist_names
    assert "LED+fan" not in dist_names
    assert "sensor.trailer_outlet_power" not in dist_entities
    assert "Pi4" not in dist_names
    loads_glance = next(
        c for c in cards if c.get("type") == "glance" and c.get("title") == "Loads (not losses)"
    )
    loads_names = {e["name"] for e in loads_glance["entities"]}
    assert "Sungold AC out" in loads_names
    assert "Sungold breaker" in loads_names
    assert "Trailer CT A3" in loads_names
    assert "A3 hot leg" not in loads_names
    assert "Pi4" not in loads_names
    ku = next(c for c in cards if c.get("type") == "glance" and c.get("title") == "KU 24 V (est. chargers)")
    ku_names = {e["name"] for e in ku["entities"]}
    assert "Sungold AC-in" in ku_names
    assert "LED+fan" not in ku_names
    losses_glance = next(
        c for c in cards if c.get("type") == "glance" and c.get("title") == "Conversion losses"
    )
    loss_entities = {e["entity"] for e in losses_glance["entities"]}
    assert "sensor.solar_component_losses_power" in loss_entities
    dump_ctrl = next(
        c for c in cards if c.get("type") == "entities" and c.get("title") == "Dump load HA control"
    )
    assert dump_ctrl.get("show_header_toggle") is False
    dump_ctrl_ids = {
        row.get("entity") for row in dump_ctrl["entities"] if isinstance(row, dict)
    }
    assert "input_boolean.dump_control_enabled" in dump_ctrl_ids
    assert "input_number.dump_ac_limit_t2_w" in dump_ctrl_ids
    assert "input_number.dump_ac_limit_ku_w" in dump_ctrl_ids
    assert "input_number.dump_ac_limit_sph_w" in dump_ctrl_ids
    assert "binary_sensor.dump_batt_t2_ok" in dump_ctrl_ids
    assert "sensor.battery_1_power" in dump_ctrl_ids
    assert "sensor.battery_2_power" in dump_ctrl_ids
    assert "sensor.sungold_sph302480a_load_power" in dump_ctrl_ids
    dump_card = next(
        c for c in cards if c.get("type") == "entities" and c.get("title") == "Sim dump plugs"
    )
    assert dump_card.get("show_header_toggle") is True
    dump_ids = {e["entity"] for e in dump_card["entities"]}
    expected_plugs = {f"switch.sim_ac_plug_{n}" for n in range(1, 7)}
    expected_inv = {f"input_select.dump_plug_{n}_inverter" for n in range(1, 7)}
    expected_power = {f"sensor.sim_ac_plug_{n}_power" for n in range(1, 7)}
    expected_src = {f"input_text.dump_plug_{n}_power_entity" for n in range(1, 7)}
    assert dump_ids == expected_plugs | expected_inv | expected_power | expected_src
    assert not any("dump_plug_" in e and e.endswith("_watts") for e in dump_ids)
    watts_hist = next(
        c for c in cards if c.get("type") == "history-graph" and c.get("title") == "Watts"
    )
    watts_names = {e["name"] for e in watts_hist["entities"]}
    assert "Sungold AC-in" in watts_names
    assert "Sungold AC out" in watts_names
    assert "Sungold load" not in watts_names
    kwh = next(c for c in cards if c.get("type") == "statistics-graph")
    kwh_names = {e["name"] for e in kwh["entities"]}
    assert "Sungold AC-in" in kwh_names
    assert "Sungold AC out" in kwh_names
    assert "Trailer A3" not in kwh_names
    yaml_text = DASHBOARD.read_text(encoding="utf-8")
    assert "input_boolean.sim_ac_plug" not in yaml_text
    assert "LED+fan" not in yaml_text
    assert "A3 hot leg" not in yaml_text
    dump_hist = next(
        c
        for c in cards
        if c.get("type") == "history-graph" and c.get("title") == "Sim dump plugs"
    )
    assert len(dump_hist["entities"]) == 6
    dump_w = next(
        c
        for c in cards
        if c.get("type") == "history-graph" and c.get("title") == "Sim dump plug W"
    )
    dump_w_ids = {e["entity"] for e in dump_w["entities"]}
    assert "sensor.sim_dump_load_power" in dump_w_ids
    assert "sensor.sim_ac_plug_3_power" in dump_w_ids
    sungold_ac = next(
        c for c in cards if c.get("type") == "glance" and c.get("title") == "Sungold AC"
    )
    status_ids = {e["entity"] for e in sungold_ac["entities"]}
    assert "sensor.sungold_sph302480a_fail_code" in status_ids
    assert "binary_sensor.sungold_sph302480a_fault_active" in status_ids
    assert "sensor.sungold_sph302480a_load_power" not in status_ids
    t2 = next(c for c in cards if c.get("type") == "glance" and c.get("title") == "T2 24 V")
    t2_ids = {e["entity"] for e in t2["entities"]}
    assert "sensor.solar_controller_yield_today" in t2_ids
    assert "sensor.battery_1_state_of_charge" in t2_ids
    sungold_cart = next(
        c for c in cards if c.get("type") == "glance" and c.get("title") == "Sungold cart"
    )
    cart_ids = {e["entity"] for e in sungold_cart["entities"]}
    assert "sensor.sungold_sph302480a_load_power" not in cart_ids


def test_docs_and_install_script_exist() -> None:
    text = DOCS.read_text(encoding="utf-8")
    assert "power-sankey" in text
    assert "sim_dump_control.yaml" in text
    assert "energy/save_prefs" in text
    assert "thermostat" in text
    assert "weather-forecast" in text
    assert "weather.417373300314" in text
    assert "statistics-graph" in text
    assert "sensor.battery_1_remaining_minutes" in text
    assert "Do **not** configure EM16 A3 as the electricity **grid**" in text
    assert "sensor.solar_component_losses_power" in text
    assert "combined_losses_w" in text
    assert "no** KU PV est" in text
    assert "Trailer CT A3" in text
    assert "entities" in text
    assert "switch.sim_ac_plug_1" in text
    assert "input_boolean.dump_control_enabled" in text
    assert "Dump load HA control" in text
    script = INSTALL.read_text(encoding="utf-8")
    assert "check_config" in script
    assert "docker restart homeassistant" in script
    assert "dashboards/solar-plant.yaml" in script
    assert "energy:" in script
