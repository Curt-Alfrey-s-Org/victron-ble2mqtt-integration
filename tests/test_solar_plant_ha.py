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
    jumper_t2 = by_id["sensor.t2_ku_jumper_at_t2_power"]
    assert "sensor.t2_ku_jumper_power" in jumper_t2["state"]
    assert jumper_t2["state"].lstrip().startswith("{{ -(") or "-(" in jumper_t2["state"]
    assert jumper_t2["device_class"] == "power"
    share = by_id["sensor.ku_charger_equal_share_power"]
    assert "/ 3" in share["state"]
    ku = by_id["sensor.ku_unmetered_pv_est_power"]
    assert "sensor.battery_2_power" in ku["state"]
    assert "sensor.t2_ku_jumper_power" in ku["state"]
    assert "sensor.trailer_outlet_power" in ku["state"]
    assert by_id["sensor.battery_1_charge_power"]["device_class"] == "power"
    assert by_id["sensor.battery_1_discharge_power"]["device_class"] == "power"
    rest_blocks = data.get("rest") or []
    assert rest_blocks
    nws = rest_blocks[0]
    assert "api.weather.gov/alerts/active?point=36.32,-82.12" in nws["resource"]
    assert nws["scan_interval"] == 300
    assert nws["headers"]["User-Agent"]
    assert nws["headers"]["Accept"] == "application/geo+json"
    nws_sensor = nws["sensor"][0]
    assert nws_sensor["unique_id"] == "nws_watauga_lake_alerts"
    losses = by_id["sensor.solar_component_losses_power"]
    assert losses["device_class"] == "power"
    assert "sensor.t2_mppt_conversion_loss_power" in losses["state"]
    assert "sensor.sungold_conversion_loss_power" in losses["state"]
    t2_loss = by_id["sensor.t2_mppt_conversion_loss_power"]
    assert "sensor.solar_controller_charging_power" in t2_loss["state"]
    assert "| max" in t2_loss["state"]
    sg_loss = by_id["sensor.sungold_conversion_loss_power"]
    assert "sensor.sungold_sph302480a_charging_power" in sg_loss["state"]
    site_solar = by_id["sensor.site_solar_power"]
    assert "sensor.solar_controller_solar" in site_solar["state"]
    assert "sensor.sungold_sph302480a_pv_power" in site_solar["state"]
    assert "sensor.ku_unmetered_pv_est_power" in site_solar["state"]
    assert "| max" in site_solar["state"]
    site_charge = by_id["sensor.site_charge_power"]
    assert "sensor.battery_1_charge_power" in site_charge["state"]
    assert "sensor.battery_2_charge_power" in site_charge["state"]
    assert "sensor.sungold_sph302480a_charging_power" in site_charge["state"]
    assert "sensor.solar_controller_charging_power" not in site_charge["state"]
    assert "| max" in site_charge["state"]


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
    assert "sensor.site_solar_power" in sources
    assert "sensor.site_charge_power" in sources
    assert "sensor.site_load_power" not in sources
    assert "sensor.t2_ku_jumper_at_t2_power" not in sources
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


def _cards_from_view(view: dict) -> list:
    cards: list = []
    header = view.get("header") or {}
    if header.get("card"):
        cards.append(header["card"])
    footer = view.get("footer") or {}
    if footer.get("card"):
        cards.append(footer["card"])
    for section in view.get("sections") or []:
        cards.extend(_all_cards(section.get("cards") or []))
    cards.extend(_all_cards(view.get("cards") or []))
    return cards


def _section_tiles(view: dict, heading: str) -> list[dict]:
    for section in view.get("sections") or []:
        if section.get("type") != "grid":
            continue
        section_cards = section.get("cards") or []
        if not section_cards:
            continue
        first = section_cards[0]
        if first.get("type") == "heading" and first.get("heading") == heading:
            return [c for c in section_cards if c.get("type") == "tile"]
    return []


def _section_cards(view: dict, heading: str) -> list[dict]:
    for section in view.get("sections") or []:
        if section.get("type") != "grid":
            continue
        section_cards = section.get("cards") or []
        if not section_cards:
            continue
        first = section_cards[0]
        if first.get("type") == "heading" and first.get("heading") == heading:
            return section_cards
    return []


def _first_section_heading(view: dict) -> str | None:
    for section in view.get("sections") or []:
        if section.get("type") != "grid":
            continue
        section_cards = section.get("cards") or []
        if not section_cards:
            continue
        first = section_cards[0]
        if first.get("type") == "heading":
            return first.get("heading")
    return None


def _section_headings(view: dict) -> list[str]:
    headings: list[str] = []
    for section in view.get("sections") or []:
        if section.get("type") != "grid":
            continue
        section_cards = section.get("cards") or []
        if not section_cards:
            continue
        first = section_cards[0]
        if first.get("type") == "heading":
            heading = first.get("heading")
            if heading:
                headings.append(heading)
    return headings


def _entities_card_by_title(cards: list, title: str) -> dict:
    return next(c for c in cards if c.get("type") == "entities" and c.get("title") == title)


def test_dashboard_uses_official_cards_only() -> None:
    data = _load(DASHBOARD)
    assert data["title"] == "Solar plant"
    views = data["views"]
    now_view = views[0]
    history_view = views[1]
    for view in views:
        assert view.get("type") == "sections"
        assert view.get("max_columns") == 3
        assert view.get("dense_section_placement") is False
    cards = []
    for view in views:
        cards.extend(_cards_from_view(view))
    types = {c["type"] for c in cards}
    assert "power-sankey" in types
    assert "tile" in types
    assert "glance" not in types
    assert "vertical-stack" not in types
    assert "history-graph" in types
    assert "distribution" in types
    assert "markdown" in types
    assert "thermostat" in types
    assert "weather-forecast" in types
    assert "picture" in types
    assert "statistics-graph" in types
    assert "statistic" in types
    assert "entities" in types
    assert "heading" in types
    assert _first_section_heading(now_view) == "Site totals"
    site_cards = _section_cards(now_view, "Site totals")
    site_stat_cards = [c for c in site_cards if c.get("type") == "statistic"]
    assert len(site_stat_cards) == 3
    stat_entities = {c["entity"] for c in site_stat_cards}
    assert stat_entities == {
        "sensor.site_solar_energy_kwh",
        "sensor.site_charge_energy_kwh",
        "sensor.sungold_load_energy_kwh",
    }
    for stat_card in site_stat_cards:
        assert stat_card["stat_type"] == "change"
        assert stat_card["period"]["calendar"]["period"] == "day"
    site_tiles = [c for c in site_cards if c.get("type") == "tile"]
    site_tile_names = {t["name"] for t in site_tiles}
    assert site_tile_names == {"Solar now", "Charge now", "Load now"}
    site_tile_entities = {t["entity"] for t in site_tiles}
    assert site_tile_entities == {
        "sensor.site_solar_power",
        "sensor.site_charge_power",
        "sensor.sungold_sph302480a_load_power",
    }
    pair_types = [c["type"] for c in site_cards if c.get("type") in ("tile", "statistic")]
    assert pair_types == [
        "tile",
        "statistic",
        "tile",
        "statistic",
        "tile",
        "statistic",
    ]
    yaml_pkg = PACKAGE.read_text(encoding="utf-8")
    assert "utility_meter" not in yaml_pkg
    assert "site_load_power" not in yaml_pkg
    assert "energy-sources-table" not in DASHBOARD.read_text(encoding="utf-8")
    assert "gauge" not in types
    assert "horizontal-stack" not in types
    card_types = {c["type"] for c in cards}
    assert "grid" not in card_types
    for section in now_view.get("sections") or []:
        assert section.get("type") == "grid"
    forbidden = {"custom:", "iframe", "webpage"}
    for card in cards:
        t = card["type"]
        assert not any(t.startswith(p) for p in forbidden)
        assert "picture-elements" not in t
        if t == "history-graph":
            entities = card.get("entities") or []
            assert len(entities) <= 8
    sankey = next(c for c in cards if c["type"] == "power-sankey")
    assert sankey["layout"] == "auto"
    assert sankey["collection_key"] == "energy_dashboard"
    assert sankey.get("grid_options", {}).get("columns") == "full"
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
    radar = next(c for c in cards if c.get("type") == "picture")
    assert radar["image"] == "https://radar.weather.gov/ridge/standard/KMRX_loop.gif"
    assert radar["tap_action"]["action"] == "url"
    assert radar["tap_action"]["url_path"] == "https://radar.weather.gov/station/KMRX/standard"
    assert not any(c.get("type") == "glance" and c.get("title") == "Ecobee" for c in cards)
    assert not any(c.get("title") == "Trailer climate" for c in cards)
    assert not any(c.get("title") == "House climate" for c in cards)
    assert not any(c.get("title") == "T2 MPPT extras" for c in cards)
    assert not any(c.get("title") == "T2 shunt extras" for c in cards)
    assert not any(c.get("title") == "KU shunt extras" for c in cards)
    assert not any(c.get("title") == "Sim dump plug W" and c.get("type") == "glance" for c in cards)
    assert not any(c.get("title") == "Sungold status" for c in cards)
    hygro_tiles = [
        c
        for c in cards
        if c.get("type") == "tile"
        and c.get("entity", "").startswith("sensor.thermo_hygrometer_caaf6f_h5072_75_")
    ]
    hygro_ids = {c["entity"] for c in hygro_tiles}
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
    ku_tiles = _section_tiles(now_view, "KU 24 V (est. chargers)")
    ku_names = {t["name"] for t in ku_tiles}
    ku_ids = {t["entity"] for t in ku_tiles}
    assert "KU share est." in ku_names
    assert "Jumper from T2" in ku_names
    assert "Each charger est." not in ku_names
    assert "Sungold AC-in" not in ku_names
    assert "LED+fan" not in ku_names
    assert "sensor.ku_charger_equal_share_power" in ku_ids
    assert "sensor.t2_ku_jumper_power" in ku_ids
    assert "sensor.trailer_outlet_power" not in ku_ids
    assert not any(c.get("title") == "Conversion losses" for c in cards)
    assert not any(c.get("type") == "gauge" for c in cards)
    footer_tile = now_view["footer"]["card"]
    assert footer_tile["type"] == "tile"
    assert footer_tile["entity"] == "input_boolean.dump_control_enabled"
    assert footer_tile["features"] == [{"type": "toggle"}]
    badges = now_view.get("badges") or []
    badge_entities = {b["entity"] for b in badges}
    assert "sensor.battery_1_state_of_charge" in badge_entities
    assert "input_boolean.dump_control_enabled" in badge_entities

    now_headings = _section_headings(now_view)
    for heading in ("Dump", "Dump voltages", "Dump limits", "Dump plugs"):
        assert heading in now_headings
    assert not any(c.get("title") == "Dump load HA control" for c in cards)
    assert not any(c.get("title") == "Sim dump plugs" and c.get("type") == "entities" for c in cards)

    dump_tiles = _section_tiles(now_view, "Dump")
    dump_tile_ids = {t["entity"] for t in dump_tiles}
    assert "input_boolean.dump_control_enabled" in dump_tile_ids
    assert "binary_sensor.dump_charge_float" in dump_tile_ids
    assert "sensor.dump_next_plug" in dump_tile_ids
    assert "sensor.dump_surplus_w" in dump_tile_ids
    automations_tile = next(
        t for t in dump_tiles if t["entity"] == "input_boolean.dump_control_enabled"
    )
    assert automations_tile["features"] == [{"type": "toggle"}]

    dump_voltages = _entities_card_by_title(cards, "Dump voltages")
    assert dump_voltages.get("show_header_toggle") is False
    assert dump_voltages.get("grid_options", {}).get("columns") != "full"
    voltages_ids = {
        row.get("entity") for row in dump_voltages["entities"] if isinstance(row, dict)
    }
    assert "input_boolean.dump_soc_unsynced" in voltages_ids
    assert "input_number.dump_float_t2_v" in voltages_ids
    assert "input_number.dump_rebulk_t2_v" in voltages_ids
    assert "input_number.dump_min_solar_w" in voltages_ids

    dump_limits = _entities_card_by_title(cards, "Dump limits")
    assert dump_limits.get("show_header_toggle") is False
    limits_ids = {
        row.get("entity") for row in dump_limits["entities"] if isinstance(row, dict)
    }
    assert "input_number.dump_ac_limit_t2_w" in limits_ids
    assert "binary_sensor.dump_batt_t2_ok" in limits_ids
    assert "sensor.battery_1_power" not in limits_ids

    plug_tiles = _section_tiles(now_view, "Dump plugs")
    plug_tile_ids = {t["entity"] for t in plug_tiles}
    assert "switch.sim_ac_plug_1" in plug_tile_ids
    assert "sensor.sim_ac_plug_6_power" in plug_tile_ids
    plug_switch = next(t for t in plug_tiles if t["entity"] == "switch.sim_ac_plug_1")
    assert plug_switch["features"] == [{"type": "toggle"}]

    plug_wiring = _entities_card_by_title(cards, "Dump plug wiring")
    assert plug_wiring.get("show_header_toggle") is False
    assert plug_wiring.get("grid_options", {}).get("columns") == "full"
    wiring_ids = {e["entity"] for e in plug_wiring["entities"]}
    expected_inv = {f"input_select.dump_plug_{n}_inverter" for n in range(1, 7)}
    expected_src = {f"input_text.dump_plug_{n}_power_entity" for n in range(1, 7)}
    assert wiring_ids == expected_inv | expected_src
    assert not any("dump_plug_" in e and e.endswith("_watts") for e in wiring_ids)
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
    sungold_tiles = _section_tiles(now_view, "Sungold")
    sungold_ids = {t["entity"] for t in sungold_tiles}
    sungold_names = {t["name"] for t in sungold_tiles}
    assert "sensor.sungold_sph302480a_fail_code" in sungold_ids
    assert "binary_sensor.sungold_sph302480a_fault_active" in sungold_ids
    assert "sensor.sungold_sph302480a_load_power" in sungold_ids
    assert "sensor.trailer_outlet_power" in sungold_ids
    assert "sensor.em16_a3_power" in sungold_ids
    assert "sensor.sungold_conversion_loss_power" in sungold_ids
    assert "Sungold AC-in" in sungold_names
    assert "Sungold AC out" in sungold_names
    assert "Trailer CT A3" in sungold_names
    assert "Sungold breaker" in sungold_names
    assert "A3 hot leg" not in sungold_names
    assert "Pi4" not in sungold_names
    t2_tiles = _section_tiles(now_view, "T2 24 V")
    t2_ids = {t["entity"] for t in t2_tiles}
    t2_names = {t["name"] for t in t2_tiles}
    assert "sensor.solar_controller_yield_today" in t2_ids
    assert "sensor.battery_1_state_of_charge" in t2_ids
    assert "sensor.t2_mppt_conversion_loss_power" in t2_ids
    assert "Jumper to KU" in t2_names
    assert "sensor.t2_ku_jumper_at_t2_power" in t2_ids
    assert "sensor.t2_ku_jumper_power" not in t2_ids
    assert not any(c.get("title") == "Sungold cart" for c in cards)
    assert not any(c.get("title") == "Sungold AC" for c in cards)
    for graph in [c for c in cards if c.get("type") in ("history-graph", "statistics-graph")]:
        assert graph.get("grid_options", {}).get("columns") == "full"
    assert history_view.get("type") == "sections"


def test_docs_and_install_script_exist() -> None:
    text = DOCS.read_text(encoding="utf-8")
    assert "power-sankey" in text
    assert "sim_dump_control.yaml" in text
    assert "energy/save_prefs" in text
    assert "thermostat" in text
    assert "weather-forecast" in text
    assert "weather.417373300314" in text
    assert "KMRX_loop.gif" in text
    assert "sensor.nws_watauga_lake_alerts" in text
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
    assert "Dump voltages" in text
    assert "Dump plugs" in text
    assert "KU share est." in text
    assert "Do **not** put Sungold A/C-in here" in text
    assert "Jumper from T2" in text
    assert "sensor.t2_ku_jumper_at_t2_power" in text
    assert "Negative = leaving T2" in text
    assert "Gauges (PV)" not in text
    assert "Gauges (batteries)" not in text
    assert "type: sections" in text or "sections view" in text
    assert "tile" in text
    assert "Site totals" in text
    assert "site_solar_power" in text
    assert "stat_type: change" in text or "dashboards/statistic" in text
    assert "mobile_app:" in text
    assert "Do **not** add" in text and "default_config:" in text
    script = INSTALL.read_text(encoding="utf-8")
    assert "check_config" in script
    assert "docker restart homeassistant" in script
    assert "dashboards/solar-plant.yaml" in script
    assert "energy:" in script
    assert "mobile_app:" in script
    assert "sim_dump_control.yaml" in script
    assert 'if [[ -f "$DUMP_DST" && -f "$DUMP_SRC" ]]' in script
    assert "default_config:" not in script or "Do not add default_config" in script
    assert not any(
        line.strip() == "default_config:" for line in script.splitlines()
    )
