# Site solar help: Dump timers (min-on / cooldown)

**Where:** Site solar > Now view > **Dump timers (min-on / cooldown)**.
**Logic:** `config/packages/dump_control.yaml`, `timer:` block
(`timer.h5082_<id>_<side>_min_on`, `timer.h5082_<id>_<side>_cooldown`), sensor
`dump_next_plug`, every dump automation.

## What this box is for

Two timers per dump-capable socket (16 sockets: all 8 plugs). They show
why a socket is being skipped right now.

## The entities

| Timer | Length | Started when | Effect |
|---|---|---|---|
| `timer.h5082_<id>_<side>_cooldown` ("<ID> <side> dump cooldown (10 min)") | 10 min | HA turns that dump socket off for any reason: failed confirm, charger left float during confirm, solar gone, stop volts, battery limit, shed | While **active**, `sensor.dump_next_plug` skips that socket, so HA cannot turn it on again. Stops rapid on/off cycling. |
| `timer.h5082_<id>_<side>_min_on` ("<ID> <side> dump min-on (15 min, display only)") | 15 min | HA confirmed the socket's load | **Display only.** No rule waits for it; every turn-off rule cancels it and turns the socket off anyway. |

Both have `restore: true`: an active timer keeps running across an HA restart.

There is nothing to raise or lower in the dashboard: the lengths are in the package
(`duration: "00:10:00"` / `"00:15:00"`). To change them, edit
`config/packages/dump_control.yaml` in the repo and rerun
`scripts/install_dump_control_ha.sh`.

## How it works in the package

- Only HA's own turn-offs start a cooldown. If you switch a dump socket off by hand,
  no cooldown starts and HA may turn it back on at the next chance.
- A socket in cooldown shows **active** with the time left; **idle** means HA may use
  it again (if every other gate is open).

## Example

HA tries socket `<ID> right`, the confirm fails (nothing is drawing power there).
`<ID> right dump cooldown` shows active 9:58. HA moves on to the next dump socket in the
stage order. For the next 10 minutes `<ID> right` is never offered; after that it may be
tried again.

## Recommended first test

1. Let HA turn a test lamp socket on and confirm it: its min-on timer becomes
   active.
2. Trigger any turn-off (for example the stop-volts test in
   [Dump voltage](dump-voltage.md)). The min-on timer goes idle and the cooldown
   becomes active with about 10:00 left.
3. Confirm **Dump status > Next socket HA would add** does not show that socket until
   the cooldown is idle.
