# Site solar help: Dump status (why / why not)

**Where:** Site solar > Now view > **Dump status (why / why not)**.
**Logic:** `config/packages/dump_control.yaml`, `template:` and `binary_sensor:`
blocks, automation `dump_turn_on`.

## What this box is for

Read-only. Every condition the dump rules check, in one place, so "why isn't it
dumping?" has an answer. Nothing here is a setting; the settings are the other boxes.

## The entities

| Row | Entity | On / value means | Set by |
|---|---|---|---|
| Sockets set to dump | `sensor.dump_sockets` | How many of the 16 sockets have Use = dump and Inverter not House (attribute `entities` lists them; attribute `held` lists the ones on [manual hold](dump-hold.md)) | [Socket Use](socket-use.md) |
| Next socket HA would add | `sensor.dump_next_plug` | The socket the add rule would switch on next, or `none` | all gates below |
| Next socket HA would shed | `sensor.dump_shed_plug` | The dump socket that goes first when shedding (last in stage order that is on), or `none` | Socket Use + plug state |
| A bus is ready | `binary_sensor.dump_charge_float` | T2 SmartSolar 100/50 is `float`, or the KU 75/15 is `float`, or Sungold is at start volts | chargers + Sungold volts |
| Solar present | `binary_sensor.dump_solar_present` | T2 100/50 PV, KU 75/15 PV, or Sungold PV >= Min solar | [Dump start conditions](dump-start-conditions.md) |
| SoC ok (or ignored) | `binary_sensor.dump_soc_ok` | Ignore SoC is on, or T2 SoC >= Min SoC | [Dump start conditions](dump-start-conditions.md) |
| T2 PV now | `sensor.smartsolar_100_50_solar_power` | T2 SmartSolar 100/50 solar watts | - |
| KU PV now | `sensor.solar_controller_solar` | Paired KU BlueSolar 75/15 solar watts. This is not the T2 charger. | - |
| T2 100/50 in float | `binary_sensor.dump_t2_charger_float` | T2 charger stage is `float`. Required before a T2-bus socket is added. | charger |
| KU 75/15 in float | `binary_sensor.dump_ku_charger_float` | KU charger stage is `float`. Required before a KU-bus socket is added. Sungold sockets do not use this. | charger |
| PV falling (blocks adding) | `binary_sensor.dump_pv_falling` | T2 PV is dropping: its 15-minute derivative (`sensor.dump_surplus_derivative`, W/min) is below the threshold helper's lower limit 0 with hysteresis 5 (turns on below about -5 W/min, off above about +5 W/min) | weather |
| Sungold load above solar (sheds) | `binary_sensor.dump_load_exceeds_solar` | Sungold AC-out > KU 75/15 PV + Sungold PV (with that sum >= Min solar). T2 100/50 watts are not in this compare. | loads |
| Sungold voltage guard (blocks adding on Sungold) | `binary_sensor.dump_sph_vguard` | On = Sungold volts are under the guard floor or under the lower of T2 and KU by the margin (hysteresis applies). While on, adding skips sockets whose Inverter is Sungold. T2 and KU are not blocked by this row. | [Sungold voltage guard](dump-sph-vguard.md) |
| A Victron is in absorption or float | `binary_sensor.dump_charge_ok` | T2 100/50 or KU 75/15 is in absorption or float. Off for 1 min sheds one socket per minute. | charger |
| <bus> at/above start volts | `binary_sensor.dump_v_float_t2` / `_ku` / `_sph` | Bus voltage >= start volts | [Dump voltage](dump-voltage.md) |
| <bus> at/below stop volts | `binary_sensor.dump_v_rebulk_t2` / `_ku` / `_sph` | Bus voltage <= stop volts; on for 1 min turns that bus's dump sockets off | [Dump voltage](dump-voltage.md) |
| <bus> battery within discharge limit | `binary_sensor.dump_batt_t2_ok` / `_ku_ok` / `_sph_ok` | Battery not discharging more than its limit; off for 1 min turns that bus's dump sockets off | [Battery discharge limits](dump-battery-limits.md) |

Below the list, **Dump sockets by name (live)** repeats the next socket to add, the
next to shed and every socket set to dump (with on/off and its bus; a House socket
is listed as "House (grid power): never switched by dump control") by **name**: the
socket's Load and its plug's Where from [Plug names](plug-names.md), with the plug id
and side in brackets, or just `<ID> left` when Load is blank. The sensors themselves
still hold switch entity ids.

## How it works in the package

HA **adds** a socket (`dump_turn_on`) only when all of these hold:

- master switch on; a Victron in float or Sungold at start volts for 1 min; solar present for 1 min; SoC ok;
- PV falling **off**; Sungold load above solar **off**;
- `sensor.dump_next_plug` names a socket. It picks, in the order 2F9D left, 2F9D
  right, 3013 left ... CF79 right, the first socket that has Use = dump (and Inverter not House), is **off**, is not on manual hold,
  has an idle cooldown (or [Skip cooldown once](dump-on-demand.md) is on), is not a Sungold
  socket while `binary_sensor.dump_sph_vguard` is on, and whose Inverter bus is at/above
  start volts, not at/below stop volts, battery ok, and under its AC limit.
  A T2 socket also needs the 100/50 in float and T2 PV >= min solar. A KU socket
  needs the 75/15 in float and KU PV >= min solar. A Sungold socket needs Sungold PV
  >= min solar and does not wait on a Victron stage (set the Sungold by hand).

HA **removes** sockets when: solar present off 1 min (all), T2 absorption/float off
1 min (one per minute), Sungold load above solar 1 min (one per minute), a bus at stop
volts 1 min or its battery not ok 1 min (all on that bus), or the Sungold voltage guard
has been on for its dwell (Sungold sockets only).

## Example

Nothing is dumping at noon. The box shows `T2 charger in float` off: the charger is
still in bulk/absorption, so the battery is not full yet. Nothing is wrong; wait.
Another day `Next socket HA would add` is `none` while everything site-wide is on:
look at the bus rows; `KU at/above start volts` is off, so the only dump socket (on
KU) is not offered.

## Recommended first test

Open this box next to **Plugs** on a sunny afternoon and walk down the list: each
off row names the box to look at. Confirm `Sockets set to dump` equals the number of
sockets you set to dump.

Silent KU 75/15 (no BLE dongle) is `Battery 2 W - paired 75/15 charge W + jumper W`. Jumper W is `Battery 1 W - SmartSolar battery W` (+ into T2). `Silent 75/15 size check` is SmartSolar PV / 3 and is not the measurement. Dump sockets are added while that bus charger is in bulk, absorption, or float (plus start volts, solar, and SoC), so the extra load can keep the Victron from finishing absorption early. Float timing stays the charger's own tail current; HA does not write the MPPT.
