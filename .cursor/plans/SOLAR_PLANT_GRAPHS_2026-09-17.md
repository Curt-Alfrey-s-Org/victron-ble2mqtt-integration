# Solar plant graphs — extra live datapoints

**Goal:** Put remaining live plant sensors on Solar plant **Now** glances and **History** graphs using stock HA cards. Do not add them as Energy grid/solar.

Official: [history-graph](https://www.home-assistant.io/dashboards/history-graph/) (max 8 entities/card; group by unit), [glance](https://www.home-assistant.io/dashboards/glance/), [thermostat](https://www.home-assistant.io/dashboards/thermostat/), [statistics-graph](https://www.home-assistant.io/dashboards/statistics-graph/), [distribution](https://www.home-assistant.io/dashboards/distribution/).

## Objectives

1. Docs in `docs/SOLAR_HA_DASHBOARD.md`: which extra entities go on Solar plant graphs vs stay Energy-only vs stay on the MQTT **Solar** list.
2. `config/dashboards/solar-plant.yaml` + `tests/test_solar_plant_ha.py`: Now glances, thermostat, Instant W; History graphs by unit (W/V/A/%/F) and kWh statistics-graph. Max 8 entities per history-graph.

## Out of scope

Energy `save_prefs` grid/carbon/gas/water/KU solar/A1. New Riemann helpers. SVG/Node-RED. alfa-ai. Cluster start/stop. `solar_plant.yaml` package.

## Acceptance

`python -m pytest tests/test_solar_plant_ha.py -q`
