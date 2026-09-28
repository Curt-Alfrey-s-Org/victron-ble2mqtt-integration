# Site solar help: Dump settings change log

**Where:** Site solar > Now view > **Dump settings change log**.
**Logic:** Logbook card (via `auto-entities`) over `input_number.dump_*`,
`input_boolean.dump_*`, `input_text.dump_*`, `input_select.h5082_*` and
`input_text.h5082_*`, last 7 days. Card defined in `config/dashboards/solar-plant.yaml`;
the dump helpers live in `config/packages/dump_control.yaml`.

## What this box is for

Proof that your settings stay put. Every change to a dump number, the master switch,
Ignore SoC, the alert service, a socket's Use or Inverter, or a Where / Load label
shows here with **who or what** changed it.

## What the lines mean

| Line | Meaning |
|---|---|
| `Dump T2 start volts (float) changed to 27.1` + your name | You changed it. |
| `... changed to 27.0 triggered by action input_number.set_value` + `Dump settings: load recommended starting values` | The defaults button was pressed. |
| `... changed to ...` with a user that is the token's user (for example the one in `HA_TOKEN_FILE`) | A script from the repo (`site_solar_settings.py restore`) or another API client (Ask ALFa `ha_set_number`) wrote it. |
| No line at all, but the value is different after a restart | It was changed at start-up. Home Assistant does not log the first value an entity gets when HA starts, so a start-up reset never shows as a line here; hold the row in its box to see the history graph step at the restart time (see below). |

## Settings

None.

## How it works

- Home Assistant logs every state change of these helpers with its context.
- Before 2026-09-28, 18 dump helpers were reset by `initial:` in the package, and the
  Where / Load / Use helpers by `initial` stored in `.storage`. Those resets happened
  while HA was starting, so they left **no** line here, only a step in each helper's
  history graph. After the fix a restart restores the last value: the history graph
  stays flat across the restart.
- Everything changed while HA is running (by you, a button, a script, an automation or
  an API client) does show here.
- Other writers to keep in mind (outside this repo): the alfa-ai brain / Ask ALFa is
  allowed to write the dump volt, AC-cap and inverter helpers
  (`docs/DUMP_LOAD_HA_CONTROL.md`); its writes show here under the user of its token.

## Example

You set KU stop volts to 26.9 on Monday. On Wednesday it reads 26.8. The log shows
`changed to 26.8` at 03:12 by the alfa-ai token user: that was the brain, not a
reset. Ask it not to tune that helper, or accept its value.

## Recommended first test

1. Change one number (say Min solar 50 to 60) and one label.
2. Restart HA.
3. This box shows your two changes with your name; after the restart the values are
   still 60 and your label, and holding the Min solar row shows a flat history graph
   across the restart. Put Min solar back.
