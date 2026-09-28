# Site solar help: Socket inverter (bus)

**Where:** Site solar > Now view > **Socket inverter (bus)**.
**Logic:** YAML helpers `input_select.h5082_<id>_<side>_inverter` in
`config/packages/dump_control.yaml`, read by `sensor.dump_next_plug`, `dump_turn_on`,
`dump_turn_off_rebulk_*` and `dump_turn_off_batt_*`.

## What this box is for

Tells HA which inverter / battery bus each socket's power comes from, so it watches
the right battery.

## The entities

| Row | Entity | Options | What it does |
|---|---|---|---|
| live name (14 rows, not C38D) | `input_select.h5082_<id>_<side>_inverter` | `Sungold`, `T2`, `KU` | Picks the bus whose start/stop volts, battery discharge limit and AC limit gate this socket, and whose meter confirms its load. |

What each choice watches:

| Choice | Voltage | Battery | AC limit room | Confirm meter |
|---|---|---|---|---|
| T2 | `sensor.battery_1_voltage` | `sensor.battery_1_power` | T2 limit - T2 battery discharge | minus `sensor.battery_1_power` |
| KU | `sensor.battery_2_voltage` | `sensor.battery_2_power` | KU limit - KU battery discharge | minus `sensor.battery_2_power` |
| Sungold | `sensor.sungold_sph302480a_battery_voltage` | Sungold charging power (or current x voltage) | Sungold limit - Sungold AC-out | `sensor.sungold_sph302480a_load_power` |

Each row's name is live: the socket's **Load** and its plug's **Where** from
[Plug names](plug-names.md), with the plug id and side in brackets (`Heater (<ID> left)
at Bedroom`), or just `<ID> left` when Load is blank. No inverter or load is fixed in
the repo: a new select starts on the first option and you pick the real one.

No raise / lower: pick where the socket is really wired.

**Safe start:** set every dump socket to its real inverter before turning the master
switch on. A brand-new select starts on **Sungold** (the first option).

## How it works in the package

- `sensor.dump_next_plug` offers a socket only if **its** bus is at/above start volts,
  not at/below stop volts, battery ok and under its AC limit.
- `dump_turn_on` reads **its** bus meter before and after to confirm the load.
- `Dump OFF <bus> sockets: ...` rules turn off only sockets whose inverter is that bus.
- It only matters for sockets whose Use is dump.
- A wrong choice makes HA watch the wrong battery: a heater really on KU but set to T2
  would stay on while the KU battery drains, as long as T2 looks fine.
- These selects never had `initial:`; they already kept your choice over restarts.

## Example

Socket `<ID> left` is plugged into an outlet fed by the KU inverter: set it to **KU**.
When the KU battery starts discharging for a minute, that socket turns off even though
T2 and Sungold are fine. If you later move the plug to a Sungold outlet, change this
row (and its Where) to match.

## Recommended first test

1. Set your lamp dump socket's inverter correctly and let HA turn it on.
2. In **Dump activity log** the `turning ON (<bus> bus)` line must name the bus you
   picked, with that bus's voltage.
3. Run the stop-volts test from [Dump voltage](dump-voltage.md) on **that** bus: the
   lamp turns off. The same test on another bus must not touch it.
