# H5082 plugs, then the Grafana one-line

**Status:** plan. Plugs are not installed. Grafana is not redrawn.
**Resume here:** the first checkpoint whose box is still `[ ]`.
**Do not start at the Grafana redraw.**

Operator decision (2026-09-25), over the older "no HACS / write an MQTT sidecar" notes in [SIM_DUMP_PLUGS.md](SIM_DUMP_PLUGS.md) and [DUMP_LOAD_HA_CONTROL.md](DUMP_LOAD_HA_CONTROL.md):

- Those repo notes are **not** the install authority.
- Install the plugs the way [HACS](https://www.hacs.xyz/docs/setup/download) and the Govee integration docs say. Do not write a new BLE or MQTT bridge unless that install cannot see an H5082.
- Pairing the hardware is the Govee Home app (2.4 GHz Wi-Fi only). HA does not replace that step.

## What the operator asked for

```text
devices: 8 H5082 plugs
sockets: 16 (2 per plug)
dump loads at start: 4 sockets (2 plugs)
the other 12: normal loads, switched by hand, until assigned as dump
```

Each socket must:

- Turn on and off **by hand** in Home Assistant (the integration's switch).
- Turn on and off **by the dump automation** only when that socket is assigned **dump**.
- Be movable between **normal** and **dump** without reinstalling. Changing the assignment does not rename the switch.

A normal socket is never turned on or off by the dump automations. A dump socket still has a manual switch. The physical button on the plug still works. That is the Govee manual, not a second control path we invent.

## Checkpoint 0 — count

`[x]` 8 plugs, 16 sockets, 4 dump / 12 normal.

## Checkpoint 1 — HACS on the `.105` container

`[x]` Downloaded with the Container script from [Downloading HACS](https://www.hacs.xyz/docs/use/download/download/) (`wget -O - https://get.hacs.xyz | bash -` inside `homeassistant`). Minimum HA version check passed (2026.7.3 >= 2024.4.1). Container restarted. `/config/custom_components/hacs/manifest.json` is present. HA reported healthy.

`[x]` Operator completed the GitHub device login, then cleared the Home Assistant repair for HACS. Config entry domain `hacs` is `loaded`. HACS is in the sidebar. Do not reinstall HACS.

## Checkpoint 2 — install the integration the maintainer documents

`[x]` Downloaded [Govee Cloud Integration](https://github.com/lasswellt/govee-homeassistant) **2026.9.14** with HACS (`hacs/download`, repository id `1060642665`). Files are `/config/custom_components/govee/`. Home Assistant was restarted and is healthy. The `govee` config flow is available. Not configured yet.

`[ ]` Operator: in the Govee Home app, Profile → Settings → Apply for API Key. Then in HA, Settings → Devices & services → Add integration → **Govee Cloud Integration**, and paste that key. Do not put the key in git. Account login is optional.

`[ ]` Do **not** use the abandoned [LaggAt/hacs-govee](https://github.com/LaggAt/hacs-govee) path. Its own issue tracker says H5082 did not work there.

Two current HACS integrations:

| Integration | Docs | Use it when |
|---|---|---|
| [Govee Cloud Integration](https://github.com/lasswellt/govee-homeassistant) | HACS → custom repository `https://github.com/lasswellt/govee-homeassistant`, category Integration. API key from the Govee Home app: Profile → Settings → Apply for API Key. Account login is optional and is what that README says turns on real-time push. | **First.** H5082 is a Wi-Fi plug. This integration builds entities from the capabilities Govee reports, and it already documents per-outlet switches for multi-outlet plugs. `.105` has no Bluetooth radio. |
| [Govee BLE Smart Plug](https://github.com/virtuald/govee-ble-plugs) | HACS custom repository. README lists **H5082 Dual Smart Plug** by name. Requires Home Assistant Bluetooth. | **Only if** Checkpoint 3 shows the cloud integration did not create two switches for an H5082. Not the first try: this HA container does not have Bluetooth. |

Pass: the integration is installed and restarted the way that README says. API key is typed into the HA config flow, not committed.

## Checkpoint 3 — sixteen switches exist

`[ ]` After the plugs are in the Govee Home app, HA shows **two switch entities per plug** (16). If a plug arrives as one switch, stop. Report the entity list and the integration diagnostics. Do not invent a sidecar in that same session.

Record the 16 `entity_id`s in this file when they exist. Do not guess them before discovery.

## Checkpoint 4 — normal vs dump, manual vs auto

`[ ]` Add one [input_select](https://www.home-assistant.io/integrations/input_select/) per socket, options `normal` and `dump`. Default **normal**. The operator sets **dump** on the 4 sockets that are the two dump plugs. Helpers stay editable under Settings → Helpers.

Rules:

- **Manual:** the Govee switch. Always. Dashboard tile and Developer Tools. Works in either assignment.
- **Auto:** `sim_dump_control.yaml` may call `switch.turn_on` / `turn_off` only when that socket's select is `dump`. A `normal` socket is not in the shed list, the add list, or the all-off list.
- Reassigning is changing the select. No package rewrite, no entity rename.
- Retire the hardcoded `switch.sim_ac_plug_1`…`_6` list. The dump package reads the selects.
- Sim template switches stay installed until one real dump socket has been turned on and off by the automation **and** by hand. Then remove `sim_dump_plugs.yaml` from the HA packages and from git. Do not delete them first.

## Checkpoint 5 — Node-RED

`[ ]` `/solar/metrics` gains one sample per socket that already exists in HA (on/off, and watts only if that integration created a power sensor). No second watt math. Redeploy with `scripts/deploy-nodered-solar.sh` only.

## Checkpoint 6 — Grafana, after the switches are real

`[ ]` Redraw the one-line in three left-to-right bands. Under Sungold AC out, one card per socket that is currently **dump**, and the normal sockets grouped as a manual row so they are not mixed into the dump path. Do not draw the six sim plugs.

## Checkpoint 7 — done

`[ ]` A normal socket toggles from HA and the dump automation does not touch it.
`[ ]` A dump socket toggles from HA **and** from the dump automation.
`[ ]` Changing the select moves a socket between those two behaviors.
`[ ]` Sim switches are gone.
`[ ]` Grafana matches that split.

## Where a new session starts

Checkpoint **2**, the Govee API key in the Home Assistant config flow. HACS and the integration files are already on `.105`. Do not download them again. Do not write a Govee client. Do not redraw Grafana.
