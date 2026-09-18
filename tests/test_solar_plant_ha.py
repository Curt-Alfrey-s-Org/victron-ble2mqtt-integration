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
    assert "statistics-graph" in types
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
    dist = next(c for c in cards if c["type"] == "distribution")
    dist_entities = {e["entity"] for e in dist["entities"]}
    assert "sensor.sungold_sph302480a_pv_power" in dist_entities
    assert "sensor.ku_unmetered_pv_est_power" not in dist_entities
    dist_names = {e["name"] for e in dist["entities"]}
    assert "LED+fan" in dist_names
    assert "Pi4" in dist_names
    losses_glance = next(
        c for c in cards if c.get("type") == "glance" and c.get("title") == "Conversion losses"
    )
    loss_entities = {e["entity"] for e in losses_glance["entities"]}
    assert "sensor.solar_component_losses_power" in loss_entities


def test_docs_and_install_script_exist() -> None:
    text = DOCS.read_text(encoding="utf-8")
    assert "power-sankey" in text
    assert "solar_dump.py" in text
    assert "energy/save_prefs" in text
    assert "thermostat" in text
    assert "statistics-graph" in text
    assert "sensor.battery_1_remaining_minutes" in text
    assert "Do **not** configure EM16 A3 as the electricity **grid**" in text
    assert "sensor.solar_component_losses_power" in text
    assert "combined_losses_w" in text
    assert "no** KU PV est" in text
    script = INSTALL.read_text(encoding="utf-8")
    assert "check_config" in script
    assert "docker restart homeassistant" in script
    assert "dashboards/solar-plant.yaml" in script
    assert "energy:" in script
