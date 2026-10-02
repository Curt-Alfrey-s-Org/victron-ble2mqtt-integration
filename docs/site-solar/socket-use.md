# Site solar help: Socket Use (normal / dump / charge)

**Where:** Site solar > Now view > **Socket Use (normal / dump / charge)**.
**Logic:** storage helpers `input_select.h5082_<id>_<side>_use` (from
`scripts/create_h5082_socket_labels.py`), read by every template and automation in
`config/packages/dump_control.yaml`.

## What this box is for

Decides which sockets Home Assistant may switch **by itself**.

## The entities

| Row | Entity | Options | What it does |
|---|---|---|---|
| live name (16 rows) | `input_select.h5082_<id>_<side>_use` | `normal`, `dump`, `Sungold charge` | **dump:** the dump rules may turn this socket on (when there is spare solar) and off (solar gone, stop volts, battery limit, shed), unless its [Inverter](socket-inverter.md) is **House**. **Sungold charge:** the [Sungold charge](sph-charge.md) rule may turn this socket on and off so the pack can charge from the bank named by Inverter (T2 or KU), for a low pack or for surplus watts while Sungold is under full volts. It is not a dump. **normal:** no rule ever touches it; only you (Plugs button, plug's own button). |

Each row's name is live: the socket's **Load** and its plug's **Where** from
[Plug names](plug-names.md), with the plug id and side in brackets, for example
`Heater (<ID> left) at Bedroom`. A blank Load shows just `<ID> left`. Nothing about
what is plugged in is fixed in the repo (auto-entities template in
`config/dashboards/solar-plant.yaml`).

Moving a socket from normal to dump "raises" HA's control (it may now switch it);
dump to normal removes it. **Sungold charge** is a third choice, not a dump: dump
add, shed, off, on-demand and the voltage-guard shed ignore it. Any other value
still counts as normal.

**Safe start:** everything **normal**. Then one socket with a lamp set to **dump** for
the first test, then the real dump loads (the plan: 4 sockets on 2 plugs).
Only choose dump for a load that can lose power at any moment without harm (for
example a resistive heater). Never for something that must stay on (for example a
fridge, freezer, pump or computer). Check the socket's Load first.

## How it works in the package

- A socket is a dump socket when Use = dump **and** its Inverter is not **House**
  (House = grid-powered house plug). Use = `Sungold charge` is never a dump socket.
  The option is added on existing helpers by `scripts/create_h5082_socket_labels.py`
  (it appends the option and does not change the value you already picked). A
  brand-new select still starts on **normal** (the first option). `sensor.dump_sockets` counts those;
  `sensor.dump_next_plug` and `sensor.dump_shed_plug` only consider those; every
  turn-off rule builds its list from those. A House socket set to dump is still never
  switched (Dump sockets by name shows it as "House (grid power): never switched").
- A dump socket you switch by hand is put on [manual hold](dump-hold.md) for **Dump
  manual hold** minutes: the dump rules do not turn it on during the hold, and turn it
  off only if **Hold also blocks turn-offs** is off.
- Stage order is 2F9D left, 2F9D right, 3013 left, ... CF79 right; sheds go in the
  reverse order.
- Changing a socket from **dump to normal** while it is on: HA stops touching it and
  it stays on until you turn it off.
- Changing a socket from **normal to dump** while it is on: it stays on; the next
  time a turn-off rule fires, it is included.
- Each socket also needs the right [Socket inverter](socket-inverter.md).
- Before this fix, a restart put every Use back to **normal** (the helpers were
  created with `initial: normal`), silently disabling your dump sockets. After the
  one-time `create_h5082_socket_labels.py` run the choice survives restarts.

## Example

Plug `<ID>`: you typed Left load = `Space heater` and Right load = `Fridge`. The rows
read `Space heater (<ID> left)` and `Fridge (<ID> right)`. Set the left one to dump and
the right one to normal. HA may run the heater on spare solar; it never touches the
fridge. When you later swap what is plugged in, change the Load text and review Use.

## Recommended first test

1. Master switch off. Set one lamp socket to **dump** and its Inverter correctly.
2. **Dump status > Sockets set to dump** shows 1.
3. Master switch on in float: the lamp comes on by itself (activity log: `turning ON`).
4. Set it back to **normal**: HA no longer touches it (turn it off by hand).
5. Restart HA once and check the choice is still there.
