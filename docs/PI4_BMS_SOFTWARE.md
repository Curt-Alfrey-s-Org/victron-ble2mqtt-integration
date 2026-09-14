# Pi battery supervisor (BMS software)

**Status:** Phase 1+2 implemented (12 Sep 2026). Code in `bms_supervisor/`; **default off** (`ENABLE_BMS_SUPERVISOR=0`). **Not** a replacement for any pack's internal BMS.

The Raspberry Pi 4 at **`.223`** is the Victron BLE radio for this repo ([DEVICES.md](DEVICES.md), alfa-ai [PI4_VICTRON_OPERATOR.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/PI4_VICTRON_OPERATOR.md)). The same sidecar may run on **Pi 5** (`.240`) when a house-bank VE.Direct USB cable is plugged there. Any supervisor process must **coexist** with `victron_ble2mqtt` (Bluetooth on, Instant Readout ads). It must not steal GPIO 14/15 (Bluetooth UART on Pi 4).

This chapter is **not** a 48 V island BOM and **not** a T2/KU cutover. Island math stays in [SOLAR_ARRAY_SOLARK.md](SOLAR_ARRAY_SOLARK.md). Live 24 V plant stays in [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md).

## 1. Goal and non-goals

**Goal:** operator-owned software on a Pi that **observes** battery banks you actually install (LiTime, Discover AES, or a generic shunt bank), estimates SoC from **published** meters, logs, and publishes MQTT next to Victron -- so Home Assistant can show voltage, current, SoC, and alarms.

**Non-goals**

| Do not | Why |
|--------|-----|
| Replace the pack BMS | LiTime 200 A BMS and Discover GEN-4 BMS stay in series with the cells. Bypassing AES BMS voids warranty ([IOM](https://discoverenergysys.com/s4x_files/resources/des-aes-rackmount-user-manual.pdf) 10 / 885-0043 exclusion 18). |
| Drive pack FETs / cell tap / raw UART to cells | **Official silent** on LiTime host protocol (see section 8). Do not reverse-engineer. |
| Mix AES + LiTime on one DC bus | Discover IOM 9.7 same-model only; Sol-Ark "do not mix" makes; LiTime identical packs only. |
| Cut over T2/KU into the 48 V island | [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md) is unchanged. |
| Auto-disconnect or auto-cap inverter charge on v1 | Observe/log default (L1). Any actuation is L2 (section 6). |
| Production well / server island on v1 | Phase 0-2 are bench / spare pack. |
| Clone LYNK AEBus on GPIO | Discover LYNK RJ45 is a battery network; IOM 9.8: **isolate** it; do not mix other networks. |
| Ask ALFa / cluster start-stop | This is operator BMS software on Pi, not the alfa-ai catalog. |

## 2. Architecture

One **optional** sidecar process, same pattern as Sungold: distinct MQTT topic root, Home Assistant discovery, **read-only** until a later approved phase. Victron BLE stays the primary Pi4 workload.

```
Pack internal BMS (always in circuit)
        |
   battery +/-  ----  inverter / chargers
        |
   external shunt + voltage sense   (never GPIO into 25.6 / 51.2 V)
        |
   isolated USB / BLE / (future) CAN
        |
Pi4 .223  or  Pi5 .240 (if house VE.Direct USB)
  victron_ble2mqtt     -- existing BLE Instant Readout (Pi4 only; do not stop)
  sungold_modbus_ro    -- optional USB, ENABLE_SUNGOLD, already isolated
  bms_supervisor       -- NEW, default off, own topic root
        |
Mosquitto :1883  -->  Home Assistant
```

**Adapters (one family per process instance -- do not merge banks):**

| Adapter | When | Official path |
|---------|------|----------------|
| `litime_shunt` | LiTime 24 V 230 Ah (no Bluetooth) | Product FAQ: use a [500 A battery monitor with shunt](https://www.litime.com/products/litime-500a-battery-monitor-with-shunt). Prefer a **Victron SmartShunt** already in this stack ([SmartShunt interfacing](https://www.victronenergy.com/media/pg/SmartShunt/en/interfacing.html), [VE.Direct protocol 3.34](https://www.victronenergy.com/upload/documents/VE.Direct-Protocol-3.34.pdf)). |
| `aes_lynk_observe` | AES 48-48-5120 closed-loop to Sol-Ark | Inverter closed-loop stays **LYNK II 950-0025**. Pi does **not** join the LYNK RJ45 network. Optional later: Discover [Serial CAN technical reference](https://discoverenergysys.com/s4x_files/resources/lynk-serial-can-interface-technical-reference.pdf) as a **monitor** -- only if Discover/Sol-Ark confirm a Pi may share that CAN with the inverter. Until then, observe AES with an **external shunt**. |
| `generic_shunt` | Any other identical-pack bank | Isolated shunt + voltage; same data model. |

Do not run `litime_shunt` and `aes_lynk_observe` against packs paralleled together.

v1: all three adapters use the **same** VE.Direct USB read path. `BMS_ADAPTER` only changes MQTT identity / HA device manufacturer+model strings.

## 3. Hardware (Pi electrical limits)

Raspberry Pi 4 GPIO is **3.3 V** logic. Official [Raspberry Pi 4 Model B datasheet](https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-datasheet.pdf) (Release 1.1, March 2024):

- VDD_IO = on-board **3.3 V** rail.
- VIH 2.0 V to VDD_IO; VIL 0-0.8 V.
- Default drive ~2 mA class; max drive **7 mA** IOL/IOH at the tabulated voltages (Table 3). Do not treat GPIO as a 48 V ADC.
- 28 GPIOs on the 40-pin header; UART/I2C/SPI are **muxed** (Table 5). GPIO 14/15 are TXD0/RXD0 (ALT0) and TXD1/RXD1 (ALT5) -- the usual Bluetooth / console UART pair.
- USB-C supply **5 V / 3 A** (2.5 A if downstream USB < 500 mA). Downstream USB aggregate ~**1.1 A**.
- Ambient 0-50 C.

**Isolation (mandatory)**

- **Never** share battery negative with Pi GND through a raw divider unless a listed isolated transducer is used. Victron [VE.Direct FAQ](https://www.victronenergy.com/live/vedirect_protocol:faq): TX/RX go almost directly into the product UART; **use VE.Direct to USB (or VE.Direct to RS232)** because those include **galvanic isolation**. Direct GPIO UART to a shunt or inverter is not that path.
- Cable: Victron **ASS030530000** VE.Direct to USB. Linux FTDI **0403:6015** ([venus issue](https://github.com/victronenergy/venus/issues/4)). Prefer `/dev/serial/by-id/`; udev symlink `/dev/vedirect`.
- LiTime 500 A LCD monitor: shielded wire is **display-only** in the published spec. No Pi host protocol is documented -- do not splice that cable onto GPIO.
- AES LYNK RJ45: IOM 9.8 isolate the LYNK network; mixing networks can damage equipment.
- Shunt class: LiTime 200 A continuous (2S still 200 A). Victron SmartShunt 300/500 A class, or LiTime 500 A shunt, must exceed expected current. Wire as Victron [installation](https://www.victronenergy.com/media/pg/SmartShunt/en/installation.html): all negatives through **one** shunt (BATTERY MINUS vs SYSTEM MINUS). Two shunts plus a jumper will not show pack-to-pack current ([SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md)).
- Voltage sense: use the shunt's voltage leads or an isolated voltage transducer rated for 24 V or 48 V. Official docs are **silent** on a homemade resistor divider into GPIO ADC (Pi 4 has no general-purpose ADC on the header in the datasheet). Do not invent one.

**Coexistence with Victron BLE**

- Keep `victron_ble2mqtt` running on Pi4. Close VictronConnect on phones while testing ads ([README](../README.md)).
- Use **USB** VE.Direct (isolated) for the supervisor shunt -- not `enable_uart=1` on GPIO 14/15 (that fights Bluetooth on Pi 4).
- Pi5: optional house-bank VE.Direct USB only; does not run Victron BLE or a second HA.

## 4. Data model

Publish SI units. Home Assistant MQTT sensor fields per [sensor.mqtt](https://www.home-assistant.io/integrations/sensor.mqtt/): `state_topic`, `unique_id`, `device`, `device_class`, `state_class`, `unit_of_measurement`.

| Key | Unit | device_class | Notes |
|-----|------|--------------|--------|
| `voltage` | V | `voltage` | Pack or bank |
| `current` | A | `current` | Sign: Victron SmartShunt positive = charge ([operation](https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html)) |
| `power` | W | `power` | V * I if the meter does not send P |
| `soc` | % | `battery` | From shunt coulomb count or LYNK -- **not** lead-acid voltage SoC (AES IOM 10.2) |
| `consumed_ah` | Ah | | If the meter provides it (VE.Direct `CE`) |
| `temperature` | C | `temperature` | Only if `T` present in block (BMV temp accessory). Omitted from HA when absent. |
| `alarm` | binary | | Undervoltage, overcurrent, comms lost -- from meter flags, not invented BMS bits |

SoC estimate without a shunt: **official silent** for LiTime. Do not ship a voltage-only SoC for LiFePO4 as "BMS software."

## 5. MQTT topics (house pattern)

Victron uses HA discovery (`homeassistant/#`) via `ha_services.mqtt4homeassistant`. Sungold sidecar uses a **distinct** root `MQTT_TOPIC=sungold_sph302480a` ([SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md)). Supervisor must **not** reuse Victron or Sungold roots.

| Piece | Value |
|-------|--------|
| State root | `bms_supervisor/{adapter}/{key}/state` |
| Discovery | `homeassistant/sensor/bms_supervisor-{adapter}-{key}/config` (binary_sensor for alarm) |
| Availability | `bms_supervisor/{adapter}/status` payloads `online` / `offline` ([MQTT](https://www.home-assistant.io/integrations/mqtt/)) |
| Device `identifiers` | `[bms_supervisor, adapter, bank_id]` |
| Env topic root | `BMS_MQTT_TOPIC=bms_supervisor` |
| Same broker | Existing `MQTT_HOST` / `MQTT_USER` / `MQTT_PASSWORD` |
| Writes | None on v1 (no `number` / `switch` discovery for charge caps) |

### Container health (heartbeat)

Compose [healthcheck](https://docs.docker.com/reference/compose-file/services/#healthcheck) watches `HEARTBEAT_FILE` (max age **180s**). The sidecar touches that file only after a VE.Direct Text frame parsed **and** at least one curated MQTT **state** publish completed ([Paho `Client.publish`](https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html#paho.mqtt.client.Client.publish): `is_connected()`, `rc == MQTT_ERR_SUCCESS`, then [`wait_for_publish`](https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html#paho.mqtt.client.MQTTMessageInfo.wait_for_publish) / [`is_published`](https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html#paho.mqtt.client.MQTTMessageInfo.is_published) with `loop_start()` running). USB frames with the broker down do not keep the container `healthy`. Label `autoheal: "true"` so autoheal can restart an unhealthy sidecar ([autoheal entrypoint](https://github.com/willfarrell/docker-autoheal/blob/master/docker-entrypoint)). Do not add HA `expire_after` on these sensors ([MQTT sensor](https://www.home-assistant.io/integrations/sensor.mqtt/)).

Phase 3 charge-current **request** (if ever) is a documented inverter API only -- Sol-Ark closed-loop is LYNK, not this process. Official silent on a Pi writing Sol-Ark registers. Stop and ask.

## 6. Oversight

This is **operator** software on Pi, not Ask ALFa. The autonomy labels match alfa-ai [AI_AUTONOMY_AND_OVERSIGHT.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/AI_AUTONOMY_AND_OVERSIGHT.md):

| Action | Level | Default |
|--------|-------|---------|
| Read shunt / VE.Direct / BLE; log; MQTT sensors | **L1** observe | On when the sidecar is enabled |
| Disconnect contactor, charge-inhibit GPIO, inverter current cap | **L2** | Off. Human Approve each time. Show the exact command / register before acting. |
| Silent auto-fix / cell FET control | Forbidden | Never |

v1 implements L1 only. No GPIO outputs to contactors. Parser is **Text-mode only**; never sends HEX (`:`) frames to serial ([VE.Direct protocol 3.34](https://www.victronenergy.com/upload/documents/VE.Direct-Protocol-3.34.pdf)).

## 7. Phased plan

| Phase | What | Production island? |
|-------|------|--------------------|
| **0** | This chapter + bench wiring diagram (isolated USB shunt, spare pack). | No |
| **1** | VE.Direct Text parser (`vedirect_text.py`), checksum per [FAQ Q8](https://www.victronenergy.com/live/vedirect_protocol:faq), unit conversions. Not-available placeholders (`---` for missing temp sensor, unsynced BMV SOC/CE, or DC-monitor fields per [protocol 3.34](https://www.victronenergy.com/upload/documents/VE.Direct-Protocol-3.34.pdf) footnotes 8/10/11) are omitted from metrics -- not a parse crash. Bench spare pack only. | No |
| **2** | MQTT sidecar (`bms_supervisor/`), `ENABLE_BMS_SUPERVISOR=0` default, Compose + udev + deploy hooks. HA discovery. | No |
| **3** | Optional inverter **current cap request**, L2 only, after the inverter vendor documents the write path. Not Sol-Ark CAN tap unless manuals allow it. | Still not well/server v1 |

## 8. Enable (bench / spare pack first)

1. Wire an isolated **Victron SmartShunt** (or compatible VE.Direct shunt) to a **spare** pack -- not T2/KU or live 48 V well island.
2. Plug **ASS030530000** VE.Direct-to-USB into the Pi (Pi4 solar site or Pi5 if house bank).
3. In `.env`:

```text
ENABLE_BMS_SUPERVISOR=1
BMS_SERIAL_DEVICE=/dev/vedirect
BMS_ADAPTER=generic_shunt
BMS_BANK_ID=bench
BMS_MQTT_TOPIC=bms_supervisor
BMS_DEVICE_NAME=Bench shunt
```

4. Deploy:

```bash
sudo bash scripts/deploy.sh
```

Deploy installs `udev/99-vedirect-usb.rules` (`/dev/vedirect`, FTDI 0403:6015). If the cable is not plugged in, deploy prints a message and skips the container (does not fail the whole deploy).

5. Smoke:

```bash
bash scripts/bms_supervisor_smoke.sh
docker logs -f bms_supervisor
```

**Pi4 vs Pi5:** Pi4 runs Victron BLE + optional Sungold + optional BMS (extra USB). Pi5 runs AdGuard + Theengs; set `ENABLE_BMS_SUPERVISOR=1` only when a house VE.Direct USB is present. `MQTT_HOST` on Pi5 stays the `.105` broker -- no second HA.

Manual Compose (without full deploy):

```bash
docker compose -f docker-compose.bms-supervisor.yml up -d --build
```

## 9. Official-silent list (operator can answer)

Stop here rather than inventing protocols.

1. **LiTime 24 V 230 Ah host BMS map** (UART, RS485, CAN, Bluetooth GATT). Product page: no Bluetooth; use a 500 A shunt monitor.
2. **LiTime 500 A LCD monitor** host protocol (shielded wire to LCD only in the published spec).
3. **LiTime 500 A Bluetooth shunt** third-party BLE map (app exists; no GATT document found).
4. **Pi GPIO analog frontend** for 25.6 / 51.2 V (no ADC in the Pi 4 datasheet header section; no official divider).
5. **Tapping AES LYNK RJ45 / AEBus** from the Pi (IOM: isolate LYNK).
6. **Sharing Sol-Ark closed-loop CAN** with a hobby CAN adapter while LYNK II is the inverter gateway.
7. **Discover LYNK II street price** (list SKU 950-0025 only).
8. **Raspberry Pi OS UART overlay steps** on [configuration.html](https://www.raspberrypi.com/documentation/computers/configuration.html) -- use the [Pi 4 datasheet](https://datasheets.raspberrypi.com/rpi4/raspberry-pi-4-datasheet.pdf) mux table before enabling extra UARTs.
9. **Sol-Ark register write** from Pi to cap charge current (Phase 3). Closed-loop current limit is LYNK/BMS, not a hobby Modbus map unless Sol-Ark publishes one.

## Related

- [DEVICES.md](DEVICES.md) -- live Victron / Sungold / BMS catalog
- [SOLAR_ARRAY_SOLARK.md](SOLAR_ARRAY_SOLARK.md) -- 48 V island planning; AES vs LiTime comparison
- [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md) -- 24 V T2/KU (do not mix)
- [SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md) -- read-only MQTT sidecar pattern
- [PI5_HOUSE_EDGE.md](PI5_HOUSE_EDGE.md) -- Pi5 optional BMS USB
- alfa-ai [PI4_VICTRON_OPERATOR.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/PI4_VICTRON_OPERATOR.md)
- alfa-ai [AI_AUTONOMY_AND_OVERSIGHT.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/AI_AUTONOMY_AND_OVERSIGHT.md) -- L1/L2 vocabulary only
