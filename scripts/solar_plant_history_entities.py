"""Entity IDs whose recorder states / statistics belong to the solar plant site.

Used by scripts/purge_solar_plant_ha_history.py. Climate / Ecobee and NWS alerts
are excluded (not site power math).
"""

from __future__ import annotations

# solar_plant.yaml templates, integrals, utility_meter (fixed ids).
SOLAR_PLANT_PACKAGE_ENTITY_IDS: tuple[str, ...] = (
    "sensor.t2_ku_jumper_power",
    "sensor.t2_ku_jumper_at_t2_power",
    "sensor.trailer_outlet_power",
    "sensor.ku_unmetered_pv_est_power",
    "sensor.ku_charger_equal_share_power",
    "sensor.battery_1_charge_power",
    "sensor.battery_1_discharge_power",
    "sensor.battery_2_charge_power",
    "sensor.battery_2_discharge_power",
    "sensor.t2_mppt_conversion_loss_power",
    "sensor.sungold_uti_va_power",
    "sensor.sungold_ac_out_va_power",
    "sensor.sungold_conversion_loss_power",
    "sensor.solar_component_losses_power",
    "sensor.site_solar_power",
    "sensor.site_charge_power",
    "sensor.t2_mppt_energy_kwh",
    "sensor.battery_1_charge_energy_kwh",
    "sensor.battery_1_discharge_energy_kwh",
    "sensor.battery_2_charge_energy_kwh",
    "sensor.battery_2_discharge_energy_kwh",
    "sensor.em16_a3_energy_kwh",
    "sensor.sim_dump_energy_kwh",
    "sensor.sungold_load_energy_kwh",
    "sensor.site_solar_energy_kwh",
    "sensor.site_charge_energy_kwh",
    "sensor.site_solar_today",
    "sensor.site_charge_today",
    "sensor.sungold_load_today",
)

# Match live Victron MQTT, Sungold modbus, sim dump packages on HA.
SOLAR_ENTITY_ID_PREFIXES: tuple[str, ...] = (
    "sensor.solar_controller_",
    "sensor.battery_1_",
    "sensor.battery_2_",
    "sensor.sungold_",
    "sensor.site_solar",
    "sensor.site_charge",
    "sensor.t2_",
    "sensor.ku_",
    "sensor.trailer_",
    "sensor.em16_",
    "sensor.sim_dump_",
    "sensor.sim_ac_plug_",
    "sensor.dump_",
    "binary_sensor.dump_",
    "binary_sensor.sungold_",
)

EXCLUDED_ENTITY_PREFIXES: tuple[str, ...] = (
    "sensor.nws_",
    "sensor.417373300314_",
    "climate.",
    "binary_sensor.417373300314_",
)


def entity_id_excluded(entity_id: str) -> bool:
    return any(entity_id.startswith(p) for p in EXCLUDED_ENTITY_PREFIXES)


def matches_solar_prefix(entity_id: str) -> bool:
    if entity_id_excluded(entity_id):
        return False
    return any(entity_id.startswith(p) for p in SOLAR_ENTITY_ID_PREFIXES)


def merge_purge_entity_ids(
    discovered: list[str] | None = None,
) -> list[str]:
    """Sorted unique entity ids to purge (states + statistics)."""
    ids: set[str] = set(SOLAR_PLANT_PACKAGE_ENTITY_IDS)
    if discovered:
        for eid in discovered:
            if matches_solar_prefix(eid) or eid in SOLAR_PLANT_PACKAGE_ENTITY_IDS:
                if not entity_id_excluded(eid):
                    ids.add(eid)
    return sorted(ids)
