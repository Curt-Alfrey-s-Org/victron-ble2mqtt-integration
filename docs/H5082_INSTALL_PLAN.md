# H5082 plugs, then the Grafana one-line

**Status:** Bluetooth chosen. Cloud API key is not the path. Plugs are not installed. Grafana is not redrawn.
**Resume here:** the first checkpoint whose box is still `[ ]`.
**Do not start at the Grafana redraw. Do not take `hci0`.**

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

## Checkpoint 2 — Bluetooth, not the cloud key

`[x]` Operator chose local Bluetooth. No Govee account. The downloaded Govee Cloud Integration stays unused. Do not paste an API key.

`[x]` Pi 4 radios, checked 2026-09-25, not changed:

| Adapter | Bus | Address | Who uses it |
|---|---|---|---|
| `hci0` | USB TP-Link `2357:0604` | `B0:19:21:E3:A4:72` | **Victron.** `BLE_ADAPTER=hci0`. Do not share it and do not move this dongle. |
| `hci1` | UART, the Pi's own chip | `2C:CF:67:3F:1C:D4` | Up, not used by Victron. This is the spare radio. |

Home Assistant on `.105` has no Bluetooth radio. Its Bluetooth docs only accept a local adapter, USB/IP of a USB adapter, or an ESPHome proxy that can hold an active connection ([Bluetooth](https://www.home-assistant.io/integrations/bluetooth/), [remote adapters](https://www.home-assistant.io/integrations/bluetooth/#remote-adapters-bluetooth-proxies)). The spare radio is not USB, so USB/IP cannot move it. Shelly proxies cannot make the active connection an H5082 needs.

`[x]` Spare radio `hci1` can see all 8 plugs. A 20s Bleak scan on `hci1` only (not `hci0`) heard `ihoment_H5082_` advertisements for `C061`, `82FB`, `2F9D`, `CF79`, `3EC9`, `9607`, `3013`, and `C38D`.

`[ ]` Pair each plug with the button procedure in [virtuald/govee-ble-plugs](https://github.com/virtuald/govee-ble-plugs) `GoveePlugPairer` (message `aa b1`, reply `aa b1 01` is the key). GATT on `82FB` is the project's service, but the plug answered **need button**, not a key. Keys go in `/home/n4s1/.govee-h5082-keys` mode `600` on the Pi, never in git. Then publish one MQTT switch per socket. Do not write a second protocol.

## Retired — cloud install

Downloaded [Govee Cloud Integration](https://github.com/lasswellt/govee-homeassistant) **2026.9.14** into `/config/custom_components/govee/`. Not configured. Do not paste an API key. Do not use [LaggAt/hacs-govee](https://github.com/LaggAt/hacs-govee).

## Checkpoint 3 — sixteen switches exist

`[ ]` After Checkpoint 2, HA shows **two MQTT switches per plug** (16). If a plug arrives as one switch, stop. Do not guess entity ids before discovery.

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

Checkpoint **2**, the open box: H5082 Bluetooth on Pi 4 `hci1` only. Do not touch `hci0`. Do not paste a Govee API key. Do not redraw Grafana.
