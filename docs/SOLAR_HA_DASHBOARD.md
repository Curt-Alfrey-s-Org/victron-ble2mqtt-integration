# Solar plant (Home Assistant Lovelace)

**Canonical operator power-flow view** is this Lovelace dashboard on **`.105:8123`**.
The custom SVG proxy on `:8765` is **retired** ([SOLAR_FLOW_DASHBOARD.md](SOLAR_FLOW_DASHBOARD.md)).

Home Assistant already holds the Victron, shunt, Refoss, Sungold, and sim-dump
entities. This dashboard uses **stock cards** only:

- [Energy cards](https://www.home-assistant.io/dashboards/energy/) (`power-sankey`)
- [Glance](https://www.home-assistant.io/dashboards/glance/)
- [Gauge](https://www.home-assistant.io/dashboards/gauge/)
- [History graph](https://www.home-assistant.io/dashboards/history-graph/)
- [Distribution](https://www.home-assistant.io/dashboards/distribution/)
- [Markdown](https://www.home-assistant.io/dashboards/markdown/)

YAML dashboards: [Adding YAML dashboards](https://www.home-assistant.io/dashboards/dashboards/#adding-yaml-dashboards).
Packages: [Configuration packages](https://www.home-assistant.io/docs/configuration/packages/).
Template sensors: [Template](https://www.home-assistant.io/integrations/template/).
Watt-hours from watts: [Integral (Riemann)](https://www.home-assistant.io/integrations/integration/).
Energy sources: [Home energy management](https://www.home-assistant.io/docs/energy/).

Dump ON/OFF stays in alfa-ai `solar_dump.py` (deterministic). This dashboard does
**not** actuate plugs.

**Do not** add hops, SVG wires, or Node-RED for this view.

Site physics (two 24 V buses, jumper estimate, A3 = trailer outlet total):
[SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md).

The existing storage-mode sidebar item **Solar** (`dashboard-solar`) stays as the
MQTT/Sungold **entity list**. This YAML dashboard is **Solar plant**
(`/solar-plant`).

---

## What you get

| Surface | Role |
|---------|------|
| **Solar plant** Lovelace | Live W glance + gauges + `power-sankey` (after Energy is configured) |
| Template sensors | Jumper est., trailer outlet W, KU PV est., KU equal-share est. |
| Integral sensors | kWh from live W (T2 MPPT, battery charge/discharge, trailer outlet, dump, Sungold load) |

HA Energy / `power-sankey` is a **sources / battery / home / devices** Sankey, not a
Victron GX two-bus cartoon. KU MPPT/PWM remain **estimates** (no live Victron clamps).

---

## Template entity ids

| entity_id | Meaning |
|-----------|---------|
| `sensor.t2_ku_jumper_power` | Est. `solar_controller_solar - battery_1_power` (T2 Renogy idle = 0). + = T2 to KU. |
| `sensor.trailer_outlet_power` | `\|B3\|` if \|B3\| >= 0.5 W, else `\|A3\|` |
| `sensor.ku_unmetered_pv_est_power` | `battery_2_power - jumper + trailer_outlet` |
| `sensor.ku_charger_equal_share_power` | KU PV est. / 3 (MPPT 1, MPPT 2, PWM each) |
| `sensor.battery_1_charge_power` / `_discharge_power` | `max(0, +/- battery_1_power)` |
| `sensor.battery_2_charge_power` / `_discharge_power` | same for Battery 2 |

Do **not** treat KU equal-share as a live Victron watt clamp. Do **not** add A3 as
utility grid.

---

## Enable on `.105` (one path)

**Prerequisites:** HA Container `homeassistant`, config `/opt/homeassistant`, victron
clone pulled.

```bash
cd /home/ansible/victron-ble2mqtt-integration
bash scripts/install_solar_plant_ha.sh
```

The script copies the package and dashboard YAML, appends `lovelace:` / `recorder:` /
`history:` / `energy:` when missing, runs
`python -m homeassistant --script check_config -c /config` inside the container
([check configuration](https://www.home-assistant.io/docs/configuration/troubleshooting/)),
then `docker restart homeassistant`
([Container install](https://www.home-assistant.io/installation/linux#install-home-assistant-container)).
This HA has no `default_config:`. Recorder/history are required for graphs; Energy
(`energy`) is required for **Settings > Dashboards > Energy**
([default config](https://www.home-assistant.io/integrations/default_config/),
[Energy FAQ](https://www.home-assistant.io/docs/energy/faq/#the-energy-dashboard-is-not-visible)).

Open:

```text
http://192.168.0.105:8123/solar-plant
```

YAML dashboard reload after later file edits: dashboard three-dots **Refresh**
(not only the browser reload).

---

## Energy dashboard (once, UI)

`power-sankey` stays empty until Energy sources exist
([Energy cards](https://www.home-assistant.io/dashboards/energy/)). There is no
supported YAML for the Energy config store. In HA:

**Settings > Dashboards > Energy**

Add **power** sensors (W) and the matching **integral kWh** sensors after they
appear:

| Energy slot | Power (W) | Energy (kWh, after integral exists) |
|-------------|-----------|-------------------------------------|
| Solar | `sensor.solar_controller_solar` | `sensor.t2_mppt_energy_kwh` |
| Battery T2 | charge `sensor.battery_1_charge_power`, discharge `sensor.battery_1_discharge_power` | matching `*_energy_kwh` |
| Battery KU | charge/discharge `sensor.battery_2_*` | matching `*_energy_kwh` |
| Device: trailer A/C | `sensor.trailer_outlet_power` (always >= 0 W) | `sensor.em16_a3_energy_kwh` |
| Device: sim dump | `sensor.sim_dump_load_power` | `sensor.sim_dump_energy_kwh` |
| Device: Sungold A/C out | `sensor.sungold_sph302480a_load_power` | `sensor.sungold_load_energy_kwh` |

**Individual devices** (after Trailer A/C): add **Sungold load energy kWh**, then
**Sim dump energy kWh**. In the picker, skip Battery charge/discharge, T2 MPPT kWh, and
**A1 this month energy** -- those are already solar/battery sources, not loads.
Sungold kWh uses live `sensor.sungold_sph302480a_load_power` (MQTT id
`load_power`; friendly name still "Load active power").

Energy may warn `sensor.battery_1_discharge_energy_kwh` is **unknown** while Battery 1
is only charging (discharge watts stay `0`). The Integral helper does not leave
`unknown` until its source changes
([Integral data updates](https://www.home-assistant.io/integrations/integration/#data-updates)).
That is not a bad battery config. It clears on the first T2 discharge, or after
[Developer tools > States](https://www.home-assistant.io/docs/tools/dev-tools/)
sets `sensor.battery_1_discharge_power` to `0` so the helper records a sample.

Do **not** configure EM16 A3 as the electricity **grid**. This site is not on
utility import. Do **not** add KU equal-share as a second solar source (double-count).

`sensor.em16_a3_power` is a signed CT. Integrating it made `sensor.em16_a3_energy_kwh`
negative (`-0.02` kWh) and Energy warned that individual devices need a positive
state. The integral source is `sensor.trailer_outlet_power` (absolute watts). If
the warning remains, adjust that entity in
[Settings > Tools > Statistics](https://www.home-assistant.io/docs/energy/faq/#why-is-my-energy-dashboard-showing-inflated-totals).

Integral sensors use Riemann **left** + `max_sub_interval` 5 minutes per the
[Integral energy example](https://www.home-assistant.io/integrations/integration/#energy).

If glance history is empty, this HA instance has no `default_config:` -- the
install script adds `recorder:` and `history:` when missing
([Recorder](https://www.home-assistant.io/integrations/recorder/),
[History](https://www.home-assistant.io/integrations/history/)).
It also adds `energy:` so the Energy settings page exists
([Energy FAQ](https://www.home-assistant.io/docs/energy/faq/#the-energy-dashboard-is-not-visible)).

---

## Retired SVG (`:8765`)

The custom GX proxy is gone. After pull on `.105`:

```bash
bash scripts/uninstall_solar_flow.sh
```
