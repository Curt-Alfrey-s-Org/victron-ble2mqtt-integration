# Site solar help: Dump start conditions

**Where:** Site solar > Now view > **Dump start conditions**.
**Logic:** `config/packages/dump_control.yaml` (`binary_sensor.dump_solar_present`,
`binary_sensor.dump_soc_ok`, `binary_sensor.dump_load_exceeds_solar`, automations
`dump_turn_on` and `dump_turn_off_solar_gone`).

## What this box is for

Site-wide gates that apply to every dump socket, whatever bus it is on:

- **Min solar** decides when "the sun is up". Below it for 1 minute, every dump
  socket turns off. This is what keeps dump loads from running at night.
- **Min T2 SoC** blocks *adding* dump sockets while the T2 battery's state of charge
  is lower.
- **Ignore SoC** switches the SoC check off (for when the SmartShunt has not synced
  to 100 % yet and its SoC number cannot be trusted).

## The entities

| Row | Entity | Unit / range | What it does | Raise it | Lower it |
|---|---|---|---|---|---|
| Min solar (below = solar gone) | `input_number.dump_min_solar_w` | W, 0-500, step 10 | `binary_sensor.dump_solar_present` is on while T2 MPPT PV (`sensor.solar_controller_solar`, fallback `sensor.solar_controller_solar_power`) >= this | Dumps start later in the morning and stop earlier at dusk or in clouds | Dumps run later into dusk; **never 0** (0 W >= 0 is always true, so night never counts as "solar gone") |
| Min T2 SoC to add sockets | `input_number.dump_min_soc_percent` | %, 80-100, step 1 | `binary_sensor.dump_soc_ok` is on while `sensor.battery_1_state_of_charge` >= this (only when Ignore SoC is off) | Fewer dump starts (battery must be fuller) | More dump starts at a lower SoC |
| Ignore SoC (shunt not synced) | `input_boolean.dump_soc_unsynced` | on / off | On: `dump_soc_ok` is always on (SoC not checked). Off: SoC must be >= Min T2 SoC | - | - |

**Safe starting values:** min solar 50 W, min SoC 95 %, Ignore SoC **on** until the
T2 SmartShunt has done a full charge and synced to 100 %, then **off**.

## How it works in the package

- `Dump ON: add dump sockets while the charger is in float` (`dump_turn_on`) needs
  `dump_solar_present` on for 1 minute and `dump_soc_ok` on, and checks both again
  before every extra socket. `sensor.dump_next_plug` returns `none` while either is
  off.
- `Dump OFF all: solar gone for 1 minute` (`dump_turn_off_solar_gone`) fires when
  `dump_solar_present` has been off for 1 minute: every dump socket that is not
  already off is turned off, its min-on cancelled, its cooldown started.
- Min solar is also part of `binary_sensor.dump_load_exceeds_solar`: that alarm is
  only on while T2 PV + Sungold PV is at least min solar (so it stays quiet at night).
- Only the **T2** SoC (`sensor.battery_1_state_of_charge`) is checked, for every
  socket, including KU and Sungold ones.
- SoC below the minimum only stops **adding**. It does not turn sockets off; the
  voltage and battery rules do that.
- Before 2026-09-28 `Ignore SoC` was forced **on** at every restart and both numbers
  went back to 50 / 95. They now keep your setting. On a brand-new install Ignore SoC
  starts **off** (SoC checked) until you press **Load recommended starting values**.

## Example

Min solar 50 W. At 18:40 T2 PV falls to 45 W. `Solar present` turns off; at 18:41
every dump socket turns off and the activity log says
`turned OFF by "Dump OFF all: solar gone for 1 minute": T2 PV 45 W below Dump min
solar 50 W for 1 min`. If you want dumps to stop earlier, raise it to 100 W.

## Recommended first test

1. Keep the lamp test socket from [Socket Use](socket-use.md) on while dumping.
2. Late afternoon, set **Min solar** a little above the present T2 PV (see
   **Dump status > T2 PV now**). After about a minute the lamp turns off with the
   "solar gone" line in the activity log.
3. Put **Min solar** back to 50 W.
4. With Ignore SoC **off**, set Min T2 SoC above the present SoC: **Dump status >
   SoC ok** goes off and no new socket is added. Set it back.
