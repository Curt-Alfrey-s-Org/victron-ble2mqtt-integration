# Site solar help: Sungold charge

**Where:** Site solar > Now view > **Sungold charge**.
**Logic:** `config/packages/dump_control.yaml` and the Use option `Sungold charge` from
`scripts/create_h5082_socket_labels.py`. Dashboard seed: `config/dashboards/solar-plant.yaml`.

## What this box is for

Charge the Sungold pack from a T2 or KU outlet. Two paths share this Use. There is
no second Use and no second enable switch.

**Rescue** turns the socket on when the Sungold battery is low and the bank named
by that socket's **Inverter** helper is healthy. **Surplus** turns the same socket
on when rescue is off, Sungold is still under full volts, and that bank is already
in the dump-accept state with enough charge watts going into its battery.

You choose which socket is the grid inlet by setting that socket's **Use** to
**Sungold charge** and its **Inverter** to the bank that feeds it (T2 or KU).
Nothing in the repo names a plug, a load or a place.

This is not a dump. Dump add, shed, off, on-demand and the Sungold voltage-guard
shed only look at Use = dump. A Sungold charge socket is left out of all of those,
including while rescue is on. Solar-gone, re-bulk and the dump sheds do not turn
it off.

The Sungold sidecar only reads the inverter. These rules switch the socket. They
do not write the inverter's charge settings. On the Sungold front panel, charger
source priority must allow **mains / utility** charging. If the panel is solar-only,
the socket can be on while charging power stays about 0 W. Grid voltage can still
be present in that case. The inlet alert covers both.

## The entities

| Row | Entity | Range / states | What it does |
|---|---|---|---|
| Status | `sensor.sph_charge_status` | disabled, idle, need, charging, surplus, min on, inlet dark | Short state. Attribute `reason` is the Why row. **surplus** means a Sungold charge socket is on, rescue is off, and Sungold volts are under full. **min on** means the socket is on, rescue is off, and Sungold is at or above full (or volts are missing) while the minimum on timer runs out. |
| Why | `sensor.sph_charge_status` | text | Same sensor, attribute `reason`. |
| Pack needs charge | `binary_sensor.sph_charge_need` | on / off | Rescue. On when charge control is enabled and the pack is under the floor, under the lower of T2 and KU by the margin, or under the optional SoC. Stays on until the pack reaches full volts and the optional SoC is no longer under its helper. The voltage guard does not turn this on. Missing Sungold volts do not start a floor or margin trip; if it was already on, missing volts keep it on. |
| Inlet has no power | `binary_sensor.sph_charge_inlet_dark` | on / off | On when any Sungold charge socket is on, both Sungold grid voltage and charging power are numbers, and charging power is at or below 5 W while grid voltage is at or below 0 V or at or above 50 V. Missing, `unknown` or `unavailable` sidecar values stay **off**. They are not treated as 0. |
| Feeding bank under stop volts | `binary_sensor.sph_charge_source_stop` | on / off | On when a Sungold charge socket is on and the bank named by its Inverter helper is under the source stop helper. |
| Feeding bank has surplus | `binary_sensor.sph_charge_surplus_ready` | on / off | On when rescue is off, the dump master is not holding a dump socket as next, and a Sungold charge socket is off, not on hold and not in cooldown, and its feeding bank passes the surplus checks below. |
| Sungold voltage guard (sheds dump sockets only) | `binary_sensor.dump_sph_vguard` | on / off | Shown here so you can see it. It does **not** start or hold a Sungold charge. It only sheds dump sockets whose Inverter is Sungold. See [dump-sph-vguard.md](dump-sph-vguard.md). |
| Enable Sungold charge | `input_boolean.sph_charge_enabled` | on / off | Own switch for rescue and surplus. Does not follow the dump master switch. A brand-new helper starts **off**. Turning it off leaves sockets as they are. |
| Floor (Sungold volts) | `input_number.sph_charge_floor_v` | 20–29.5 V, step 0.05 | Rescue trips when `sensor.sungold_sph302480a_battery_voltage` is under this. Suggested start **25.0 V**. A brand-new helper starts at **20**. |
| Margin below the lower of T2 and KU | `input_number.sph_charge_margin_v` | 0–2 V, step 0.05 | Rescue trips when Sungold is below the lower of `sensor.battery_1_voltage` and `sensor.battery_2_voltage`, minus this. Suggested start **0.50 V**. A brand-new helper starts at **0**. |
| Full volts (off at or above) | `input_number.sph_charge_full_v` | 24–29.5 V, step 0.05 | Rescue clears only when Sungold is at or above this. Surplus also requires Sungold under this, and turns the socket off through the pack-recovered rule once Sungold reaches it. Suggested start **26.8 V**. A brand-new helper starts at **24**. |
| Surplus min charge W | `input_number.sph_charge_surplus_min_w` | 100–4000 W, step 50 | The feeding bank's battery power must be at least this many watts **charging** (positive `sensor.battery_1_power` or `sensor.battery_2_power`) before surplus turns the socket on. Suggested start **1100 W**. A brand-new helper starts at **100**. Type 1100 by hand. |
| Also charge when SoC is low | `input_boolean.sph_charge_soc_enabled` | on / off | Off: SoC is ignored. On: rescue also trips while Sungold SoC is under the helper below, and does not clear until SoC is back up. A brand-new helper starts **off**. |
| SoC below | `input_number.sph_charge_soc_below` | 0–100 %, step 1 | Used only when the SoC switch is on. Suggested start **50**. A brand-new helper starts at **0**. |
| Source minimum volts | `input_number.sph_charge_source_min_v` | 24–29.5 V, step 0.05 | Rescue only. The feeding bank must be at or above this before the socket turns on. Suggested start **26.6 V**. A brand-new helper starts at **24**. |
| Source stop volts | `input_number.sph_charge_source_stop_v` | 24–29.5 V, step 0.05 | Turn the socket off, even during the minimum on time, when that bank falls under this. Set it **below** the source minimum. Suggested start **26.2 V**. A brand-new helper starts at **24**. |
| Require source SoC | `input_boolean.sph_charge_source_soc_enabled` | on / off | Rescue only. Off: source SoC is ignored. On: the feeding bank's SoC must also be at or above the helper below before rescue turn-on. It does not by itself turn the socket off. A brand-new helper starts **off**. |
| Source minimum SoC | `input_number.sph_charge_source_min_soc` | 0–100 %, step 1 | Used only when Require source SoC is on. Suggested start **90**. A brand-new helper starts at **0**. |
| Dwell | `input_number.sph_charge_dwell_s` | 15–600 s, step 15 | Rescue, surplus, pack-recovered and source-stop must hold this long before a switch. Suggested start **60 s**. A brand-new helper starts at **15**. |
| Minimum on time | `input_number.sph_charge_min_on_s` | 60–1800 s, step 30 | After rescue turns a socket on, pack-recovered waits until this timer is idle. Surplus does not start this timer. Source-stop does not wait. Suggested start **300 s**. A brand-new helper starts at **60**. |
| Sungold battery voltage | `sensor.sungold_sph302480a_battery_voltage` | V | Pack voltage from the read-only sidecar. |
| Sungold battery SoC | `sensor.sungold_sph302480a_battery_soc` | % | Pack SoC from the sidecar. |
| Sungold grid voltage | `sensor.sungold_sph302480a_grid_voltage` | V | Mains voltage the inverter reports. Used by the inlet alert only. |
| Sungold charging power | `sensor.sungold_sph302480a_charging_power` | W | Power into the Sungold battery. About 0 W with the socket on is the inlet alert. |
| T2 battery voltage | `sensor.battery_1_voltage` | V | T2 SmartShunt. Rescue reference and the source check when Inverter is T2. |
| KU battery voltage | `sensor.battery_2_voltage` | V | KU SmartShunt. Rescue reference and the source check when Inverter is KU. |
| T2 battery power | `sensor.battery_1_power` | W | Positive means the T2 pack is charging. Surplus on Inverter T2 compares this with Surplus min charge W. |
| KU battery power | `sensor.battery_2_power` | W | Positive means the KU pack is charging. Surplus on Inverter KU compares this with Surplus min charge W. |
| T2 battery SoC | `sensor.battery_1_state_of_charge` | % | Used only when Require source SoC is on and Inverter is T2. |
| KU battery SoC | `sensor.battery_2_state_of_charge` | % | Used only when Require source SoC is on and Inverter is KU. |

`binary_sensor.sph_charge_surplus_stop` is not on the card. It is on while rescue
is off, Sungold is not yet at full volts, and a Sungold charge socket should turn
off because its feeding bank no longer passes the surplus checks.

No helper here has `initial:`. Home Assistant keeps what you type across a restart.
**Load recommended starting values** does not write these numbers and does not turn
the enable switch on. Set them by hand, including Surplus min charge W at 1100.

The rescue reference is the **lower** of the two live shunt voltages. One shunt
missing: the other is the reference. Both missing: only the floor, the full helper
and the optional SoC apply.

Which socket is the inlet is only the **Use** helper
(`input_select.h5082_<id>_<side>_use` = `Sungold charge`) and the **Inverter** helper
(`input_select.h5082_<id>_<side>_inverter` = `T2` or `KU`). House and Sungold are
not feeding banks. A socket set to Sungold charge with Inverter Sungold is not
switched by this rule and is not shed by the voltage guard (the guard only sheds
Use = dump).

### Helpers removed from the package

`input_number.sph_charge_target_v` (target gap) and `input_number.sph_charge_confirm_s`
(inlet confirm) are no longer in `dump_control.yaml`. Full volts are the only rescue
cap. The inlet alert is a fixed 3 minutes (`00:03:00`). They were YAML package
helpers, not storage helpers. The install restart drops them with the package. A
dashboard card that still names them shows unavailable until the Site solar seed is
applied. If one is still listed after that restart, delete it under Settings >
Devices & services > Helpers. Nothing in the automations writes them, so a leftover
row is unused.

## How it works in the package

- `binary_sensor.sph_charge_need` is the rescue trip, with the off point taken from
  its previous state. The automations do not hard-code the volts.
- Rescue on (`dump_sph_charge_on`) waits until need has been on for
  `input_number.sph_charge_dwell_s`, then switches each eligible socket. It also
  runs when the feeding bank's volts or SoC change, on Home Assistant start, and
  every minute, so a need that is already on after a restart still acts.
- A rescue socket is eligible when Use is Sungold charge, Inverter is T2 or KU, the
  switch is off, manual hold is not active, that bank's volts are at or above
  `input_number.sph_charge_source_min_v`, and (only if Require source SoC is on)
  that bank's SoC is at or above `input_number.sph_charge_source_min_soc`.
  Rescue does **not** wait for the 10 minute cooldown.
- Rescue starts that socket's min-on timer at `input_number.sph_charge_min_on_s`.
- Pack recovered (`dump_sph_charge_off`) runs only when Sungold volts are at or
  above full. It waits until need has been off for the dwell, then until that
  socket's min-on timer is idle, then turns it off and starts the cooldown. It
  does not turn off a surplus charge that is still under full volts.
- Surplus on (`dump_sph_charge_surplus_on`) runs only while need is off. The feeding
  bank must be in float (`binary_sensor.dump_v_float_t2` or `dump_v_float_ku`),
  `binary_sensor.dump_solar_present` on, not at stop volts (`dump_v_rebulk_t2` or
  `dump_v_rebulk_ku` off), within its discharge limit (`dump_batt_t2_ok` or
  `dump_batt_ku_ok`), and charging by at least
  `input_number.sph_charge_surplus_min_w`, and Sungold must be under full volts.
  The socket must be off, not on hold, and its cooldown must be idle. It does not
  start the min-on timer.
- Surplus waits while `input_boolean.dump_control_enabled` is on and
  `sensor.dump_next_plug` still names a dump socket, so small dumps stage first.
  When the dump master is off, surplus does not wait on that sensor.
- Surplus off (`dump_sph_charge_surplus_off`) turns the socket off when those bank
  checks fail, or when Sungold volts are not a number, after the dwell, once the
  min-on timer is idle. Reaching full volts is the pack-recovered rule. While
  rescue is on, this rule leaves the socket alone.
- Source stop (`dump_sph_charge_source_stop`) does not wait for the minimum on
  time. It turns the socket off after the feeding bank has been under
  `input_number.sph_charge_source_stop_v` for the dwell, then starts the cooldown.
  That cooldown does not block a later rescue.
- Each automatic switch fires `dump_control_switching` first, so it does not arm
  manual hold. A hand tap (Plugs button or the plug's own button) does arm
  `timer.h5082_<id>_<side>_hold` for **Dump manual hold** minutes, the same as a
  dump socket, when Inverter is T2 or KU and hold minutes are above 0.
  Turn-on always skips a hold. Turn-off skips a hold only while **Hold also blocks
  turn-offs** is on. When a hold ends, a surplus charge that still qualifies stays
  on. A hold that ends while rescue is off and the bank no longer qualifies turns
  the socket off.
- The inlet alert (`dump_sph_charge_inlet_dark`) notifies after a fixed 3 minutes
  when `binary_sensor.sph_charge_inlet_dark` stays on. It uses
  `notify.persistent_notification` and `input_text.dump_notify_service` when that
  is a notify service name. It does not turn the socket off. Unknown sidecar
  values do not start it.
- Unavailable plugs are not commanded on (the switch state is not `off`). A bridge
  that is down leaves those sockets unavailable; that is a host issue, not this rule.
- The dump master switch is not required for rescue. It only delays surplus while
  a dump socket is still next.

## Voltage guard

The guard only sheds dump sockets whose Inverter is Sungold, and it still blocks
adding those dump sockets. It does not turn `binary_sensor.sph_charge_need` on and
it does not turn a Sungold charge socket on. You can run the charge rule with the
guard off. You can run the guard with charge off (alert and shed only, no inlet).

## Example

Set one socket's Use to **Sungold charge** and its Inverter to **T2** (the bank
that actually feeds that inlet). Leave every other socket as it is. Type the
suggested starts: floor 25.0 V, margin 0.50 V, full 26.8 V, surplus min charge
1100 W, source minimum 26.6 V, source stop 26.2 V, dwell 60 s, minimum on 300 s.
Leave both SoC switches off. Then turn **Enable Sungold charge** on.

With Sungold at 22.0 V and T2 and KU near 27 V, pack-needs-charge turns on (22 is
under the floor and under 27 minus 0.50). After the dwell, that socket turns on
even if its cooldown timer is still active. Status reads **charging**. If grid
voltage stays 0 and charging power stays about 0 for 3 minutes, or grid voltage
is present (50 V or more) and charging power stays about 0 for 3 minutes, you get
a notification: the plug did not pass power, or the Sungold panel is not allowing
mains charging. If the sidecar values are unavailable, there is no notification.

When Sungold reaches 26.8 V, need clears. The socket stays on until the minimum
on time ends, then turns off and takes a 10 minute cooldown. If T2 falls under
26.2 V while the socket is on, it turns off without waiting out the minimum on time.

Later, with rescue off and Sungold at 26.6 V (under 26.8), T2 in float, solar
present, T2 not at stop volts, T2 within its discharge limit, and T2 battery power
at or above 1100 W: after the dwell, and after any waiting dump socket, that same
socket turns on. Status reads **surplus**. If T2 charge power falls under 1100 W
for the dwell, the socket turns off and takes a cooldown. Rescue can turn it back
on during that cooldown if the pack goes low again.

## Recommended first test

1. Do not enable yet. On the inlet socket only, set Use to **Sungold charge** and Inverter to the bank that feeds it (T2 or KU). Confirm **Sockets set to dump** does not count it.
2. Type the suggested starts above, including Surplus min charge W at 1100. Confirm the enable switch is still off and Status reads **disabled**.
3. On the Sungold panel, set charger source priority so mains / utility charging is allowed.
4. Turn **Enable Sungold charge** on. With the pack under the floor, Status goes to **need** and, after the dwell, the inlet socket turns on if that bank is at or above the source minimum.
5. If the socket turns on and charging power stays at or below 5 W for 3 minutes, with grid voltage at or below 0 or at or above 50, the notification appears and the socket stays on. Unavailable sidecar values do not notify.
6. Raise the full helper below the live Sungold voltage (or wait until the pack recovers). After the dwell and the minimum on time, the socket turns off.
7. With the pack under full volts and rescue off, raise the feeding bank's charge power above 1100 W while that bank is in float with solar present. After small dumps and the dwell, the socket turns on and Status reads **surplus**.
8. Tap the socket by hand with Dump manual hold above 0. The activity log shows a `by hand` line and the button shows a hold. With **Hold also blocks turn-offs** on, a recovery does not turn it off until the hold ends.
