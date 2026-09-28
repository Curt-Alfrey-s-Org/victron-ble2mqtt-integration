# Site solar help: Dump activity log

**Where:** Site solar > Now view > **Dump activity log**.
**Logic:** Logbook card (via `auto-entities`) over `switch.ihoment_h5082_*`,
`automation.dump_*`, `script.dump_*` and `input_boolean.dump_control_enabled`, last
48 hours. The reasons come from `logbook.log` steps in every automation in
`config/packages/dump_control.yaml` (the package also loads the `logbook`
integration).

## What this box is for

Watch **when** and **why** a plug was switched, and whether HA or a person did it.

## What the lines mean

| Line (examples) | Meaning |
|---|---|
| `<switch name> turned on triggered by action switch.turn_on triggered by automation Dump ON: add dump sockets while the charger is in float triggered by state of sensor.dump_next_plug` | HA switched it; the automation name is the rule. |
| `Dump control Heater (<ID> left) at Bedroom: turning ON (T2 bus): charger in float, T2 PV 640 W, bus 27.03 V >= start 27.0 V, T2 load before -35 W.` | Why HA is adding this socket. |
| `Dump control Heater (<ID> left) at Bedroom: kept ON: T2 load rose 712 W (needs 25 W).` | The load confirmed; the socket stays on. |
| `Dump control <ID> right: turned back OFF: not confirmed. Plug reported on; Sungold load rose 3 W, needs 25 W. Cooldown 10 min.` | Nothing drew power; 10 minute cooldown. |
| `Dump control <name>: turned OFF by "Dump OFF all: solar gone for 1 minute": T2 PV 38 W below Dump min solar 50 W for 1 min.` | Evening / storm all-off. |
| `Dump control <name>: turned OFF by "Dump OFF KU sockets: KU bus at stop volts (re-bulk)": KU bus 26.78 V ...` | That bus sagged to stop volts. |
| `Dump control <name>: turned OFF by "Dump OFF T2 sockets: T2 battery discharging past limit": ...` | The pack was supplying the load. |
| `Dump control <name>: turned OFF by "Dump SHED one per minute: ...": ...` | Shedding one socket per minute (charger left float, or Sungold load above solar). |
| `Dump load HA control (master switch) turned off triggered by action input_boolean.turn_off` + your name | Someone turned the master switch off. |
| `<switch name> turned off` + a person's name | Switched by hand. |

Every **Dump control** line starts with the socket's live name: its **Load** and its
plug's **Where** from [Plug names](plug-names.md), with the plug id and side in
brackets (`Heater (<ID> left) at Bedroom`), or just `<ID> left` when Load is blank.
The name is read when the line is written, so old lines keep the name the socket had
then. Nothing about what is plugged in is fixed in the repo.

The automations' names in this list are their new names (2026-09-28); their entity
ids did not change.

## Settings

None. To keep more than 48 hours, edit the card (`hours_to_show`). The recorder keeps
10 days by default.

## How it works

- Each automation (`dump_turn_on`, `dump_turn_off_solar_gone`, `dump_turn_off_bulk`,
  `dump_shed_load_exceeds_solar`, `dump_turn_off_rebulk_*`, `dump_turn_off_batt_*`)
  writes a `logbook.log` entry named **Dump control** against the socket it switched,
  with the socket's live Where / Load name and the measured values at that moment.
- Home Assistant's own logbook adds the context (which automation, which trigger,
  which user).
- The alert automation does not switch plugs; it shows as the automation having
  been triggered.

## Example

At 17:52 you see `<switch name> turned off` and just above it
`Dump control Heater (<ID> left) at Bedroom: turned OFF by "Dump SHED one per minute:
Sungold load above solar": Sungold load 1650 W is above T2 PV 620 W + Sungold PV
580 W.` A big normal load on the Sungold side started, so HA gave the power back.

## Recommended first test

1. After the lamp test in [Dump master switch](dump-master-switch.md), open this box:
   you should see `turning ON` and `kept ON` for the lamp socket.
2. Switch the lamp off by hand: the entry shows your name, not an automation.
