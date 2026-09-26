# ALFa AI and this Victron / Home Assistant edge

**Status (2026-09-20):** Pi collectors stay **read-only MQTT** (no `mqtt_publish`
back to Victron hardware). **Dump on/off** is Home Assistant
(`sim_dump_control.yaml`). alfa-ai on `.111` **observes** HA REST; it does not
toggle dumps. Operator UI is built-in **Energy**.

Do not scrape Lovelace (`/dashboard-solar/0`). Official API:
[REST API](https://developers.home-assistant.io/docs/api/rest/).

Canonical runbook (token, settings, dump-load physics):
[alfa-ai docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md)
(local sibling: `../alfa-ai/docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md`).

## What is live on this repo

| Surface | Location |
|---------|----------|
| Pi edge stack (BLE -> MQTT -> HA) | `DEPLOY.md`, `scripts/deploy.sh` |
| Cluster / hub integration | `docs/ALFA_CLUSTER_INTEGRATION.md` |
| Power buses (T2 vs KU, EM16 A3) | `docs/SOLAR_POWER_BALANCE.md` -- 10-11 Sep A3 = trailer; 15 Sep A3 = Sungold AC-in |
| Dump-load plugs must sit on the **intended AC circuit** | Fed from **Sungold AC out**, not KU Renogy; 15 Sep A3 clamp is Sungold AC-in; see SOLAR_POWER_BALANCE |
| H5082 sockets | [H5082_INSTALL_PLAN.md](H5082_INSTALL_PLAN.md) -- 16 switches on Site solar. Sim dump plugs are retired. |
| **Solar (HA Energy)** | [SOLAR_HA_DASHBOARD.md](SOLAR_HA_DASHBOARD.md) -- canonical live W/kWh on `.105:8123/energy`; dump helpers in HA |

## Safety

- Victron BLE / Sungold USB publishers remain **sensor-only**.
- alfa-ai may `switch.turn_on` / `turn_off` only for **allowlisted** HA entities.
- Battery / charge-cycle **advice** (if added later) must still include a hardware
  disclaimer and point at Victron manuals.
- Empty allowlist or `ALFA_AI_HOME_ASSISTANT_ENABLED=0` means no toggles.
