# Site solar help: Plug names (Where / Load)

**Where:** Site solar > Now view > **Plug names (Where / Load)** (one card per plug).
**Logic:** storage helpers created by `scripts/create_h5082_socket_labels.py`; read
by the Plugs buttons (`config/dashboards/solar-plant.yaml`), Node-RED `/solar/metrics` and
Grafana. The dump rules in `config/packages/dump_control.yaml` never
read them.

## What this box is for

Your own labels for what is plugged into each socket and where each plug is, so a
socket shows the name you typed instead of just its plug id and side (`<ID> left`).
The repo never hard-codes loads or locations: plugs move and loads change, so you set
and change them here in HA.

## The entities (per plug)

| Row | Entity | Type | What it does |
|---|---|---|---|
| Where | `input_text.h5082_<id>_location` | text, 0-64 characters | Room or spot of the plug. The id (2F9D, 3013, ...) is printed on the plug and stays with it when you move it: change Where when you move the plug. |
| Heard by | `sensor.h5082_<id>_heard_by` | read-only | Which radio hears the plug best (pi5, ha-105, pi4, with dBm), from `config/packages/h5082_heard_by.yaml`. |
| Left / Right | `switch.ihoment_h5082_<id>_left` / `switch.ihoment_h5082_<id>_right` | switch | The socket itself (same as the Plugs button). |
| Left load / Right load | `input_text.h5082_<id>_left_load` / `input_text.h5082_<id>_right_load` | text, 0-64 characters | What is plugged into that side. Change it when you plug something else in. |

No raise / lower: type text. Blank is fine (the button then shows the id).

**Current names (live)** at the top of the box is a read-only table of every plug's
Where, Left load and Right load as they are right now (`_not set_` when blank). The
same live names are used by the Plugs buttons, the Socket Use and Socket inverter rows,
**Dump status > Dump sockets by name** and the **Dump control** logbook lines.

## Why they used to reset, and why they stay now

The first version of `create_h5082_socket_labels.py` created every Where / Load helper
with `initial: ""` (and every Use select with `initial: normal`). For helpers made
through the UI/API, Home Assistant stores that `initial` in
`/opt/homeassistant/.storage/input_text` and puts it back at **every restart**,
ignoring what you typed (HA core `input_text/__init__.py`: the last value is only
restored when no initial is set). Today's installs restarted HA several times, so the
labels went blank each time.

The script now creates helpers without `initial` and, when rerun, removes `initial`
from the existing H5082 helpers without changing their names or values. After that
one run (see the host steps in `NEXT_STEPS.md`), labels survive restarts, package
reloads, repo pulls, bridge restarts and reruns of the install scripts. Back them up
any time with `python3 scripts/site_solar_settings.py export`.

## Example

Plug `<ID>` sits in the bathroom with a water heater on the left and nothing on the
right: type Where `Bathroom`, Left load `Water heater`, Right load blank. The Plugs
button now reads `Water heater` / `Bathroom · dump · pi5`, the Use / Inverter rows read
`Water heater (<ID> left) at Bathroom` and `<ID> right at Bathroom`, and the next
Dump control logbook line for that socket starts with the same name. Move the plug to
the shop later: change Where to `Shop` and everything follows.

## Recommended first test

1. Type a Where and a Load on one plug.
2. Restart HA (Settings > System > Restart, or `docker restart homeassistant`).
3. After it is back, the text is still there. **Dump settings change log** shows your
   change with your name.
