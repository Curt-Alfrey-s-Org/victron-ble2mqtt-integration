# ALFa AI and this Victron / Home Assistant edge

**Status (2026-09-15):** Pi collectors stay **read-only MQTT** (no `mqtt_publish`
back to Victron hardware). **Load control** (smart plugs / relays) is owned by
**alfa-ai on `.111`**, which calls Home Assistant's official REST API on `.105:8123`
using operator Settings and an entity allowlist.

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
| **Simulated** dump-load plugs (no hardware) | [SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md) -- six `switch.sim_ac_plug_*` on `.105` (YAML package; opt-in) |
| **GX-style solar flow page** | [SOLAR_FLOW_DASHBOARD.md](SOLAR_FLOW_DASHBOARD.md) -- production on `.105` like HA: LAN `:8765` + Tailscale MagicDNS `:8765`; HA REST proxy; dump-load panel read-only |

## Safety

- Victron BLE / Sungold USB publishers remain **sensor-only**.
- alfa-ai may `switch.turn_on` / `turn_off` only for **allowlisted** HA entities.
- Battery / charge-cycle **advice** (if added later) must still include a hardware
  disclaimer and point at Victron manuals.
- Empty allowlist or `ALFA_AI_HOME_ASSISTANT_ENABLED=0` means no toggles.
