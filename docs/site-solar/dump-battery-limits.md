# Site solar help: Battery discharge limits

**Where:** Site solar > Now view > **Battery discharge limits**.
**Logic:** `config/packages/dump_control.yaml`, binary sensors `dump_batt_t2_ok` /
`dump_batt_ku_ok` / `dump_batt_sph_ok`, automations `dump_turn_off_batt_t2` / `_ku`
/ `_sph`.

## What this box is for

Dump loads should only use **spare solar**, never the battery. This box says how
much battery discharge HA tolerates on each bus before it calls that battery
"not ok": then no new dump sockets on that bus, and after 1 minute every dump socket
on that bus turns off.

## The entities

| Row | Entity | Unit / range | Battery meter | Raise it | Lower it |
|---|---|---|---|---|---|
| T2 max battery discharge | `input_number.dump_max_discharge_t2_w` | W, 0-500, step 10 | `sensor.battery_1_power` (SmartShunt, + charge / - discharge) | Tolerate more drain before shutting T2 dumps off | Shut off at the first sign of discharge |
| KU max battery discharge | `input_number.dump_max_discharge_ku_w` | W, 0-500 | `sensor.battery_2_power` | as T2 | as T2 |
| Sungold max battery discharge | `input_number.dump_max_discharge_sph_w` | W, 0-500 | `sensor.sungold_sph302480a_charging_power`, or battery current x voltage when that is missing | as T2 | as T2 |

"Battery ok" = battery power >= minus the limit. With 0 W, any discharge at all
counts. With 50 W, up to 50 W of discharge is tolerated.

**Safe starting values:** T2 0 W, KU 0 W, Sungold 50 W. If dump sockets keep turning
off on tiny readings (-5 W, -12 W) while the sun is strong, raise that bus to 20-50 W.

## How it works in the package

- `sensor.dump_next_plug` only offers a socket whose bus battery is ok.
- `Dump OFF <bus> sockets: <bus> battery discharging past limit` fires when
  `dump_batt_<bus>_ok` has been off for 1 minute and the master switch is on: every
  dump socket whose Inverter is that bus and that is not already off is turned off
  (even during min-on), its min-on cancelled, its cooldown started. Other buses are
  untouched.
- If the battery meter is unavailable (shunt out of range, Sungold offline) the
  battery counts as **not ok**, so the same turn-off happens after 1 minute. That is
  deliberate: no meter, no dumping.
- Before 2026-09-28 the limits went back to 0 / 0 / 50 at every HA restart. They now
  keep your value.

## Example

KU limit 0 W. Clouds come over; `sensor.battery_2_power` reads -140 W for a minute
(the KU inverter is now pulling from the pack). `KU battery within discharge limit`
goes off, and a minute later every KU dump socket turns off with
`turned OFF by "Dump OFF KU sockets: KU battery discharging past limit": KU battery
power -140 W is past the -0 W limit for 1 min`.

## Recommended first test

1. With a lamp on a T2 dump socket that HA has turned on, look at **Batt 1 W** on the
   Now view.
2. If it is charging (positive), nothing happens. Turn on a normal load on the T2
   inverter big enough to make Batt 1 W negative for over a minute.
3. The lamp turns off with the battery line in **Dump activity log**.
4. Turn the extra load off. The lamp can come back after its 10 minute cooldown.
