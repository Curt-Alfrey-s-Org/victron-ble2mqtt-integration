# Site solar help: Sungold voltage guard

**Where:** Site solar > Now view > **Sungold voltage guard**.
**Logic:** `config/packages/dump_control.yaml`: `input_boolean.dump_sph_vguard_enabled`,
`input_number.dump_sph_vguard_floor_v`, `input_number.dump_sph_vguard_margin_v`,
`input_number.dump_sph_vguard_hysteresis_v`, `input_number.dump_sph_vguard_dwell_s`,
`binary_sensor.dump_sph_vguard`, `sensor.dump_sph_vguard_gap`, automation
`dump_sph_vguard_shed`. Voltages: `sensor.sungold_sph302480a_battery_voltage`,
`sensor.battery_1_voltage` (T2, SmartShunt HQ2239CQYT2), `sensor.battery_2_voltage`
(KU, SmartShunt HQ2239JTRKU).

## What this box is for

While you are balancing the packs, stop dump sockets that are assigned to the Sungold
inverter from pulling the Sungold battery further below the T2 and KU voltages, or
below a floor you set. The guard tells you the state, sheds those dump sockets, and
blocks turning them on. It does not change the inverter.

## The gap

The Sungold sidecar in this repo publishes sensors only. It does not write Modbus, and
there is no other switch here for the inverter's charge current, AC charge or output
mode. Those stay on the inverter's front panel.

What this repo can do:

- Turn **off** dump sockets whose **Inverter** helper is Sungold (Use = dump, not House),
  and refuse to turn those sockets **on**, while the guard is active.
- Post a notification (and a phone text if [Dump alerts](dump-alerts.md) has a service).

What it cannot do: raise or hold Sungold voltage by itself. Shedding only removes the
AC load of the dump sockets you assigned to Sungold. If the sag is the inverter's own
load, a socket whose Use is normal, or charge settings, the guard still **alerts** and
the voltage can keep falling. No change in another repo is required for this alert and
shed; a real charge command would be new work on the read-only sidecar.

Which sockets are on the Sungold inverter is only the **Inverter** helper
(`input_select.h5082_<id>_<side>_inverter` = Sungold). Nothing in the repo names a load
or a place.

## The entities

| Row | Entity | Range / states | What it does |
|---|---|---|---|
| Guard active | `binary_sensor.dump_sph_vguard` | on / off | **on** when the guard is enabled and Sungold volts are under the floor, or under the lower of the live T2 and KU volts by the margin. Stays on until both tests have recovered by the hysteresis. **off** when the guard is disabled, Sungold volts are missing, or the voltage has recovered. Attributes: `sungold_v`, `t2_v`, `ku_v`, `ref_v` (the lower shunt, or `none`), `reason`. |
| Sungold minus lower of T2 and KU | `sensor.dump_sph_vguard_gap` | volts, may be negative | `sensor.sungold_sph302480a_battery_voltage` minus the lower of `sensor.battery_1_voltage` and `sensor.battery_2_voltage`. Negative means Sungold is below that shunt. `none` if Sungold or both shunts are missing. One missing shunt: the other shunt is the reference. |
| Sungold battery voltage | `sensor.sungold_sph302480a_battery_voltage` | V | Sungold pack voltage from the read-only sidecar. |
| T2 battery voltage | `sensor.battery_1_voltage` | V | T2 SmartShunt voltage. |
| KU battery voltage | `sensor.battery_2_voltage` | V | KU SmartShunt voltage. |
| Enable Sungold voltage guard | `input_boolean.dump_sph_vguard_enabled` | on / off | Master for this guard only. **Off:** the sensor stays off and nothing is shed for this rule. A brand-new helper starts **off**. |
| Floor (Sungold volts) | `input_number.dump_sph_vguard_floor_v` | 24.0–29.5 V, step 0.05 | Sungold at or above this is not a floor trip. Suggested start **25.6 V**. A brand-new helper starts at **24.0**. |
| Margin below the lower of T2 and KU | `input_number.dump_sph_vguard_margin_v` | 0–2 V, step 0.05 | Trip when Sungold is below (lower of T2 and KU) minus this. Suggested start **0.30 V**. A brand-new helper starts at **0** (any drop below the lower shunt). |
| Hysteresis | `input_number.dump_sph_vguard_hysteresis_v` | 0.05–1 V, step 0.05 | Once tripped, Sungold must rise by this much above the floor and above (lower shunt minus margin) before the guard clears. Suggested start **0.10 V**. A brand-new helper starts at **0.05**. |
| Minimum time under the limit | `input_number.dump_sph_vguard_dwell_s` | 15–600 s, step 15 | The guard must stay on this long before the shed and the notification. Suggested start **60 s**. A brand-new helper starts at **15**. |

No helper here has `initial:`. Home Assistant keeps what you set across a restart. The
numbers above are suggested starts, written by hand or by **Dump master switch > Load
recommended starting values** (that button also replaces every other dump number, and
it does **not** turn the guard on).

The reference is the **lower** of the two live shunt voltages, so a difference between
T2 and KU does not force Sungold to chase the higher pack. If one shunt is unavailable,
the other is used. If both are unavailable, only the floor applies.

## How it works in the package

- `binary_sensor.dump_sph_vguard` is the trip, with hysteresis taken from its own
  previous state. The automation does not hard-code the volts or the seconds: it waits
  until the sensor has been on for `input_number.dump_sph_vguard_dwell_s`.
- Then it always notifies (`notify.persistent_notification`, plus the phone service
  when set), even if the master switch is off.
- If the master switch is on, it turns off every dump socket whose Inverter is Sungold
  and that is not already off, starts that socket's 10 minute cooldown, and logs the
  reason. The same [hold](dump-hold.md) rule as the other turn-offs applies: a held
  socket is skipped only while **Hold also blocks turn-offs** is on.
- While the sensor is on, `sensor.dump_next_plug` and Turn next dump ON will not choose
  a Sungold socket. T2 and KU sockets are unchanged.
- Turning the master switch on while the guard has already been on for the dwell sheds
  at that moment.
- If a hold ends while the guard is still on and the socket is still on, `Dump HOLD end`
  turns a Sungold dump socket off (`Sungold voltage guard`).
- Missing Sungold voltage: the sensor stays **off**. It will not shed on an empty
  reading.

## Example

T2 `sensor.battery_1_voltage` = 27.20 V, KU `sensor.battery_2_voltage` = 27.00 V, so the
lower shunt is 27.00 V. Floor 25.6 V, margin 0.30 V, hysteresis 0.10 V, dwell 60 s,
guard enabled, master switch on, Hold also blocks turn-offs off.

Sungold falls to 26.65 V (below 27.00 − 0.30 = 26.70, still above the floor). The gap
sensor reads about −0.35 V. After 60 s the guard notifies and turns off dump sockets
whose Inverter is Sungold. A dump socket on T2 or KU stays on. Sungold must climb to
26.80 V (26.70 + 0.10) before the guard clears. Under the floor (25.6 V) trips the same
way even if the shunts are lower.

## Recommended first test

1. Read **Sungold battery voltage**, **T2 battery voltage** and **KU battery voltage**.
   Set floor, margin, hysteresis and dwell **before** enabling. Suggested start: 25.6 V,
   0.30 V, 0.10 V, 60 s. Leave the guard off until those four match what you typed.
2. Set one test socket's Use to dump and its Inverter to Sungold, and leave a second
   dump socket on T2 or KU. Master switch on. Hold also blocks turn-offs off.
3. Temporarily set the floor **above** the live Sungold voltage (put it back after).
   Within the dwell, Guard active turns on, a notification appears, the Sungold socket
   turns off (Dump activity log names the voltage guard), and the T2/KU socket stays.
   **Next socket HA would add** is not the Sungold socket.
4. Set the floor back to 25.6 V. When Sungold is above the floor and within the margin
   of the lower shunt, Guard active clears after the hysteresis.
