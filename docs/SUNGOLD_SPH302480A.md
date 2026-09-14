# Sungold SPH302480A — read-only Modbus → MQTT → Home Assistant

**Most people:** plug the USB cable, set `ENABLE_SUNGOLD=1` in `.env`, run `sudo bash scripts/deploy.sh`. On/off and how this fits next to Victron: **[DEVICES.md](DEVICES.md#sungold-inverter)**. First install: **[README](../README.md)**.

Sibling sidecar to **victron_ble2mqtt**. Publishes **sensors and binary_sensors only** — no HA controls, no Modbus writes. Change inverter settings on the **front panel** only.

## Hardware

**This site:** the SPH302480A sits on a **dolly cart** with **2x LiTime 24 V 100 Ah** in parallel (emergency backup). It is **not** wired into the T2/KU trailer buses. Trailer layout: [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md).

| Item | Value |
|------|--------|
| Model | Sungold **SPH302480A** (SRNE-class hybrid) |
| Link | USB-B → Pi (CH340 serial, vendor **1a86**) |
| Modbus | RTU **9600 8N1**, slave address **1** |
| Phase | Single-phase **120 V**, one MPPT |

## Architecture

```
SPH302480A (USB) → sungold_modbus_ro → Mosquitto (:1883) → Home Assistant
Victron BLE      → victron_ble2mqtt  → Mosquitto (:1883) → Home Assistant
```

- Victron stack is **unchanged**.
- Discovery prefix: `homeassistant/sensor/sungold_sph302480a-*` (and `binary_sensor`).
- MQTT topic root: `MQTT_TOPIC=sungold_sph302480a` (distinct from Victron).

## Operator setup (Pi4)

### 1. Plug USB

Connect the inverter **USB-B** cable to the Pi. Confirm CH340:

```bash
lsusb | grep -i '1a86\|ch340\|qinheng'
ls -l /dev/serial/by-id/
```

Typical by-id path (example — yours may differ):

```text
/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0
```

### 2. Udev stable symlink

```bash
sudo cp udev/99-sungold-ch340.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=tty
ls -l /dev/sungold
```

Or re-run **`sudo bash scripts/deploy.sh`** with `ENABLE_SUNGOLD=1` (installs the rule automatically).

### 3. Configure `.env`

Add to `.env` (see `dotenv.sample`):

```bash
ENABLE_SUNGOLD=1
SUNGOLD_SERIAL_DEVICE=/dev/sungold
# Or the full by-id path:
# SUNGOLD_SERIAL_DEVICE=/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0
MQTT_TOPIC=sungold_sph302480a
DEVICE_NAME=Sungold SPH302480A
MODBUS_ADDRESS=1
POLL_INTERVAL_SEC=5
MODBUS_TIMEOUT=1.0
```

Uses the same **`MQTT_HOST` / `MQTT_USER` / `MQTT_PASSWORD`** as Victron and Home Assistant.

### 4. Deploy

```bash
sudo bash scripts/deploy.sh
# Or stack only:
docker compose -f docker-compose.sungold.yml up -d --build
```

Dockge: stack appears as **`sungold`** under `/opt/stacks/sungold` when `ENABLE_DOCKGE=1`.

### 5. Verify

```bash
bash scripts/sungold_smoke.sh
```

Manual checks:

```bash
docker logs -f sungold_modbus_ro
mosquitto_sub -h "$MQTT_HOST" -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" \
  -t 'sungold_sph302480a/sensor/+/state' -v
mosquitto_sub -h "$MQTT_HOST" -p 1883 -u "$MQTT_USER" -P "$MQTT_PASSWORD" \
  -t 'homeassistant/sensor/sungold_sph302480a-+/config' -C 3 -W 5
```

In Home Assistant: **Settings → Devices & services → MQTT** — device **Sungold SPH302480A** with PV, battery, grid, load, and temperature entities.

**Solar dashboard:** HA [label](https://www.home-assistant.io/docs/organizing/labels/) **Sungold** (`sungold`) on that device and its MQTT entities, plus a **Sungold** [sections](https://www.home-assistant.io/dashboards/sections/) heading on sidebar **Solar** (one [tile](https://www.home-assistant.io/dashboards/tile/) per entity). Tiles bind **live** `entity_id`s from MQTT `unique_id` `sungold_sph302480a-*` and set `name: {type: entity}` so the card shows **PV input voltage**, not `Sungold S...` ([card naming](https://www.home-assistant.io/dashboards/naming/)). The cart stays off T2/KU.

Order: sidecar must already have republished discovery while HA is **running**, then stop HA and apply:

```bash
sudo python3 scripts/ha_label_sungold_solar.py
```

Then start the `homeassistant` container and wait for `:8123` ([container common tasks](https://www.home-assistant.io/common-tasks/container/), alfa-ai `wait-http.sh`).

## Published entities (curated)

HA MQTT `name` strings follow the SPH302480A **LCD real-time pages** and **fault table**, not SRNE nicknames. MQTT `unique_id` is `{mqtt_topic}-{key with / as -}` (for example `sungold_sph302480a-pv1-voltage`). Changing a **display name** keeps the same `unique_id`. Changing a **register key** (for example `pv/voltage` → `pv1/voltage`) is a new `unique_id`; Lovelace must be rewritten from the live registry.

Official: [SunGoldPower SPH302480A product page](https://sungoldpower.com/products/3000w-24v-solar-inverter-charger) (user manual download: LCD §4.1, fault codes §6.2). Same LCD wording in the 2023-11-28 reprint: [3000W_SPH302480A_20231128.pdf](https://www.solaris-shop.com/content/3000W_SPH302480A_20231128.pdf). Product page also states **high frequency transformer-less** and **PV Charging Current** as the 0–80 A rating (LCD field is `PV OUTPUT A`).

| HA name | Official source |
|---------|-----------------|
| PV input voltage | LCD `PV INPUT V` |
| PV output current | LCD `PV OUTPUT A` (PV output current) |
| PV output power | LCD `PV OUTPUT KW` |
| Remaining battery | LCD battery bars ("remaining battery") |
| Battery input voltage | LCD `INPUT BATT V` |
| Input battery current | LCD `INPUT BATT A` |
| Battery temperature | Not an LCD page; SRNE holding register (keep as diagnostic) |
| Charge state | CHARGE LED (charging / charging completed) plus setup boost / constant-voltage / floating; Modbus integers are SRNE-class, not printed in the SPH manual |
| Battery input power | LCD `INPUT BATT KW` |
| Output mode | AC/INV LED: Mains output / Inverter output. LCD does not name Initialization / Standby; unknown codes publish as the raw integer |
| Inverter error flags | Not an LCD page; SRNE diagnostic |
| Fault code | LCD middle + §6.2 `【01】`… including BMS `【30】`–`【64】` |
| Fault state | FAULT LED "Fault state" |
| AC input voltage | LCD `AC INPUT V` (manual: Mains / AC input, not "grid") |
| AC input current | Not a numbered LCD page; named to match `AC INPUT V` / `Hz` |
| AC input frequency | LCD `AC INPUT Hz` |
| Output load voltage | LCD `OUTPUT LOAD V` |
| AC output frequency | LCD `AC OUTPUT LOAD Hz` |
| AC output load current | LCD `AC OUTPUT LOAD A` |
| Load active power | LCD `INV OUTPUT LOAD KW` |
| PV charger heatsink temperature | LCD `PV TEMP` |
| Inverter heat sink temperature | LCD `INV TEMP` / §6.2 "Inverter heat sink" |

Not published for this model (manual + this hardware):

- **PV total power** — one PV port / one MPPT (`PV+` / `PV-` only).
- **Grid power** — SPH302480A rejected holding register `0x023A` (illegal data address).
- **Transformer temperature** — product is **high frequency transformer-less**.
- LCD pages **OUTPUT BATT A / KW** and **OUTPUT LOAD KVA** — no verified Modbus address in the SPH manual (manual does not publish a map).

Slave **illegal request** (unsupported address) still **skips** that register for `MODBUS_SKIP_RETRY_INTERVAL` ([IllegalRequestError](https://minimalmodbus.readthedocs.io/en/stable/apiminimalmodbus.html#minimalmodbus.IllegalRequestError)). USB timeouts (`NoResponseError` / "no communication with the instrument") do **not** skip: every curated register is polled again on the next cycle so a brief USB drop does not blank half the Solar tiles for an hour. Skip does **not** publish an empty MQTT discovery payload. Home Assistant [removes the entity](https://www.home-assistant.io/integrations/mqtt/#discovery-messages) when the discovery topic is an empty retained string; that is used only for `RETIRED_DISCOVERY`. Last Modbus values are published with MQTT **retain** so an HA restart keeps the last reading until the next poll.

Sidecar-only rebuild on Pi4 (do **not** run full `scripts/deploy.sh` for this; that compose file can rewrite Mosquitto):

```bash
sudo docker compose -f docker-compose.sungold.yml up -d --build
```

Do not pass `--remove-orphans`.

## Troubleshooting

| Symptom | Action |
|---------|--------|
| Deploy skips Sungold | Set `ENABLE_SUNGOLD=1`; confirm `/dev/sungold` or `SUNGOLD_SERIAL_DEVICE` exists |
| Container unhealthy | No heartbeat because Modbus is not answering — check inverter power, USB-B, address, baud; `docker logs sungold_modbus_ro`. Solar tiles should stay **Unavailable**, not **Entity not found**. |
| Solar tiles **Entity not found** | Lovelace still points at retired `entity_id`s, or empty discovery deleted the MQTT entities. Recreate the sidecar, wait until HA has the `sungold_sph302480a-*` unique_ids, then re-run `ha_label_sungold_solar.py` with HA stopped. |
| No HA entities | Confirm HA MQTT integration uses same broker; check discovery topics with `mosquitto_sub` |
| Permission denied on serial | User in `dialout` group; udev rule sets `GROUP=dialout` |

## Out of scope

- HA write controls (switch/number/select/button).
- SolarAssistant / Voltronic PI30 path.
- Changes to Victron BLE or ADVKEY configuration.

## Reference

Register map derived from [timbit123/srne-modbus](https://github.com/timbit123/srne-modbus) (Apache-2.0). This repo ships a **thin read-only** subset, not a full upstream clone.
