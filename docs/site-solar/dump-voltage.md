# Site solar help: Dump voltage (start / stop)

**Where:** Site solar (`/site-solar`) > Now view > **Dump voltage (start / stop)**.
**Logic:** `config/packages/dump_control.yaml` (binary sensors `dump_v_float_*`,
`dump_v_rebulk_*`, sensor `dump_next_plug`, automations `dump_turn_off_rebulk_*`).

## What this box is for

Each battery bus (T2, KU, Sungold cart) has two voltages:

- **Start volts (float):** the bus must be at or above this before HA may put a
  dump socket on that bus. It means "the battery is full and the charger is only
  holding it there".
- **Stop volts (re-bulk):** if the bus falls to or below this for 1 minute, HA turns
  off every dump socket on that bus. It means "the dump load is now pulling the
  battery down".

Between the two (below start, above stop) HA does not add more sockets on that bus,
and it does not turn the ones already on off.

## The entities

| Row | Entity | Unit / range | What it does | Raise it | Lower it |
|---|---|---|---|---|---|
| T2 start volts (float) | `input_number.dump_float_t2_v` | V, 26.0-29.5, step 0.05 | `binary_sensor.dump_v_float_t2` is on while `sensor.battery_1_voltage` >= this | Dumping on T2 starts later / less often (the bus must be higher) | Starts sooner; too low and it can start before the pack is really full |
| T2 stop volts (re-bulk) | `input_number.dump_rebulk_t2_v` | V, 25.5-29.0, step 0.05 | `binary_sensor.dump_v_rebulk_t2` is on while `sensor.battery_1_voltage` <= this; on for 1 min turns T2 dump sockets off | Dumps shut off sooner, at a higher voltage (safer for the pack) | Dumps stay on longer while the voltage sags |
| KU start volts (float) | `input_number.dump_float_ku_v` | V, 26.0-29.5 | same, on `sensor.battery_2_voltage` | as T2 | as T2 |
| KU stop volts (re-bulk) | `input_number.dump_rebulk_ku_v` | V, 25.5-29.0 | same, on `sensor.battery_2_voltage` | as T2 | as T2 |
| Sungold start volts (float) | `input_number.dump_float_sph_v` | V, 26.0-29.5 | same, on `sensor.sungold_sph302480a_battery_voltage` | as T2 | as T2 |
| Sungold stop volts (re-bulk) | `input_number.dump_rebulk_sph_v` | V, 25.5-29.0 | same, on `sensor.sungold_sph302480a_battery_voltage` | as T2 | as T2 |

**Safe starting values:** 27.0 V start and 26.8 V stop on every bus. 27.0 V is the
Victron LiFePO4 24 V float default; 26.8 V is Victron's re-bulk offset (float minus
0.1 V per 12 V, doubled on 24 V). Better: set start to the float voltage you set in
VictronConnect for that charger, and stop 0.2 V lower. The **Load recommended
starting values** button in **Dump master switch** writes 27.0 / 26.8.

**Rule:** keep stop at least 0.2 V **below** start. If stop is at or above start, a
bus can be "at start" and "at stop" at the same time: `sensor.dump_next_plug` never
picks it and the stop rule turns it off again.

## How it works in the package

1. `sensor.dump_next_plug` only offers a socket whose **Inverter** bus has
   `dump_v_float_<bus>` **on** and `dump_v_rebulk_<bus>` **off** (plus the other
   gates in [Dump status](dump-status.md)). There is no extra wait on the voltage
   itself: the moment the bus is at start volts it counts.
2. The site-wide start still needs the **T2** MPPT in float for 1 minute
   (`binary_sensor.dump_charge_float`), even for KU and Sungold sockets.
3. `Dump OFF <bus> sockets: <bus> bus at stop volts (re-bulk)` (ids
   `dump_turn_off_rebulk_t2` / `_ku` / `_sph`) fires when `dump_v_rebulk_<bus>` has
   been on for 1 minute and the master switch is on. It turns off every dump socket
   whose Inverter is that bus and that is not already off (even during min-on),
   cancels its min-on and starts its 10 minute cooldown. Other buses are untouched.
4. If a voltage sensor is unavailable, both binary sensors for that bus are off:
   HA adds nothing on that bus, and the stop rule does not fire (the battery rule in
   [Battery discharge limits](dump-battery-limits.md) still can).

Before 2026-09-28 these six numbers had `initial:` in the package and went back to
27.0 / 26.8 at every HA restart. They now keep your value.

## Example

T2 charger float is set to 27.0 V. At 13:00 the T2 MPPT is in float and the shunt
reads 27.02 V, so `dump_v_float_t2` turns on and HA adds the first dump socket whose
Inverter is T2. The heater draws more than the spare PV, the bus sags, and at 26.78 V
`dump_v_rebulk_t2` turns on. One minute later every T2 dump socket turns off and the
activity log says `Dump control turned OFF by "Dump OFF T2 sockets: T2 bus at stop
volts (re-bulk)": T2 bus 26.78 V at or below stop volts 26.8 V for 1 min`.

If that happens several times a day, raise T2 stop volts a little (26.85) so it
stops earlier, or accept it: the 10 minute cooldown keeps it from flapping.

## Recommended first test

1. One socket with a lamp: **Use** = dump, **Inverter** = the bus it is on (say T2).
2. Sunny afternoon, T2 charger in float, master switch on. Watch **Dump status**:
   `T2 at/above start volts` should be on and the lamp should come on.
3. Note the T2 voltage, then set **T2 stop volts** 0.05 V **above** it. Within about
   a minute the lamp turns off and **Dump activity log** shows the stop-volts line.
4. Put **T2 stop volts** back (26.8 V). The lamp stays off for its 10 minute
   cooldown (see [Dump timers](dump-timers.md)), then may come back on.
