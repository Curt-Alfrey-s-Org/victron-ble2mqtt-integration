# Site solar help: Dump master switch

**Where:** Site solar > Now view > **Dump master switch**.
**Logic:** `config/packages/dump_control.yaml`: every dump automation's first
condition is `input_boolean.dump_control_enabled` = on; `script.dump_load_recommended_defaults`.

## What this box is for

The one switch that allows Home Assistant to turn dump sockets on and off by itself,
plus a button that puts the dump numbers back to safe starting values.

## The entities

| Row | Entity | What it does |
|---|---|---|
| Dump load HA control (master switch) | `input_boolean.dump_control_enabled` | **On:** the dump rules run (add sockets in float, turn off on solar gone, stop volts, battery limit, shed). **Off:** no rule switches any socket. |
| Load recommended starting values | button, runs `script.dump_load_recommended_defaults` (asks for confirmation) | Writes: start volts 27.0 V and stop volts 26.8 V on every bus, AC limits 2000 W, battery discharge limits T2 0 / KU 0 / Sungold 50 W, min solar 50 W, min SoC 95 %, confirm wait 5 s, min load rise 25 W, manual hold 60 min, and turns **Ignore SoC** and **Hold also blocks turn-offs** on. It does **not** touch the master switch, the alert service, any socket Use / Inverter / label, or any plug. |

## How it works in the package

- Turning the master switch **off** does not turn anything off. Sockets that are on
  stay on until you switch them off (Plugs box) or you turn the master switch back on
  and a rule fires. The add loop in `dump_turn_on` checks the switch before each new
  socket, so it stops adding within a few seconds.
- The 10-minute overdraw alert (`dump_notify_load_exceeds_solar`) is the one rule that
  runs with the master switch off.
- The switch has no `initial:`: it keeps its state across HA restarts. On a brand-new
  install it starts **off**.
- The defaults button is manual only. Nothing in the repo runs it on start-up, on a
  timer or from another automation; it shows in the logbook as "Dump control loaded
  the recommended starting values".

## Example

You are working on a heater on a dump socket: turn the master switch off, then turn
the socket off in **Plugs**. HA will not turn it back on until you turn the master
switch on again.

## Recommended first test

1. Master switch **off**. All sockets' **Use** = normal except one lamp socket set to
   dump, with its **Inverter** set (see [Socket Use](socket-use.md),
   [Socket inverter](socket-inverter.md)).
2. On a fresh install press **Load recommended starting values** once and read back
   the numbers in the boxes below.
3. On a sunny float afternoon turn the master switch **on**. Within a few minutes the
   lamp comes on and **Dump activity log** shows `turning ON` and `kept ON`.
4. Turn the master switch **off**: the lamp stays on (expected). Turn it off by hand.
