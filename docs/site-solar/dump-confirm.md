# Site solar help: Dump confirm (wait / load rise)

**Where:** Site solar > Now view > **Dump confirm (wait / load rise)**.
**Logic:** `config/packages/dump_control.yaml`, automation `dump_turn_on`
(`Dump ON: add dump sockets while the charger is in float`), template sensors
`dump_bus_load_t2` / `_ku` / `_sph`.

## What this box is for

The H5082 plugs report on/off but no watts. So after HA turns a dump socket on, it
checks that the load really started by looking at the bus meter: if the load on that
bus went up enough, the socket stays on; if not (nothing plugged in, appliance
thermostat off, plug did not switch), HA turns it back off and tries the next one.

## The entities

| Row | Entity | Unit / range | What it does | Raise it | Lower it |
|---|---|---|---|---|---|
| Confirm wait | `input_number.dump_site_confirm_s` | s, 5-30, step 1 | Seconds HA waits, after the plug reports on, before reading the meter again | Slower staging, but slow meters (Sungold Modbus polls every ~5 s) have time to update | Faster staging; too short and the meter has not caught up, so good loads fail |
| Confirm min load rise | `input_number.dump_site_delta_min_w` | W, 5-500, step 5 | The bus load must rise by at least this many watts | Small loads (lamp, fan) get rejected | Meter noise may "confirm" a socket that is not drawing anything |

**Safe starting values:** 5 s and 25 W. A good rule: min load rise = about half the
watts of your smallest dump load (a 60 W lamp: 25-30 W; a 1500 W heater: 25-500 W).

## How it works in the package

For each socket `sensor.dump_next_plug` offers, `dump_turn_on`:

1. Reads the bus load **before** (`load_before`). The meter depends on the socket's
   **Inverter**: T2 = `sensor.dump_bus_load_t2` (= minus `sensor.battery_1_power`),
   KU = `sensor.dump_bus_load_ku` (= minus `sensor.battery_2_power`), Sungold =
   `sensor.dump_bus_load_sph` (= `sensor.sungold_sph302480a_load_power`).
2. Logs `turning ON (<bus> bus) ...` and calls `switch.turn_on`.
3. Waits up to 2 minutes for the H5082 to **report** on (the Pi bridge only reports
   on after the plug acknowledges over Bluetooth).
4. Waits **Confirm wait** seconds, then reads the load **after**.
5. If the T2 charger left float or solar went away meanwhile: socket off, 10 minute
   cooldown, staging stops.
6. **Confirmed** = the plug reported on **and** both readings are numbers **and**
   after - before >= **Confirm min load rise**. Confirmed: its 15 minute min-on timer
   starts and the log says `kept ON: <bus> load rose N W`. HA then tries the next
   socket (at most 14 per run).
7. **Not confirmed:** socket off, 10 minute cooldown, log says
   `turned back OFF: not confirmed ... load rose N W, needs M W`. HA moves on to the
   next socket.

Note for T2 and KU: the meter is the battery shunt. In float the MPPT can cover part
of a new load from PV, so the shunt may show less than the appliance's full watts.
If a known-good T2/KU heater keeps failing confirm, lower min load rise first.

Before 2026-09-28 both numbers went back to 5 s / 25 W at every HA restart. They now
keep your value.

## Example

Sungold socket with a 700 W heater. Load before 310 W; the plug reports on after
3 s; 5 s later Sungold AC-out reads 1015 W. Rise 705 W >= 25 W: kept on. A socket
whose heater thermostat is satisfied reads a rise of 4 W: turned back off, cooldown
10 minutes, log `not confirmed ... load rose 4 W, needs 25 W`.

## Recommended first test

1. Lamp on a dump socket (see [Socket Use](socket-use.md)); set min load rise to half
   the lamp's watts.
2. When HA adds it, the activity log should show `turning ON` then `kept ON: ... load
   rose N W`.
3. Unplug the lamp and wait for the next attempt (after the 10 minute cooldown): the
   log should say `not confirmed` and the socket goes back off.
