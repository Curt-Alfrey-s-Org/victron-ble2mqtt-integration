# H5082 plugs, then the Grafana one-line

**Status:** Bluetooth chosen. Cloud API key is not the path. Plugs are not installed. Grafana is not redrawn.
**Resume here:** Checkpoint 7 on `.105`. `dump_control.yaml` reads the per-socket selects (2026-09-28). `C38D` remains state-only until a key exists and is never a dump socket.
**Do not start at the Grafana redraw. Do not take `hci0`.**

Operator decision (2026-09-25), over the older "no HACS / write an MQTT sidecar" notes (the retired sim dump plug doc) and [DUMP_LOAD_HA_CONTROL.md](DUMP_LOAD_HA_CONTROL.md):

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

`[ ]` Pair each plug with the button procedure in [virtuald/govee-ble-plugs](https://github.com/virtuald/govee-ble-plugs) `GoveePlugPairer` (message `aa b1`, reply `aa b1 01` is the key). Arm every unpaired plug at once (`/home/n4s1/bin/h5082_listen.py` on `hci1`). A press on any socket is the pairing press for that whole plug. Keys go in `/home/n4s1/.govee-h5082-keys` mode `600` on the Pi, never in git. Then publish one MQTT switch per socket. Do not write a second protocol.

Partial, listener stopped 2026-09-25 at the operator's "done": **7 keys saved** (`2F9D`, `CF79`, `3EC9`, `3013`, `82FB`, `C061`, `9607`). **`C38D` is not paired.** (Correction 2026-09-28: an earlier note here said the Pi 4 was powered from C38D. It is not; the Pi 4 is not plugged into any H5082.) Before pressing a plug's button to pair it, check that socket's **Load** in HA and move anything that must stay on first. MQTT switches are not published yet.

## Retired — cloud install

Downloaded [Govee Cloud Integration](https://github.com/lasswellt/govee-homeassistant) **2026.9.14** into `/config/custom_components/govee/`. Not configured. Do not paste an API key. Do not use [LaggAt/hacs-govee](https://github.com/LaggAt/hacs-govee).

## Checkpoint 3 — sixteen switches exist

`[x]` Home Assistant on `.105` has **two MQTT switches per plug** (16), discovered from `h5082-mqtt.service` on the Pi (`hci1` only). States were set from each plug's advertisement, not by turning sockets. `C38D` has no pairing key, so a command for that plug is ignored and the switch stays on the reported state.

`[x]` Site solar (`/site-solar`, Now view, heading **Plugs**) shows those 16 tiles. The sim plug package and the **Sim dump plugs** history card are removed. `switch.sim_ac_plug_*` is gone.

| Plug | Left | Right |
|---|---|---|
| `switch.ihoment_h5082_2f9d_left` / `_right` | on | off |
| `switch.ihoment_h5082_3013_left` / `_right` | on | off |
| `switch.ihoment_h5082_3ec9_left` / `_right` | on | on |
| `switch.ihoment_h5082_82fb_left` / `_right` | on | off |
| `switch.ihoment_h5082_9607_left` / `_right` | off | off |
| `switch.ihoment_h5082_c061_left` / `_right` | on | on |
| `switch.ihoment_h5082_c38d_left` / `_right` | off | off |
| `switch.ihoment_h5082_cf79_left` / `_right` | on | off |

## Checkpoint 4 — normal vs dump, manual vs auto

`[x]` (repo, 2026-09-28) `config/packages/dump_control.yaml` replaces `sim_dump_control.yaml` and reads `input_select.h5082_<id>_<side>_use`; each socket also has `input_select.h5082_<id>_<side>_inverter` and its own min-on / cooldown timers. C38D (no pairing key yet) is left out. What each socket feeds and where each plug is are the HA **Where** / **Load** helpers, not repo text. Install on `.105` with `bash scripts/install_dump_control_ha.sh`.

Add one [input_select](https://www.home-assistant.io/integrations/input_select/) per socket, options `normal` and `dump`. Default **normal**. The operator sets **dump** on the 4 sockets that are the two dump plugs. Helpers stay editable under Settings → Helpers.

Rules:

- **Manual:** the Govee switch. Always. Dashboard tile and Developer Tools. Works in either assignment.
- **Auto:** `dump_control.yaml` may call `switch.turn_on` / `turn_off` only when that socket's select is `dump`. A `normal` socket is not in the shed list, the add list, or the all-off list.
- Reassigning is changing the select. No package rewrite, no entity rename.
- The hardcoded sim switch list is retired. The dump package reads the selects.
- Sim template switches and both sim packages are removed from git (2026-09-28); `install_dump_control_ha.sh` deletes any copy left in `/opt/homeassistant/packages/`.

## Checkpoint 5 — Node-RED

`[x]` `/solar/metrics` publishes `solar_plant_socket` for each of the 16 sockets (on=1, off=0). Labels are the HA **Where**, **Load**, and **Use** text. There is no power sensor on these plugs, so there is no watt sample. `/solar/computed` lists the same rows. Redeploy with `scripts/deploy-nodered-solar.sh`.

Where / Load / Use survive HA restarts only when their storage helpers have no `initial` (fixed 2026-09-28; `scripts/create_h5082_socket_labels.py` strips it). Per-box help: [site-solar/plug-names.md](site-solar/plug-names.md), [site-solar/socket-use.md](site-solar/socket-use.md), [site-solar/socket-inverter.md](site-solar/socket-inverter.md).

## Checkpoint 6 — Grafana, after the switches are real

`[x]` Grafana **Solar plant one-line** keeps the plant canvas. Under it, **Dump sockets** and **Manual sockets** tables read `solar_plant_socket`. A socket moves between those tables when its **Use** select changes. The six sim plugs are not drawn.

## Checkpoint 7 — done

`[ ]` A normal socket toggles from HA and the dump automation does not touch it.
`[ ]` A dump socket toggles from HA **and** from the dump automation.
`[ ]` Changing the select moves a socket between those two behaviors.
`[x]` Sim switches are gone (repo). On `.105`, delete leftover `switch.sim_ac_plug_*` / sim helper entities if the registry still lists them.
`[ ]` Grafana matches that split.

## Where a new session starts

Checkpoint **7**. Node-RED and Grafana already show the 16 sockets. `dump_control.yaml` switches only sockets whose Use is dump; install it on `.105`, set Use + Inverter, then test one dump socket by hand and by the automation. `C38D` has no key. `hci1` only. Do not touch `hci0`. Do not paste a Govee API key.
