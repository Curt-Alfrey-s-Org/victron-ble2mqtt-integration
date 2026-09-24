# Solar HA: device sensors only (policy)

**Effective:** removed template **site total** sensors and **duplicate tiles** from
`config/dashboards/solar-plant.yaml`. **Now** view: one tile per device entity
(Victron BLE, Sungold Modbus, EM16). Header SoC badges only.

## Removed (do not re-add without operator approval)

- `sensor.site_solar_power`, `site_charge_power`, `site_source_power`,
  `site_total_load_power`, `site_load_*`, `*_today` site integrals
- Riemann `integration` / `utility_meter` rows in `solar_plant.yaml` (kWh tiles)
- Dashboard **Quick meters**, **Instant W** distribution, duplicate tiles (same entity twice)
- Template dump status tiles on the main view (`dump_surplus_w`, `dump_bus_load_*`, binary gates)
- Jumper math: `t2_ku_jumper_*`, `ku_unmetered_pv_est_*`, `ku_charger_equal_share_*`
- AC merge/loss estimates: `trailer_outlet_power`, `ku_renogy_ac_load_power`,
  `sph_ac_in_unmatched_power`, `sungold_*_va_power`, `*_conversion_loss_*`,
  `solar_component_losses_power`, `sungold_cart_to_load_power`, charge/discharge splits

## Use instead

| Question | Read this entity (device) |
|----------|---------------------------|
| T2 solar W | `sensor.solar_controller_solar` |
| T2 pack W | `sensor.battery_1_power` (sign = shunt) |
| KU pack W | `sensor.battery_2_power` |
| Sungold PV | `sensor.sungold_sph302480a_pv_power` |
| Cart charge W | `sensor.sungold_sph302480a_charging_power` |
| Sungold AC out | `sensor.sungold_sph302480a_load_power` |
| Trailer / breaker clamp | `sensor.em16_a3_power`, `sensor.em16_b3_power` |
| Sungold AC-in (inverter) | `sensor.sungold_sph302480a_grid_voltage` / `grid_current` |

Dump automations still use **small templates inside** `sim_dump_control.yaml`
(for staging confirm and T2+PV compare). Those are not shown on the Site solar tiles.

## Deploy

From `.105` after `git pull`:

```bash
cd /home/ansible/victron-ble2mqtt-integration
bash scripts/install_solar_plant_ha.sh
HA_TOKEN_FILE=... python3 scripts/save_solar_plant_storage_dashboard.py
```

Old computed entities may remain in **History** until purged; remove stale entities
in **Settings > Devices & services > Entities** if needed.
