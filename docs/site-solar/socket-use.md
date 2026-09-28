# Site solar help: Socket Use (normal / dump)

**Where:** Site solar > Now view > **Socket Use (normal / dump)**.
**Logic:** storage helpers `input_select.h5082_<id>_<side>_use` (from
`scripts/create_h5082_socket_labels.py`), read by every template and automation in
`config/packages/dump_control.yaml`.

## What this box is for

Decides which sockets Home Assistant may switch **by itself**.

## The entities

| Row | Entity | Options | What it does |
|---|---|---|---|
| `<ID> left` / `<ID> right` (14 rows) | `input_select.h5082_<id>_<side>_use` | `normal`, `dump` | **dump:** the dump rules may turn this socket on (when there is spare solar) and off (solar gone, stop volts, battery limit, shed). **normal:** no rule ever touches it; only you (Plugs button, plug's own button). |
| `C38D left (Pi supply, never dumped)` / `C38D right (...)` | `input_select.h5082_c38d_<side>_use` | `normal`, `dump` | C38D is not in any list in the package: it is never switched by the dump rules, even set to dump. Leave it normal. |

Moving a socket from normal to dump "raises" HA's control (it may now switch it);
dump to normal removes it. Any value other than `dump` counts as normal.

**Safe start:** everything **normal**. Then one socket with a lamp set to **dump** for
the first test, then the real dump loads (the plan: 4 sockets on 2 plugs).
Only choose dump for loads that can go off at any moment without harm (resistive
heaters, water heater). Never for a fridge, freezer, pump, trailer A/C or computer.

## How it works in the package

- `sensor.dump_sockets` counts sockets with Use = dump; `sensor.dump_next_plug` and
  `sensor.dump_shed_plug` only consider dump sockets; every turn-off rule builds its
  list from sockets with Use = dump.
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

3EC9 left has a 750 W space heater and 3EC9 right a fridge. Set 3EC9 left = dump,
3EC9 right = normal. HA may run the heater on spare solar; it never touches the
fridge.

## Recommended first test

1. Master switch off. Set one lamp socket to **dump** and its Inverter correctly.
2. **Dump status > Sockets set to dump** shows 1.
3. Master switch on in float: the lamp comes on by itself (activity log: `turning ON`).
4. Set it back to **normal**: HA no longer touches it (turn it off by hand).
5. Restart HA once and check the choice is still there.
