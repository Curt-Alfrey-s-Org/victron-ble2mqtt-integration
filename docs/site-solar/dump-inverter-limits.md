# Site solar help: Inverter AC limits

**Where:** Site solar > Now view > **Inverter AC limits**.
**Logic:** `config/packages/dump_control.yaml`, template sensor `dump_next_plug`
(the `head` table).

## What this box is for

A ceiling per inverter: HA only *adds* a dump socket to a bus while that inverter
still has room under this many watts. It keeps HA from stacking dump loads onto an
inverter that is already busy.

## The entities

| Row | Entity | Unit / range | What it does | Raise it | Lower it |
|---|---|---|---|---|---|
| T2 inverter AC limit | `input_number.dump_ac_limit_t2_w` | W, 500-4000, step 50 | Room = limit - T2 battery discharge (`max(0, -sensor.battery_1_power)`) | More T2 sockets may be added while the pack is supplying load | HA stops adding on T2 sooner |
| KU inverter AC limit | `input_number.dump_ac_limit_ku_w` | W, 500-4000 | Room = limit - KU battery discharge (`max(0, -sensor.battery_2_power)`) | as T2 | as T2 |
| Sungold inverter AC limit | `input_number.dump_ac_limit_sph_w` | W, 500-4000 | Room = limit - Sungold AC-out (`sensor.sungold_sph302480a_load_power`) | More Sungold sockets may be added while the cart inverter is loaded | HA stops adding on Sungold sooner |

**Safe starting values:** 2000 W on each (Renogy 2 kW class). Better: the
inverter's continuous rating minus your biggest dump load on it (Sungold nameplate
is 3000 W: with a 1500 W heater, 1500 W). Never set it above the inverter's rating.

## How it works in the package

- `sensor.dump_next_plug` offers a socket only if its bus room is **greater than
  0 W** (with every other gate from [Dump status](dump-status.md)).
- HA does not know the dump plug's own watts before it turns on (H5082 sends none),
  so the check is "is there room now", not "will this load fit". That is why the
  safe value is rating minus your biggest dump load.
- For T2 and KU the "load" is only what the **battery** is supplying. While PV covers
  the load (normal in float) it reads 0 W and the room is the whole limit, so on
  T2/KU this mostly matters once the pack starts discharging. On Sungold it is the
  real AC output.
- This box never turns a socket **off**. Overload protection is the inverter itself,
  plus the battery and stop-volts rules.
- Before 2026-09-28 the three limits went back to 2000 W at every HA restart. They now
  keep your value.

## Example

Sungold limit 2000 W. Sungold AC-out is 1400 W (house loads plus one dump heater):
room 600 W > 0, so HA may add another Sungold dump socket. With a second 1500 W
heater that would be 2900 W, over the 2 kW you meant: set the limit to
2000 - 1500 = 500 W and HA stops adding once AC-out is 500 W or more.

## Recommended first test

1. With a Sungold dump socket available, note Sungold **AC out W** on the Now view.
2. Set **Sungold inverter AC limit** below that number (it must be 500 W or more).
3. **Dump status > Next socket HA would add** stops showing Sungold sockets (it shows
   another bus's socket or `none`). Nothing that is already on turns off.
4. Put the limit back.
