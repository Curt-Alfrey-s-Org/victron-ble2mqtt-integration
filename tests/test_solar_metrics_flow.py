"""Node-RED /solar/metrics exposes the computed cache. It does not recalculate."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "flows" / "solar_computed_meters.json"
JS = ROOT / "scripts" / "nodered_solar_computed.js"

# Keys returned by computeSolarDerived. The metrics node prints whatever is
# numeric on that object. These must stay in the JS return so the Grafana
# one-line field names keep matching.
DERIVED_KEYS = (
    "t2_mppt_w",
    "t2_mppt_charge_w",
    "t2_ku_jumper_w",
    "ku_victron_mppt23_est_w",
    "ku_pwm_mppt_combined_est_w",
    "ku_pwm_est_w",
    "ku_charger_equal_share_w",
    "em16_a3_live_w",
    "em16_b3_live_w",
    "trailer_outlet_w",
    "sungold_pv_w",
    "sungold_ac_in_w",
    "sungold_batt_in_w",
    "sungold_ac_out_w",
    "sungold_cart_to_load_w",
    "site_solar_w",
    "site_source_w",
    "site_total_load_w",
    "load_unaccounted_w",
    "battery_1_w",
    "battery_2_w",
)


def test_metrics_route_uses_cache_not_a_second_formula() -> None:
    nodes = json.loads(FLOW.read_text(encoding="utf-8"))
    urls = [n.get("url") for n in nodes if n.get("type") == "http in"]
    assert "/solar/metrics" in urls
    fn = next(n for n in nodes if n.get("id") == "computed-metrics-fn")
    body = fn["func"]
    assert "solarComputedLast" in body
    assert "solar_plant_watts" in body
    assert "solar_plant_panel_watts" in body
    assert "text/plain; version=0.0.4" in body
    assert "# TYPE solar_plant_watts gauge" in body
    assert "2 * " not in body
    assert "computeSolarDerived" not in body
    assert "solar_plant_socket" in body
    assert "key === 'sockets'" in body


def test_derived_keys_still_in_the_only_math_module() -> None:
    text = JS.read_text(encoding="utf-8")
    for key in DERIVED_KEYS:
        assert f"{key}:" in text
    assert 'states["switch.ihoment_h5082_" + id]' in text
    assert "input_text.h5082_" in text
    assert "input_select.h5082_" in text
    assert '["82FB", "left"]' in text
    assert "sockets: socketSamples(states)" in text
