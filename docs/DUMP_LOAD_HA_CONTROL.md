# Dump-load control in Home Assistant

Home Assistant owns dump-load **on/off**. The program follows Victron's charge
cycle, not a PV-minus-load watt band. In **float**, the MPPT already throttles to
match load; a 20 W "surplus" is normal. Dump then **claims leftover PV** by adding
plugs until bus voltage approaches **re-bulk**, then sheds so the packs stay full
when the sun stops (weather or end of day). Target: **95%+ SoC remaining** after
PV is gone -- dumps must not run as night loads.

alfa-ai does **not** toggle these switches from its ticker. The brain **observes**
HA states, keeps the watt-ledger for Ask ALFa, and may write dump **helpers**
(float/re-bulk volts, AC caps, inverter assign) immediately.

This site: LiTime 24 V 230 Ah on T2 and KU ([product](https://www.litime.com/products/24v-230ah-truck-lithium-battery)
charge **28.8 V +/- 0.4 V**). Sungold cart is a separate LiTime 24 V pair.

Official manuals (RULE #1):

- Packages: [configuration packages](https://www.home-assistant.io/docs/configuration/packages/)
- Automations YAML (labeled `automation` block): [Automations in YAML](https://www.home-assistant.io/docs/automation/yaml/)
- Switch actions: [switch.turn_on](https://www.home-assistant.io/integrations/switch/) /
  [switch.turn_off](https://www.home-assistant.io/integrations/switch/)
- Threshold helper (numeric hysteresis): [Threshold](https://www.home-assistant.io/integrations/threshold/)
- State trigger `for:` (dwell): [State trigger](https://www.home-assistant.io/docs/automation/trigger/)
- Timer helper (per-plug min-on and cooldown): [Timer](https://www.home-assistant.io/integrations/timer/)
- Delay (`delay` seconds, templates): [Wait for time to pass](https://www.home-assistant.io/docs/scripts/#wait-for-time-to-pass-delay)
- Derivative helper (PV rising/falling): [Derivative](https://www.home-assistant.io/integrations/derivative/)
- Template sensors: [Template](https://www.home-assistant.io/integrations/template/)
- Number helper (AC watt cap and max battery discharge): [Input number](https://www.home-assistant.io/integrations/input_number/)
- Dropdown helpers (which sockets are dump, which inverter feeds each): [Input select](https://www.home-assistant.io/integrations/input_select/)
- Wait for the plug to report on: [Wait for a template](https://www.home-assistant.io/docs/scripts/#wait-for-a-template)
- Staged ON (`repeat` / `while` / `delay` / `if` / `stop`): [Script syntax](https://www.home-assistant.io/docs/scripts/)
- Notifications: [Notify](https://www.home-assistant.io/integrations/notify/) and [Companion](https://companion.home-assistant.io/docs/notifications/notifications-basic/)
- State `for:` 10 min / 1 min: [State trigger](https://www.home-assistant.io/docs/automation/trigger/)
- MQTT discovery (same HA path Victron BLE already uses): [MQTT](https://www.home-assistant.io/integrations/mqtt/)
- Govee BLE sensors only (**not** H5082 plugs): [Govee Bluetooth](https://www.home-assistant.io/integrations/govee_ble/)
- Victron charge stages and 1-minute re-bulk: [BlueSolar operation](https://www.victronenergy.com/media/pg/Manual_BlueSolar_MPPT_75-10_up_to_100-20/en/operation.html)
- SmartShunt current sign (+charge / -discharge): [SmartShunt operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)

Morningstar diversion role (excess after the battery is served):
[Diversion Manual §6.0](https://www.morningstarcorp.com/wp-content/uploads/technical-doc-diversion-manual-en.pdf).

Do **not** invent PV watts from Ecobee `weather.*`. Optional later: HA
[Forecast.Solar](https://www.home-assistant.io/integrations/forecast_solar/) sensors.

---

## What HA owns vs what Ask ALFa / the brain owns

Victron [BlueSolar operation](https://www.victronenergy.com/media/pg/Manual_BlueSolar_MPPT_75-10_up_to_100-20/en/operation.html):
bulk fills, absorption holds CV (~**28.4 V** on Victron lithium / LiTime 28.4-29.2 V),
float **holds** Vfloat (Victron LiFePO4 default **27.0 V** on 24 V). Re-bulk when
`Vbat < (Vfloat - 0.1 V)` for **12 V**, **multiply by two on 24 V** (offset **0.2 V**
-> **26.8 V** if float is 27.0 V) for **one minute**. Morningstar
[Diversion §6.0](https://www.morningstarcorp.com/wp-content/uploads/technical-doc-diversion-manual-en.pdf):
divert excess **after** the battery is served. Confirm float on the T2 MPPT in
VictronConnect; recommended 27.0 / 26.8 (Recommended defaults button); the values
survive restarts and Ask ALFa may tune them.

| Job | Owner |
|-----|--------|
| Kill switch | HA `input_boolean.dump_control_enabled` |
| `switch.turn_on` / `turn_off` | HA automations only |
| **When** dump may start | HA: T2 MPPT **float** for 1 min **and** that bus's shunt/cart voltage **>= float helper** for 1 min **and** solar present. **Not** bulk. **Not** surplus watts. |
| **Which** sockets | Only sockets whose `input_select.h5082_<id>_<side>_use` is **dump** (Site solar **Use**; default **normal**). A normal socket is never switched by these automations. All 16 sockets (8 plugs) are in the list. What is plugged into a socket is only its HA **Load** text, never hard-coded. |
| **How many** plugs (claim leftover PV) | HA staged ON: one socket, **site load delta** after `dump_site_confirm_s` (default 5 s), then another while that bus stays above re-bulk, batt ok, inverter headroom, and that plug's cooldown is idle |
| **When** dump must stop (keep 95%+ after PV) | HA: solar gone 1 min (cancels min-on); bus voltage **<= re-bulk helper** 1 min; pack discharging `dump_batt_t2_ok` / `_ku_ok` / `_sph_ok` off 1 min; **Sungold Load now > Solar now** 1 min sheds **one** dump plug per minute (`sensor.dump_shed_plug`); T2 MPPT not absorb/float 1 min sheds **one** plug per minute (not all at once) |
| **Loads > solar 10 min** | HA `binary_sensor.dump_load_exceeds_solar` (Sungold AC-out vs T2 MPPT PV + Sungold PV) `for: 00:10:00` then [notify](https://www.home-assistant.io/integrations/notify/). Helper `input_text.dump_notify_service` (recommended `persistent_notification`; empty = persistent notification only; set to Companion `mobile_app_<device>` for phone text). alfa-ai does **not** send this SMS. |
| Float / re-bulk volt helpers | HA `input_number.dump_float_*_v` / `dump_rebulk_*_v` (recommended 27.0 / 26.8; kept across restarts). Ask ALFa may `ha_set_number` immediately to match VictronConnect. |
| Min solar W (day vs night) | HA `input_number.dump_min_solar_w` (recommended 50). Below that for 1 min = PV stopped. |
| SoC 95% floor | HA `input_number.dump_min_soc_percent` (95) **only when** `input_boolean.dump_soc_unsynced` is **off**. While unsynced, float voltage **is** the full-enough gate (do not invent a voltage-to-% map). |
| Site confirm / delta | HA `input_number.dump_site_confirm_s` (5-30 s, recommended 5) and `input_number.dump_site_delta_min_w` (5-500 W, recommended 25) |
| Per-socket min-on / cooldown | HA `timer.h5082_<id>_<side>_min_on` (15 min, `restore: true`) and `timer.h5082_<id>_<side>_cooldown` (10 min, `restore: true`) |
| Inverter caps, socket->bus | HA `dump_ac_limit_t2_w` / `_ku_w` / `_sph_w`; `input_select.h5082_<id>_<side>_inverter` (Sungold / T2 / KU; no `initial`, so the choice survives restarts). H5082 sends no watts. |
| Watt-ledger, AI Actions, `ha_dump_tick` | alfa-ai **observe / audit** |
| Tune helpers, inspect meters | Ask ALFa `ha_set_number` / `ha_select_option` / `ha_get_states` (no Approve). **Never** dump-actuate standing night loads. |
| Surplus W (`sensor.dump_surplus_w`) | Briefing only. **Not** the ON/OFF trigger. |

Do **not** add a second dump ticker in alfa-ai that calls `switch.turn_on` /
`turn_off` while this package is loaded.

---

## Package

Tracked source: `config/packages/dump_control.yaml` (replaced the retired
`sim_dump_control.yaml` + `sim_dump_plugs.yaml` on 2026-09-28).

Depends on:

- The H5082 MQTT switches `switch.ihoment_h5082_<id>_<side>` from `govee_h5082`
  (`h5082-mqtt.service` on the Pi 4, `hci1`) -- see [H5082_INSTALL_PLAN.md](H5082_INSTALL_PLAN.md).
- The per-socket helpers `input_select.h5082_<id>_<side>_use` (normal / dump) from
  `scripts/create_h5082_socket_labels.py`. Missing or unknown = normal.

Dump sockets: the 16 sockets of 2F9D, 3013, 3EC9, 82FB, 9607, C061, C38D, CF79 whose
**Use** is dump. Stage order is that list (left before right); shed order is the
reverse. C38D was paired on the bridge 2026-09-28 and has the same Use / Inverter
selects and min-on / cooldown timers as every other socket.

**What is plugged in is not in the repo.** Loads move and plugs move, so the repo never
says what a socket feeds or where a plug is. Set **Where** (per plug) and **Load** (per
side) in HA under Site solar > **Plug names**; the Plugs buttons, the Socket Use /
Socket inverter rows, **Dump status > Dump sockets by name** and every **Dump control**
logbook line read them live (`Heater (<ID> left) at Bedroom`, or `<ID> left` when Load
is blank). Per-box help: [site-solar/plug-names.md](site-solar/plug-names.md).
`sensor.dump_sockets` shows how many sockets are dump (attribute `entities`).

PV watts: live MQTT id `sensor.solar_controller_solar`, with fallback
`sensor.solar_controller_solar_power`. Charge stage: live
`sensor.solar_controller_charge_state`, with fallback
`sensor.solar_controller_battery_state`. Bus volts: `sensor.battery_1_voltage` /
`sensor.battery_2_voltage` / `sensor.sungold_sph302480a_battery_voltage`.

`sensor.dump_surplus_w` remains for the watt-ledger. It is **not** the dump ON
trigger (float throttles PV watts to the load).

### Victron float hold then staged ON

**Bulk / absorb:** dump stays **off**. The pack is still being served (CV ~28.4-28.8 V).

**Float:** MPPT **holds** Vfloat (~27.0-27.4 V on this plant). HA may add dumps:

1. `binary_sensor.dump_charge_float` on for 1 min (T2 MPPT `float`).
2. `binary_sensor.dump_solar_present` on (PV >= `dump_min_solar_w`).
3. That plug's bus `dump_v_float_*` on for 1 min (shunt/cart V >= float helper).
4. `dump_soc_unsynced` off **and** SoC < `dump_min_soc_percent` (95) blocks T2/KU add.
   While unsynced, skip SoC (float voltage is the full-enough gate)
   ([SmartShunt 5.7](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)).
5. `sensor.dump_next_plug` picks an **off** dump socket whose **cooldown timer is idle**,
   on a bus still in the float band, batt ok, and inverter headroom. An unavailable
   socket (bridge offline) is never picked. H5082 has no per-socket watts, so
   watts never block staging.
   Staging also waits while `dump_load_exceeds_solar` is on (that rule would shed
   the socket a minute later), and stops if `dump_control_enabled` goes off.
6. One `switch.turn_on`, then wait (up to 2 min) until the H5082 **reports on** (the
   bridge publishes on only after the plug acks over BLE; a cold link is connect +
   login + retries), then [delay](https://www.home-assistant.io/docs/scripts/#wait-for-time-to-pass-delay)
   `input_number.dump_site_confirm_s` seconds (default **5**; Sungold Modbus poll
   default is also 5 s). A socket that never reports on counts as not confirmed.
7. **Site confirm** (solar-system load, not indoor Govee energy monitoring):
   - **Sungold:** `sensor.sungold_sph302480a_load_power` must rise by >=
     `dump_site_delta_min_w` (default 25 W).
   - **T2:** signed `-sensor.battery_1_power` (more AC load => more negative pack
     power / less charge).
   - **KU:** signed `-sensor.battery_2_power`.
8. If solar-present or charge-float is already off after the delay: turn that plug
   off, start its 10 min cooldown, cancel its min-on, stop staging.
9. If **not** confirmed: turn off, start 10 min cooldown, try the next plug (do
   not stop the whole automation).
10. If **confirmed**: start that plug's 15 min min-on timer, delay 1 s, stage
    another. Confirmed plugs are **not** fail-closed for missing per-plug watts;
    they stay on until solar-gone / re-bulk / batt-not-ok / Sungold load > site solar
    (1 min shed-one) as below. PV falling does **not** immediately turn off a
    confirmed plug.

That is how leftover PV is claimed: add until voltage sags toward re-bulk or the
inverter is full -- not until a 200 W surplus helper trips. Clouds: if **Load now**
(Sungold AC-out, includes dump) stays **above Solar now**, HA sheds dump plugs one
per minute so dump tracks solar. It never switches a socket whose Use is normal. End of day
or dark storm (`dump_solar_present` off 1 min) still turns every dump socket off. After the
first float of the day, leaving absorb/float sheds **one** plug per minute instead
of all of them, so the MPPT is not forced back into a same-day float-idle cycle.

**Govee H5082 (this site's dump hardware):** same *shape* as Victron BLE, not
the same product. Victron Instant Readout is a documented advertisement;
`victron_ble2mqtt` on Pi 4 decodes it and publishes [MQTT discovery](https://www.home-assistant.io/integrations/mqtt/).
HA never speaks Victron BLE. H5082 also has no official HA plug integration
([govee_ble](https://www.home-assistant.io/integrations/govee_ble/) is sensors
only). Forums/GitHub drive it with extra software (HACS or a BLE/cloud MQTT
bridge). This repo's `govee_h5082` bridge on the Pi 4 publishes one MQTT switch
per socket (16), so HA stays on official MQTT. Confirm stays **Sungold AC-out**
(and T2/KU pack sign), not Govee energy monitoring. HACS Govee plugins are not
used for the plugs.

Default AC caps are **2000 W** per inverter (operator / Renogy 2 kW class).
Sungold nameplate is **3000 W**; raise **Sungold AC limit** only if dumps are on that
inverter and you want the higher cap. Do not set a helper above the inverter
that feeds those plugs.

SoC is **not** a dump-on gate while `dump_soc_unsynced` is on. Float voltage is
the battery-served check. After PV stops, dumps go off so overnight use is the
house/inverter, not dump plugs (95%+ leftover if the day reached float).

Turn-**off** (Victron 1 minute; per-plug 10 min cooldown after any off):

- **All dump sockets:** `dump_solar_present` off 1 min (weather / end of day) --
  every dump socket that is not already off is turned off, its min-on cancelled
  and its cooldown started. This is the 95%+ after solar stops rule.
- **One plug per minute:** `dump_load_exceeds_solar` on 1 min (Load now > Solar now)
  -- last dump socket in the stage order first (`sensor.dump_shed_plug`), cancel min-on,
  start cooldown, wait 1 min, repeat while still over.
- **One plug per minute:** T2 MPPT not absorption/float 1 min -- same shed-one
  until float returns or no dump is on.
- **That inverter only:** bus voltage <= re-bulk helper 1 min, or `dump_batt_*_ok`
  off 1 min (pack supplying the inverter) -- turn off the dump sockets on that
  inverter that are not already off (unavailable ones are sent off too), cancel
  each one's min-on, start each one's cooldown.
- **Failed site confirm:** turn off that plug only, start its 10 min cooldown
  (no min-on started).

**Text alert (10 min):** `dump_load_exceeds_solar` on for `00:10:00` sends
`notify.persistent_notification` and, if `input_text.dump_notify_service` is a
Companion action such as `mobile_app_<device>`, that notify too
([Companion notifications](https://companion.home-assistant.io/docs/notifications/notifications-basic/)).
Find the action under **Settings > Tools > Actions**. This is independent of the
dump kill switch. Trailer A/C on KU is **not** in Load now; KU overdraw still
uses `dump_batt_ku_ok` / re-bulk.

### Any load on any inverter (live meters)

You do **not** type the wattage of a heater/fan/PC you plug into T2, KU, or Sungold.
HA already has the live meters:

| Inverter | How HA sees a new AC load |
|----------|---------------------------|
| T2 Renogy | Battery 1 SmartShunt `sensor.battery_1_power` / `_current` (negative = pack supplying the load) |
| KU Renogy | Battery 2 SmartShunt `sensor.battery_2_power` / `_current` (same sign) |
| Sungold cart | `sensor.sungold_sph302480a_load_power` (AC out) and cart battery V×A |

If that bus's pack starts discharging, `dump_batt_*_ok` goes off: no new dumps on
that inverter, and existing dumps on **that** inverter turn off after 1 minute.
Sungold AC-out watts also shrink Sungold headroom immediately.

H5082 advertisements carry on/off only (no watts). There is no typed rating
helper and no per-socket power sensor; confirm is the site load delta.

Ask ALFa may **observe** shunt/Sungold/plug power and voltage (`ha_get_states` /
`ha_dump_tick`) and write float/re-bulk/AC-cap/inverter helpers immediately.
It does not invent plug watts and does not own dump on/off.

---

### Review 2026-09-28 (ported from the sim package)

- Dump actions only ever target sockets whose **Use** is dump. The sim package used
  a hardcoded list of six switches (the solar-gone all-off hit all six); pointed at
  the 16 real sockets that would have switched normal loads.
- Turn-off rules send off only to dump sockets that are not already off (fewer BLE
  commands); they no longer start cooldowns on sockets that were already off.
- Staging waits for the plug to report on before the site confirm delay; with a
  cold BLE link the 5 s confirm used to run before the plug switched.
- Staging stops when the kill switch goes off and does not start while Sungold
  load is above solar (it used to add a socket the shed rule removed a minute later).
- `input_select.h5082_<id>_<side>_inverter` has no `initial`: the old
  `dump_plug_N_inverter` reset to Sungold on every HA restart, so re-bulk and
  battery rules could watch the wrong bus.
- `sensor.dump_surplus_w` is PV watts (no plug watts to subtract); the derivative
  behind `dump_pv_falling` no longer drops when a dump turns on.
- No dump helper has `initial:` any more (16 `input_number`, `dump_soc_unsynced`,
  `dump_notify_service`). Before, tuned volts / caps / confirm / min solar / SoC floor,
  the alert service and Ignore SoC all snapped back to the package values at **every**
  HA restart (watchdog, autoheal, installs). Now HA restores the last value. The old
  values are the **recommended starting values**: Site solar > **Dump master switch** >
  **Recommended defaults** (`script.dump_load_recommended_defaults`, manual only, asks
  for confirmation) sets them once. A brand-new helper starts at its `min` (numbers),
  off (Ignore SoC) or unknown (alert service: persistent notification only) until you
  set it or press the button.
- `scripts/create_h5082_socket_labels.py` used to create the Where / Load / Use storage
  helpers with `initial` "" / "normal". For storage `input_text` / `input_select`, HA
  skips restore when `initial` is set, so labels blanked and every socket fell back to
  **normal** (no dump) at each restart. The script now creates them without `initial`
  and strips it from existing ones (`--dry-run` to preview). See
  [Site solar help: Plug names](site-solar/plug-names.md).
- Every automation switch action writes a plain reason to the logbook ("Dump control:
  ..."), shown on Site solar > **Dump activity log**; helper changes (who / what) show on
  **Dump settings change log**. Automations were renamed ("Dump ON: ...", "Dump OFF ...",
  "Dump SHED ...", "Dump ALERT ...") with the same ids. `logbook:` is enabled by the
  package (no `default_config` on .105).

---

## Site solar help (one page per dashboard box)

Each dump box on Site solar > Now has a short help card and a **Help** link:

| Box | Help page |
| --- | --- |
| Dump master switch | [dump-master-switch.md](site-solar/dump-master-switch.md) |
| Dump status (why / why not) | [dump-status.md](site-solar/dump-status.md) |
| Dump voltage (start / stop) | [dump-voltage.md](site-solar/dump-voltage.md) |
| Dump start conditions | [dump-start-conditions.md](site-solar/dump-start-conditions.md) |
| Dump confirm (wait / load rise) | [dump-confirm.md](site-solar/dump-confirm.md) |
| Inverter AC limits | [dump-inverter-limits.md](site-solar/dump-inverter-limits.md) |
| Battery discharge limits | [dump-battery-limits.md](site-solar/dump-battery-limits.md) |
| Dump alerts | [dump-alerts.md](site-solar/dump-alerts.md) |
| Dump timers (min-on / cooldown) | [dump-timers.md](site-solar/dump-timers.md) |
| Plugs | [plug-buttons.md](site-solar/plug-buttons.md) |
| Plug names (Where / Load) | [plug-names.md](site-solar/plug-names.md) |
| Socket Use (normal / dump) | [socket-use.md](site-solar/socket-use.md) |
| Socket inverter (bus) | [socket-inverter.md](site-solar/socket-inverter.md) |
| Dump activity log | [dump-activity-log.md](site-solar/dump-activity-log.md) |
| Dump settings change log | [dump-settings-log.md](site-solar/dump-settings-log.md) |
| History > Dump sockets timeline | [dump-history.md](site-solar/dump-history.md) |

Back up / restore every Site solar setting (helpers + dashboard):
`python3 scripts/site_solar_settings.py export` / `restore --from LATEST --helpers`.

---

## Enable on `.105` (one path)

Prerequisites: the 16 H5082 switches are in HA and the per-socket helpers exist
(`python3 scripts/create_h5082_socket_labels.py`, skips helpers that exist).

```bash
cd /home/ansible/victron-ble2mqtt-integration
git pull --ff-only origin main
bash scripts/install_dump_control_ha.sh
```

The script removes any retired `sim_dump_control.yaml` / `sim_dump_plugs.yaml`,
copies `dump_control.yaml` into `/opt/homeassistant/packages/`, runs
`check_config`, and restarts the `homeassistant` container
([HA Container](https://www.home-assistant.io/installation/linux#install-home-assistant-container)).
After a later dump-package change, `git pull` then rerun this script (or
`install_solar_plant_ha.sh`, which refreshes the dump file when it already
exists). A stale copy leaves helpers such as
`input_boolean.dump_soc_unsynced` / `input_number.dump_float_t2_v` missing from
`/api/states` while Energy / Helpers still expect them.

Operator dump UI is **Site solar** (`/site-solar`: **Plugs** cards with Use and
Inverter per socket, site confirm/delta helpers, **Dump dwell** per-socket 15 min
min-on / 10 min cooldown), plus **Settings > Devices & services > Helpers**.
Disable: `input_boolean.dump_control_enabled` (Dump Automations helper), or delete
the package file and restart HA. YAML Lovelace is not the daily dump control.

Default: this package is **not** on `/opt/homeassistant` until the operator runs
the install script.

---

## Related

- [H5082_INSTALL_PLAN.md](H5082_INSTALL_PLAN.md)
- [SOLAR_HA_DASHBOARD.md](SOLAR_HA_DASHBOARD.md)
- alfa-ai observe/audit only: sibling `docs/HOME_ASSISTANT_BRAIN_INTEGRATION.md`
