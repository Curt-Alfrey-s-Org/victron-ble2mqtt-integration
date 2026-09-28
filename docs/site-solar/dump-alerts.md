# Site solar help: Dump alerts

**Where:** Site solar > Now view > **Dump alerts**.
**Logic:** `config/packages/dump_control.yaml`, automation
`dump_notify_load_exceeds_solar` (`Dump ALERT: Sungold load above solar for 10
minutes`) and `binary_sensor.dump_load_exceeds_solar`.

## What this box is for

Tells you when the plant has been using more than the sun makes for 10 minutes, so
you can turn something off before the batteries drain.

## The entity

| Row | Entity | Type | What it does |
|---|---|---|---|
| Alert notify service | `input_text.dump_notify_service` | text, up to 64 characters | Name of an extra notify action. Blank, `persistent_notification`, `unknown` or `none` = HA notification only. A Companion phone name such as `mobile_app_my_phone` = HA notification **and** a text to that phone. |

There is no "raise / lower" here. Change it to add or remove the phone.

**Safe starting value:** blank (HA notification only). Then find your phone's
action: Developer tools > Actions, search `notify.mobile_app`, and type only the
part after `notify.` (for example `mobile_app_pixel_8`).

## How it works in the package

- `binary_sensor.dump_load_exceeds_solar` is on while Sungold AC-out
  (`sensor.sungold_sph302480a_load_power`) is **greater than** T2 MPPT PV + Sungold
  PV, and that solar is at least **Min solar** (so it is quiet at night).
- On for 10 minutes: `notify.persistent_notification` is always sent (title
  "Solar load above solar"); then, if this box holds a name other than the blank
  values above, `notify.<that name>` is sent with the same text.
- This alert runs **even when the master switch is off**. The separate shed rule
  (`Dump SHED one per minute: Sungold load above solar`) needs the master switch and
  starts after 1 minute.
- A wrong name makes the phone step fail with an error in the automation trace; the
  HA notification was already sent.
- Before 2026-09-28 this text went back to `persistent_notification` at every HA
  restart, so a phone name you typed was lost. It now keeps your value.

## Example

`mobile_app_pixel_8` typed here. At 16:10 Sungold AC-out is 1800 W while T2 PV +
Sungold PV is 1200 W. At 16:20 both the HA bell and the phone show "Load 1800 W has
been above T2 MPPT plus Sungold PV W for 10 minutes."

## Recommended first test

1. Type your phone's action name.
2. Developer tools > Actions: run `notify.<your name>` with a message, to prove the
   name is right.
3. Wait for a real overdraw, or ask for it deliberately on a cloudy moment with a big
   Sungold load: after 10 minutes you get both notifications.
