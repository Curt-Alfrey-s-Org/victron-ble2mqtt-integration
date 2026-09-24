# Site solar UI: charge vs load (operator)

**Applies to:** Home Assistant package `config/packages/solar_plant.yaml` and **Site solar** dashboard.

## Three buckets (live watts)

| Bucket | Sensors | Meaning |
|--------|---------|---------|
| **Charge** | `site_charge_power`, `victron_pack_charge_power`, `sungold_cart_charge_power` | Energy into storage. **T2/KU Victron** from MPPT/jumper (shunt charge power). **Sungold cart** when `sungold_cart_charge_power` > 0. **Not load.** |
| **Load** | `site_total_load_power`, `site_end_use_load_power`, `ku_stack_load_power` | Energy used, not stored on Victron packs. **End-use** = Sungold AC out (Pi4, dump, vent). **KU stack load** = cart charging from KU Renogy -> Sungold path (same W as cart charge; load **on T2/KU buses**, not house AC out). **T2 MPPT DC load** included in total. **Victron pack charge is never load.** |
| **Measured hop (not a load tile)** | `trailer_outlet_power`, `ku_renogy_ac_load_power` | KU AC **into** Sungold AC-in. When cart is **not** charging, watts here that are not stack load -> `sph_ac_in_unmatched_power` (+ conversion loss in `site_load_unaccounted_power`). |

## Why trailer ~700 W is not "Load now"

- **AC out now** ~1 W = house branch only.
- **Charge now** ~590 W = **Batt 1 + Batt 2** Victron inflow (panels/chargers), not trailer CT.
- **Trailer outlet** = AC-in meter; if cart **Batt A** ~0, those AC-in watts are **Sungold AC-in unmatched**, not missing load and not Victron charge.

When cart **is** charging, **KU stack load now** should track **Cart charge now** and trailer CT should be in the same ballpark.

## Reload after git pull

On `.105`:

```bash
cd /home/ansible/victron-ble2mqtt-integration
bash scripts/install_solar_plant_ha.sh
```

Then refresh **Site solar** in HA (storage dashboard).

See also [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md) layout section.
