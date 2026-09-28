# Site solar help: Dump sockets timeline

**Where:** Site solar > **History** view > **Dump sockets timeline**.
**Logic:** History graph card (via `auto-entities`) over
`input_boolean.dump_control_enabled`, `binary_sensor.dump_charge_float`,
`binary_sensor.dump_solar_present`, `binary_sensor.dump_load_exceeds_solar`,
`binary_sensor.dump_v_rebulk_*` and `switch.ihoment_h5082_*`, last 48 hours. Card defined in
`config/dashboards/solar-plant.yaml`; the binary sensors live in `config/packages/dump_control.yaml`.

## What this box is for

A picture of the last two days: one bar per plug (on/off) lined up with the master
switch and the conditions that switch dump sockets. Use it to see patterns ("every
day at 16:30 the KU sockets drop out").

## The rows

| Row | On means |
|---|---|
| Dump load HA control (master switch) | HA may switch dump sockets |
| Dump charge float | T2 charger in float (needed to add sockets) |
| Dump solar present | T2 PV at/above Min solar (off 1 min = all dump sockets off) |
| Dump load exceeds solar | Sungold load above T2 + Sungold PV (1 min = shed one per minute) |
| Dump T2 / KU / Sungold re-bulk | That bus at/below stop volts (1 min = its dump sockets off) |
| `ihoment_H5082_<ID> Left/Right` | The socket is on |

## Settings

None. Change `hours_to_show` on the card to see more or less.

## How it works

History comes from the recorder (10 days kept by default). A socket bar that ends at
the same moment as, for example, a re-bulk bar starts plus 1 minute was turned off
by that rule; the exact reason text is in [Dump activity log](dump-activity-log.md).

## Example

The 3EC9 left bar goes off at 16:31 and `Dump KU re-bulk` turned on at 16:30: the KU
bus sagged to its stop volts. If that happens daily, raise KU stop volts a little or
move the heater to another bus.

## Recommended first test

After a sunny day with dumping, open the History view and check that each dump
socket's on-period sits inside a `Dump charge float` on-period and ends at a
condition change or when you switched it by hand.
