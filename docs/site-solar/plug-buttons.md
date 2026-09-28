# Site solar help: Plugs (socket buttons)

**Where:** Site solar > Now view > **Plugs**.
**Logic:** dashboard seed `config/dashboards/solar-plant.yaml` (button-card template
`h5082_socket`, needs HACS `button-card` and `auto-entities`); switches from the Pi 4
bridge `govee_h5082` (`h5082-mqtt.service`).

## What this box is for

One button per H5082 socket (8 plugs x 2 sides = 16), for switching by hand and for
seeing at a glance which sockets are dump sockets.

## The entities

| Part | Source | Meaning |
|---|---|---|
| Button | `switch.ihoment_h5082_<id>_<side>` | Tap = toggle, hold = details. Green plug = on, grey = off. |
| Big text | `input_text.h5082_<id>_<side>_load` | The load you typed in [Plug names](plug-names.md); if blank, the id and side (`2F9D LEFT`). |
| Small text | `input_text.h5082_<id>_location`, `input_select.h5082_<id>_<side>_use`, `sensor.h5082_<id>_heard_by` | Where you typed for that plug (else the plug id) · normal or dump · the radio that hears the plug best (pi5, ha-105, pi4). |
| Gold border | `input_select.h5082_<id>_<side>_use` | Use = dump |

Nothing to raise or lower here.

## How it works

- A tap sends the command over MQTT to the Pi 4 bridge, which switches the plug over
  Bluetooth. The button only changes colour after the plug confirms (can take a few
  seconds on a cold link). It shows unavailable when the bridge is offline.
- A **normal** socket is never switched by HA's dump rules; the button is the only
  control (plus the plug's own button).
- A **dump** socket you switch by hand can still be switched by the dump rules
  afterwards: a rule that turns dump sockets off (solar gone, stop volts, battery
  limit, shed) includes it; the add rule only picks sockets that are off. Switching it
  off by hand does not start a cooldown.
- Nothing about what is plugged in is fixed in the repo. The names are read live from the
  Where / Load helpers every time they change, so when you move a plug or plug in
  something else, change Where / Load in [Plug names](plug-names.md) and the button follows.
- Before you switch a socket by hand, check its Load: if what is plugged in must stay on,
  leave it on (and keep its Use normal).

## Example

You typed Where = `Bedroom` for plug `<ID>` and Left load = `Heater`, and set that
socket's Use to dump. Its button shows `Heater` / `Bedroom · dump · pi5` with a gold
border. With both fields blank the same button shows `<ID> LEFT` / `<ID> · dump · pi5`. You tap it off at 15:00; at the next chance HA may turn it back on (it is a
dump socket and no cooldown started). To keep it off, set its Use to normal or turn
the master switch off.

## Recommended first test

1. Tap a normal socket with a lamp: it toggles within a few seconds.
2. Check **Dump activity log**: the entry names you (by hand), not an automation.
3. Hold the button: the details dialog opens with its history.
