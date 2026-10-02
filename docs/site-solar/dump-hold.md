# Site solar help: Dump manual hold

**Where:** Site solar > Now view > **Dump manual hold**.
**Logic:** `config/packages/dump_control.yaml`: `input_number.dump_manual_hold_min`,
`input_boolean.dump_hold_blocks_turn_off`, `timer.h5082_<id>_<side>_hold` (one per
socket, 16), `sensor.dump_control_switching`, automations `Dump HOLD start: dump socket
switched by hand` (`dump_hold_start`) and `Dump HOLD end: automatic control resumes`
(`dump_hold_end`), script `script.dump_clear_holds`.

## What this box is for

When you switch a dump socket yourself, the dump rules should not undo it a minute
later. A hand switch puts that socket **on hold** for a while; when the hold ends,
automatic control resumes.

A hand switch is any on/off change of a dump socket that dump control did not ask for:
a **Plugs** button tap, the plug's **own button**, **Turn next dump ON**, **Turn dumps
OFF**, the socket's switch in any other card or app, another automation. The on-demand
buttons do not announce themselves as dump control, so the hold starts when the plug
reports the new state (see [Dump on demand](dump-on-demand.md)). Only dump sockets get
a hold (Use = dump and Inverter not House); a normal or House socket is never switched
by dump control anyway.

## The entities

| Row | Entity | Range | What it does |
|---|---|---|---|
| Hold after a hand switch (0 = off) | `input_number.dump_manual_hold_min` | 0-720 min, step 5 | How long a hand-switched dump socket is left alone. **0 = no hold** (the old behaviour: the dump rules may switch it again at once). A brand-new helper starts at 0. |
| Hold also blocks turn-offs | `input_boolean.dump_hold_blocks_turn_off` | on / off | **on:** a held socket is also skipped by every dump turn-off rule: solar gone, stop volts (re-bulk), battery discharge limit, and the two shed rules. **off:** those rules still turn a held socket off. A brand-new helper starts off. |
| Clear all holds | `script.dump_clear_holds` | button | Cancels every hold at once; the dump rules may switch those sockets again right away. |
| Holds (per socket), one row per socket | `timer.h5082_<id>_<side>_hold` | idle / active | **active** with the time left = on hold. Tap a row, then **Cancel**, to end that one hold early. Named live from the socket's Load and its plug's Where. `restore: true`: a hold keeps running across an HA restart. |

Recommended starting values (also loaded by **Dump master switch > Load recommended
starting values**): **60 min**, **Hold also blocks turn-offs = on**.

### Your choice: should a hold also block the safety turn-offs?

A hold **always** stops dump control turning a held socket **on**. Whether it also stops
dump control turning it **off** is up to you:

- **on (recommended default, "leave my socket alone"):** you switched it, so HA does not
  touch it until the hold ends, not even at sunset, at stop volts or when a battery
  discharges past its limit. A heater you turned on by hand keeps running for up to the
  hold length. When the hold ends, `Dump HOLD end` turns it off if dump control would
  want it off right then (see below). Keep the hold short if you choose this.
- **off (battery first):** solar gone, stop volts, the battery limits and the sheds still
  turn a held socket off; the hold then only keeps HA from turning it back on until the
  hold ends.

Either way the master switch still wins: with **Dump load HA control** off, no dump rule
switches anything.

## How it works in the package

- **Telling dump control from a hand switch.** The H5082 switches are MQTT switches with
  a state topic: every state change arrives from the Pi 4 bridge with a fresh context (no
  user, no parent automation), whether you tapped the button, pressed the plug, or a
  dump rule switched it. So context cannot tell them apart. Instead every dump rule fires
  the event `dump_control_switching` (socket, on/off) right before it switches a socket.
  `sensor.dump_control_switching` keeps the last request per socket (attribute
  `intents`). `Dump HOLD start` runs on every on/off change of the 16 sockets: if the new
  state matches a dump control request from the last 3 minutes, it is dump control (the
  request is marked used); otherwise it is a hand switch.
- **Hold start.** For a hand switch on a dump socket (Use = dump, Inverter not House)
  with hold minutes > 0, `timer.h5082_<id>_<side>_hold` starts for that many minutes and
  the Dump activity log says `<name>: switched ON by hand ... Hold 60 min: the dump rules
  leave it alone until 16:45.` Another hand switch restarts the hold. It runs even while
  the master switch is off, so turning the master switch on later does not undo you.
- **While held.** `sensor.dump_next_plug` and the recheck in `dump_turn_on` skip the
  socket (always). `sensor.dump_shed_plug` and the turn-off lists (solar gone, the
  three stop-volts rules, the three battery rules, and the Sungold voltage guard)
  skip it only while **Hold also blocks turn-offs** is on. `sensor.dump_sockets` still counts it (it is still set to
  dump); its attribute `held` lists the held sockets.
- **Hold end.** When the timer goes back to idle (time up, Cancel, or Clear all holds),
  `Dump HOLD end` logs `hold ended (time up)` or `hold ended (cleared)`. The turn-off
  rules only fire when their condition starts, so if the master switch is on and the
  socket is still on while dump control would want it off right now (solar gone, T2
  charger left absorption/float, Sungold load above solar, its bus at stop volts, its
  battery past the limit, or the Sungold voltage guard while this socket's Inverter is
  Sungold), it is turned off with a 10 minute cooldown and the log says why. Turning on
  resumes by itself: `sensor.dump_next_plug` offers the socket again.
- The Plugs button label shows `hold to HH:MM` while a socket is held, and
  **Dump status > Dump sockets by name** adds `on hold to HH:MM`.

**Limits of the detection.**

- A change dump control asked for is recognised only within 3 minutes of the request
  (the bridge normally confirms in seconds; a turn-on gives up after 2 minutes).
- Anything else that changes a dump socket counts as a hand switch and starts a hold:
  a plug that loses power and comes back off, a plug that was switched while the bridge
  could not hear it and reports its real state later, another automation.
  Changes to or from unavailable (bridge offline) never start a hold.
- If you switch a socket by hand to the same state dump control asked for, within
  those 3 minutes and before the plug confirmed dump control's request, it counts as
  dump control.
- `sensor.dump_control_switching` is a trigger-based template sensor; after an HA
  restart it may start empty, which only means the next change is judged a hand switch
  if it was not requested after the restart.

## Example

Hold = 60 min, Hold also blocks turn-offs = on. At 15:40 you tap the dump socket
`Heater (<ID> left) at Bedroom` on to warm the room. The log says it was switched ON by
hand, hold until 16:40, and the button label shows `hold to 16:40`. At 16:10 the sun goes
behind clouds and `Dump OFF all: solar gone` turns off every other dump socket but not
this one. At 16:40 the hold ends; solar is still gone, so `Dump HOLD end` turns it off
(`the hold ended while solar gone`) and starts its cooldown.

With Hold also blocks turn-offs = off, the same heater would have been turned off at
16:11 by the solar-gone rule, and HA would not turn it back on before 16:40.

## Recommended first test

1. Set **Hold after a hand switch** to 5 min. Pick a dump socket with a lamp that HA has
   turned on.
2. Tap its Plugs button off. The Dump activity log shows `switched OFF by hand ... Hold 5
   min`, its row under **Holds (per socket)** is active, and the button label shows
   `hold to HH:MM`. **Dump status > Next socket HA would add** does not name it.
3. Press the plug's own button on and off: each change restarts the hold (log line each
   time).
4. Press **Clear all holds**: the log shows `hold ended (cleared)`, and at the next chance
   HA may turn the socket on again (log line naming the dump rule, no new hold).
