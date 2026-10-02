# Site solar help: Sungold charge

**Where:** Site solar > Now view > **Sungold charge**.
**Logic:** `config/packages/dump_control.yaml` and the Use option `Sungold charge` from
`scripts/create_h5082_socket_labels.py`. Dashboard seed: `config/dashboards/solar-plant.yaml`.

## What this box is for

Charge the Sungold pack from a T2 or KU outlet when the Sungold battery is low.
You choose which socket is the grid inlet by setting that socket's **Use** to
**Sungold charge** and its **Inverter** to the bank that feeds it (T2 or KU).
Nothing in the repo names a plug, a load or a place.

This is not a dump. Dump add, shed, off, on-demand and the Sungold voltage-guard
shed only look at Use = dump. A Sungold charge socket is left out of all of those.

The Sungold sidecar only reads the inverter. These rules switch the socket. They
do not write the inverter's charge settings. On the Sungold front panel, charger
source priority must allow **mains / utility** charging. If the panel is solar-only,
the socket can be on while `sensor.sungold_sph302480a_grid_voltage` stays 0 V and
`sensor.sungold_sph302480a_charging_power` stays 0 W, and the pack does not charge.

## The entities

| Row | Entity | Range / states | What it does |
|---|---|---|---|
| Status | `sensor.sph_charge_status` | disabled, idle, need, charging, min on, inlet dark | Short state. Attribute `reason` is the Why row. |
| Why | `sensor.sph_charge_status` | text | Same sensor, attribute `reason`. |
| Pack needs charge | `binary_sensor.sph_charge_need` | on / off | On when charge control is enabled and the pack is under the floor, under the lower of T2 and KU by the margin, under the optional SoC, or `binary_sensor.dump_sph_vguard` is on. Stays on until the pack reaches full volts or comes within the target gap of that lower shunt, the guard is off, and the optional SoC is no longer under its helper. Missing Sungold volts do not start a floor or margin trip; if it was already on, missing volts keep it on. |
| Inlet has no power | `binary_sensor.sph_charge_inlet_dark` | on / off | On when any Sungold charge socket is on and both grid voltage and charging power are missing or at or below 0. |
| Feeding bank under stop volts | `binary_sensor.sph_charge_source_stop` | on / off | On when a Sungold charge socket is on and the bank named by its Inverter helper is under the source stop helper. |
| Sungold voltage guard (also a charge reason) | `binary_sensor.dump_sph_vguard` | on / off | While this is on and Sungold charge is enabled, pack-needs-charge stays on. The guard itself still only sheds dump sockets whose Inverter is Sungold. See [dump-sph-vguard.md](dump-sph-vguard.md). |
| Enable Sungold charge | `input_boolean.sph_charge_enabled` | on / off | Own switch. Does not follow the dump master switch. A brand-new helper starts **off**. Turning it off leaves sockets as they are. |
| Floor (Sungold volts) | `input_number.sph_charge_floor_v` | 20–29.5 V, step 0.05 | Trip when `sensor.sungold_sph302480a_battery_voltage` is under this. Suggested start **25.0 V**. A brand-new helper starts at **20**. |
| Margin below the lower of T2 and KU | `input_number.sph_charge_margin_v` | 0–2 V, step 0.05 | Trip when Sungold is below the lower of `sensor.battery_1_voltage` and `sensor.battery_2_voltage`, minus this. Suggested start **0.50 V**. A brand-new helper starts at **0** (any reading under the lower shunt). |
| Target gap (off when this close) | `input_number.sph_charge_target_v` | 0–2 V, step 0.05 | Once charging, clear when Sungold is at or above (lower shunt minus this). Keep this **smaller than the margin** so the off point sits above the on point. Suggested start **0.20 V**. A brand-new helper starts at **0**. |
| Full volts (off at or above) | `input_number.sph_charge_full_v` | 24–29.5 V, step 0.05 | Once charging, clear when Sungold is at or above this, even if it is not yet within the target gap. Suggested start **26.8 V**. A brand-new helper starts at **24**. |
| Also charge when SoC is low | `input_boolean.sph_charge_soc_enabled` | on / off | Off: SoC is ignored. On: also trip while Sungold SoC is under the helper below, and do not clear until SoC is back up. A brand-new helper starts **off**. |
| SoC below | `input_number.sph_charge_soc_below` | 0–100 %, step 1 | Used only when the SoC switch is on. Suggested start **50**. A brand-new helper starts at **0**. |
| Source minimum volts | `input_number.sph_charge_source_min_v` | 24–29.5 V, step 0.05 | The feeding bank (the socket's Inverter, T2 or KU) must be at or above this before the socket turns on. Suggested start **26.6 V**. A brand-new helper starts at **24**. |
| Source stop volts | `input_number.sph_charge_source_stop_v` | 24–29.5 V, step 0.05 | Turn the socket off, even during the minimum on time, when that bank falls under this. Set it **below** the source minimum. Suggested start **26.2 V**. A brand-new helper starts at **24**. |
| Require source SoC | `input_boolean.sph_charge_source_soc_enabled` | on / off | Off: source SoC is ignored. On: the feeding bank's SoC must also be at or above the helper below before turn-on. It does not by itself turn the socket off. A brand-new helper starts **off**. |
| Source minimum SoC | `input_number.sph_charge_source_min_soc` | 0–100 %, step 1 | Used only when Require source SoC is on. Suggested start **90**. A brand-new helper starts at **0**. |
| Dwell | `input_number.sph_charge_dwell_s` | 15–600 s, step 15 | Pack-needs-charge, pack-recovered and source-stop must hold this long before a switch. Suggested start **60 s**. A brand-new helper starts at **15**. |
| Minimum on time | `input_number.sph_charge_min_on_s` | 60–1800 s, step 30 | After a recovery, the socket stays on at least this long (the socket's min-on timer). Source-stop does not wait. Suggested start **300 s**. A brand-new helper starts at **60**. |
| Inlet confirm | `input_number.sph_charge_confirm_s` | 30–900 s, step 30 | How long the inlet must look dark before the notification. Suggested start **180 s**. A brand-new helper starts at **30**. The socket is not turned off by this alert. |
| Sungold battery voltage | `sensor.sungold_sph302480a_battery_voltage` | V | Pack voltage from the read-only sidecar. |
| Sungold battery SoC | `sensor.sungold_sph302480a_battery_soc` | % | Pack SoC from the sidecar. |
| Sungold grid voltage | `sensor.sungold_sph302480a_grid_voltage` | V | Mains voltage the inverter reports. 0 means the inlet is not reaching it. |
| Sungold charging power | `sensor.sungold_sph302480a_charging_power` | W | Power into the Sungold battery. 0 with grid voltage 0 means the inlet is not charging. |
| T2 battery voltage | `sensor.battery_1_voltage` | V | T2 SmartShunt. Reference and the source check when Inverter is T2. |
| KU battery voltage | `sensor.battery_2_voltage` | V | KU SmartShunt. Reference and the source check when Inverter is KU. |
| T2 battery SoC | `sensor.battery_1_state_of_charge` | % | Used only when Require source SoC is on and Inverter is T2. |
| KU battery SoC | `sensor.battery_2_state_of_charge` | % | Used only when Require source SoC is on and Inverter is KU. |

No helper here has `initial:`. Home Assistant keeps what you type across a restart.
**Load recommended starting values** does not write these numbers and does not turn
the enable switch on. Set them by hand.

The reference is the **lower** of the two live shunt voltages. One shunt missing:
the other is the reference. Both missing: only the floor, the full helper, the
optional SoC and the voltage guard apply.

Which socket is the inlet is only the **Use** helper
(`input_select.h5082_<id>_<side>_use` = `Sungold charge`) and the **Inverter** helper
(`input_select.h5082_<id>_<side>_inverter` = `T2` or `KU`). House and Sungold are
not feeding banks. A socket set to Sungold charge with Inverter Sungold is not
switched by this rule and is not shed by the voltage guard (the guard only sheds
Use = dump).

## How it works in the package

- `binary_sensor.sph_charge_need` is the trip, with the off point taken from its
  previous state. The automations do not hard-code the volts or the seconds.
- Turn on (`dump_sph_charge_on`) waits until need has been on for
  `input_number.sph_charge_dwell_s`, then switches each eligible socket. It also
  runs when the feeding bank's volts or SoC change, so a bank that was low can
  start the inlet once it recovers, without waiting for need to toggle again.
- A socket is eligible when Use is Sungold charge, Inverter is T2 or KU, the
  switch is off, manual hold is not active, the 10 minute cooldown timer is idle,
  that bank's volts are at or above `input_number.sph_charge_source_min_v`, and
  (only if Require source SoC is on) that bank's SoC is at or above
  `input_number.sph_charge_source_min_soc`.
- Turn off after recovery (`dump_sph_charge_off`) waits until need has been off
  for the dwell, then waits until that socket's min-on timer is idle, then turns
  it off and starts the cooldown. If the min-on timer is still running, it tries
  again when the timer goes idle.
- Source stop (`dump_sph_charge_source_stop`) does not wait for the minimum on
  time. It turns the socket off after the feeding bank has been under
  `input_number.sph_charge_source_stop_v` for the dwell, then starts the cooldown.
- Each automatic switch fires `dump_control_switching` first, so it does not arm
  manual hold. A hand tap (Plugs button or the plug's own button) does arm
  `timer.h5082_<id>_<side>_hold` for **Dump manual hold** minutes, the same as a
  dump socket, when Inverter is T2 or KU and hold minutes are above 0.
  Turn-on always skips a hold. Turn-off skips a hold only while **Hold also blocks
  turn-offs** is on.
- The inlet alert (`dump_sph_charge_inlet_dark`) notifies after
  `input_number.sph_charge_confirm_s` when a Sungold charge socket is on and both
  grid voltage and charging power are still not above 0. It uses
  `notify.persistent_notification` and `input_text.dump_notify_service` when that
  is a notify service name. It does not turn the socket off.
- Unavailable plugs are not commanded on (the switch state is not `off`). A bridge
  that is down leaves those sockets unavailable; that is a host issue, not this rule.
- The dump master switch is not required. Sungold charge has its own enable switch.

## Voltage guard

Keep it as two switches. The guard still only sheds dump sockets whose Inverter is
Sungold, and it still blocks adding those dump sockets. If **both** Enable Sungold
charge and the voltage guard are on, a guard trip is also a reason for
`binary_sensor.sph_charge_need` to stay on, so the inlet turns on under the guard's
own floor and margin. You can run the charge rule with the guard off. You can run
the guard with charge off (alert and shed only, no inlet).

## Example

Set one socket's Use to **Sungold charge** and its Inverter to **T2** (the bank
that actually feeds that inlet). Leave every other socket as it is. Type the
suggested starts: floor 25.0 V, margin 0.50 V, target gap 0.20 V, full 26.8 V,
source minimum 26.6 V, source stop 26.2 V, dwell 60 s, minimum on 300 s, inlet
confirm 180 s. Leave both SoC switches off. Then turn **Enable Sungold charge** on.

With Sungold at 22.0 V and T2 and KU near 27 V, pack-needs-charge turns on (22 is
under the floor and under 27 minus 0.50). After the dwell, that socket turns on.
Status reads **charging**. If grid voltage and charging power are still 0 after
the inlet confirm, you get a notification: the plug did not pass power, or the
Sungold panel is not allowing mains charging.

When Sungold reaches 26.8 V, need clears. The socket stays on until the minimum
on time ends, then turns off and takes a 10 minute cooldown. If T2 falls under
26.2 V while the socket is on, it turns off without waiting out the minimum on time.

## Recommended first test

1. Do not enable yet. On the inlet socket only, set Use to **Sungold charge** and Inverter to the bank that feeds it (T2 or KU). Confirm **Sockets set to dump** does not count it.
2. Type the suggested starts above. Confirm the enable switch is still off and Status reads **disabled**.
3. On the Sungold panel, set charger source priority so mains / utility charging is allowed.
4. Turn **Enable Sungold charge** on. With the pack under the floor, Status goes to **need** and, after the dwell, the inlet socket turns on if that bank is at or above the source minimum.
5. If the socket turns on and grid voltage and charging power stay at 0 for the inlet confirm, the notification appears and the socket stays on.
6. Raise the full helper below the live Sungold voltage (or wait until the pack recovers). After the dwell and the minimum on time, the socket turns off.
7. Tap the socket by hand with Dump manual hold above 0. The activity log shows a `by hand` line and the button shows a hold. With **Hold also blocks turn-offs** on, a recovery does not turn it off until the hold ends.
