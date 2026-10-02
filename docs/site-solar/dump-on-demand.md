# Site solar help: Dump on demand

**Where:** Site solar > Now view > **Dump on demand**.
**Logic:** `config/packages/dump_control.yaml`: `sensor.dump_ondemand_on`,
`sensor.dump_ondemand_off`, `input_boolean.dump_skip_cooldown`, scripts
`script.dump_force_on` (Turn next dump ON) and `script.dump_force_off` (Turn dumps OFF).
The hold itself is still [Dump manual hold](dump-hold.md).

## What this box is for

Turn dump sockets on or off when you want, without waiting for the charger to sit in
float for a minute. One press of **Turn next dump ON** switches the next eligible
socket. **Turn dumps OFF** switches off every dump socket that is currently on and not
on hold. **Skip cooldown once** lets that next on or off ignore the 10 minute cooldown,
then turns itself off.

## The entities

| Row | Entity | What it does |
|---|---|---|
| Next socket Turn next dump ON would switch | `sensor.dump_ondemand_on` | The switch entity the ON button would command, or `none`. Same socket order as automatic adding (2F9D left … CF79 right). It does **not** require float, solar, SoC, start volts, battery ok or AC headroom. It does require Use = dump, Inverter not House, the socket off, not on [manual hold](dump-hold.md), cooldown idle (unless skip cooldown is on), and not a Sungold socket while [the voltage guard](dump-sph-vguard.md) is active. |
| Sockets Turn dumps OFF would switch | `sensor.dump_ondemand_off` | How many sockets the OFF button would command. Attribute `sockets` lists them: Use = dump, Inverter not House, currently on, not on hold. |
| Skip cooldown once | `input_boolean.dump_skip_cooldown` | **On:** the next automatic add (`sensor.dump_next_plug` / `dump_turn_on`) and Turn next dump ON ignore cooldown, and Turn dumps OFF does not start a cooldown. The switch turns **off** after that next successful on, or after the first socket that reports off from Turn dumps OFF. A brand-new helper starts **off**. It does not turn itself off if the plug never reports the new state. |

The two buttons run `script.dump_force_on` and `script.dump_force_off`. They ask for
confirmation. They do **not** fire `dump_control_switching`. When the plug reports the
new state, `Dump HOLD start` treats it as a hand switch and arms the manual hold for
**Dump manual hold** minutes. If that number is **0**, no hold starts and the dump
rules may switch the socket again at once.

Below the buttons, **On demand by name (live)** shows the same sockets by Load and Where.

### Will a forced on or off stick?

A forced change arms the same hold as a Plugs tap.

- **Hold minutes above 0:** dump control will not turn that socket **on** until the hold
  ends. It turns a held socket **off** only when **Hold also blocks turn-offs** is off
  (solar gone, stop volts, battery limit, sheds, and the Sungold voltage guard still
  win). With that toggle **on**, those rules leave the held socket alone until the hold
  ends. `Dump HOLD end` can still turn it off then, if a rule would want it off.
- **Hold minutes 0:** nothing is armed. An automatic rule can undo the press at its
  next chance.
- A socket **already on hold** is left alone by both buttons. Clear that hold first, or
  use its Plugs button (a hand switch restarts the hold).
- The buttons run even when the master switch is off. Automatic rules still need the
  master switch.

Skip cooldown does not skip float, solar, SoC or the voltage guard for **automatic**
adding. It only skips the 10 minute cooldown. The ON button is the control that does
not wait for float.

## How it works in the package

- `sensor.dump_ondemand_on` is what the ON script switches. The script waits up to 2
  minutes for the plug to report on, then cancels that socket's cooldown timer. If skip
  cooldown was on, it turns the switch off. If the plug never reports on, skip cooldown
  stays as it was and no hold starts.
- `script.dump_force_off` turns off every socket in `sensor.dump_ondemand_off`'s
  `sockets` attribute, waits up to 2 minutes each, cancels min-on, and starts the 10
  minute cooldown unless skip cooldown was on (then it cancels cooldown instead). The
  hold arms when the plug reports off.
- Automatic `dump_turn_on` turns skip cooldown off when it actually asks a socket to
  turn on, so only that one add ignores cooldown. Later sockets in the same run wait
  out their own cooldowns.
- House sockets and normal sockets are never in these lists.

## Example

Dump manual hold = 60 min, Hold also blocks turn-offs = on, Skip cooldown once = off.
`<ID> left` is a dump socket, off, cooldown active (8 minutes left). `sensor.dump_ondemand_on`
names the next idle dump socket, not `<ID> left`. You turn **Skip cooldown once** on:
the sensor now names `<ID> left`. You press **Turn next dump ON**. The plug reports on,
the activity log shows the press and then `switched ON by hand ... Hold 60 min`, the
button label shows `hold to HH:MM`, and Skip cooldown once is off again. At sunset the
solar-gone rule turns off every other dump socket and leaves this one on until the hold
ends.

## Recommended first test

1. Set **Dump manual hold** to 5 min and **Hold also blocks turn-offs** on. Master switch
   may be on or off. Pick one dump socket that is off.
2. Press **Turn next dump ON**. After the plug reports on, **Holds (per socket)** shows
   that socket active, and the Dump activity log has a `by hand` line. It must **not**
   show `turning ON (… bus): charger in float` for this press.
3. Turn **Skip cooldown once** on and press **Turn dumps OFF**. The socket goes off, its
   cooldown timer stays **idle**, Skip cooldown once turns off, and a new hold starts.
4. With Skip cooldown once left off, press **Turn dumps OFF** on a socket you turned on
   by hand after clearing its hold: its cooldown shows **active**.
