# H5082 bridge on more than one Pi

The Govee H5082 bridge (`govee_h5082`, unit `h5082-mqtt`) can run on the Pi 4
(`.223`) **and** the Pi 5 (`.240`). Each plug is driven by the Pi that reaches
it, and only by that Pi. First case: plug `82FB` (the fan) times out from the
Pi 4 (`GATT 82FB ... TimeoutError`, `SET_FAIL`) but the Pi 5 hears it at about
−56 dBm (see [H5082_COVERAGE_PLAN.md](H5082_COVERAGE_PLAN.md)).

**Live since 2026-09-28:** the Pi 4 owns `2F9D 3013 3EC9 9607 CF79 C061 C38D` (`hci1`)
and the Pi 5 owns `82FB` (`hci0`, RSSI −74 there vs −90 on the Pi 4). The Pi 5 now
switches `82FB` from HA. Step-by-step host list: `NEXT_STEPS.md`, section "Pi 5
H5082 bridge".

## How it works

- **Allowlist per Pi.** `H5082_PLUGS` lists the plugs that Pi owns, as the last
  4 hex digits of the MAC (`82FB`, `2F9D`, ...), separated by commas or spaces.
  It lives in `/home/n4s1/.config/h5082-bridge.env` on each Pi, **not in git**.
  An unknown id stops the bridge with an error, so a typo cannot quietly drop a
  plug. `all` owns every plug and `none` owns none.
- **A bridge ignores plugs it doesn't own.** It does not publish their switch
  config or their state, and does not act on their commands (it logs
  `NOT_OWNER <id> <side>`). It still publishes RSSI for every plug it hears, so
  **Heard by** keeps working.
- **HA stays the same.** Every Pi uses the same command, state and discovery
  topics (`govee/h5082/<mac>/<side>/set|state`,
  `homeassistant/switch/h5082_<id>_<side>/config`), so each socket stays one
  entity (`switch.ihoment_h5082_<id>_<side>`). Only the **availability** topic
  is per host: `govee/h5082/bridge/<host>/status`. If one Pi goes down, only
  its plugs show unavailable.
  No entity edits, but **reload the MQTT integration** after a bridge starts
  or a plug moves (see below). HA kept the old config until it was reloaded.
- **Claims.** Each owner publishes a retained `govee/h5082/<mac>/owner` =
  `<host>`. If two Pis list the same plug, both log
  `OWNER_CONFLICT <id> also claimed by <host>`. Fix it by removing the plug from
  one Pi's list. After you remove a plug from a Pi's list, that Pi clears its
  own old claim on the next start (`OWNER_RELEASE <id>`).
- **Without the file (or with `H5082_PLUGS` unset)** the Pi 4 works exactly as
  before: it owns all 8 plugs and uses the old availability topic
  `govee/h5082/bridge/status`. Timings (connect 20 s, ack 8 s, 3 tries, 120 s
  idle, 20 s hold) are the same in both modes. Any bridge that is not the Pi 4
  refuses to start without `H5082_PLUGS`, so a second Pi can never take every
  plug by accident.
- **Adapter.** The Pi 4 must stay on `hci1`, because `hci0` there is Victron.
  The Pi 5 unit uses `hci0` (onboard, shared with the Theengs container). You
  can change it with `H5082_ADAPTER=hciN` in the host file, for example if you
  later add a USB dongle.
- **Keys.** Each Pi keeps its own `/home/n4s1/.govee-h5082-keys` (mode 600),
  holding only the lines for the plugs it owns. You can point the bridge at
  another file with `H5082_KEY_PATH`. At start the bridge logs
  `OWNS <ids> listener=<host> adapter=<hciN> mode=...`, then `NO_KEY_OWNED <id>`
  for any owned plug with no key line, and `KEY_FILE ... mode 644, want 600` if
  the file is readable by others. Keys are never logged.

## Python packages (venv)

Both units run `/home/n4s1/govee-ble-venv/bin/python -m govee_h5082`. That venv needs
**bleak**, **paho-mqtt** and **dbus-fast**. The Pi 5 venv (made for the RSSI-only
listener) had paho-mqtt 2.1.0 and dbus-fast but **no bleak**, so the bridge died with
`ModuleNotFoundError: No module named 'bleak'`. Fix it as `n4s1`, not root:

```bash
~/govee-ble-venv/bin/pip install bleak paho-mqtt      # 2026-09-28: bleak 3.0.2
~/govee-ble-venv/bin/python -c 'import bleak, paho.mqtt, dbus_fast' && echo ok
```

`scripts/install_h5082_bridge.sh` runs that import check before it touches systemd.
If the check fails, the script stops and prints the pip command.

The bridge works with bleak 3.x (live on the Pi 5, 3.0.2) and with older bleak (the
Pi 4 venv may be older). Adapter pinning differs between them: bleak >= 3.0 takes
`bluez={"adapter": "hciN"}`, while older bleak ignores that and needs `adapter="hciN"`,
or else it uses the default adapter (`hci0`, Victron on the Pi 4). The bridge picks
the right form from the installed version and logs it at start as
`OWNS ... bleak=<version>`.

## Files

| File | What |
|---|---|
| `systemd/h5082-mqtt.service` | Pi 4 unit (`pi4`, `hci1`). Reads the optional `~/.config/h5082-bridge.env`. |
| `systemd/h5082-mqtt-pi5.service` | Pi 5 unit, installed as **`h5082-mqtt.service`** (`pi5`, `hci0`, MQTT from `hosts/pi5/mqtt.env`). The host file is required here. It replaces `h5082-rssi-pi5`, since it also publishes pi5 RSSI. |
| `scripts/install_h5082_bridge.sh --host pi4\|pi5 [--dry-run]` | Checks that the venv can import bleak / paho.mqtt / dbus_fast, then copies the unit, runs daemon-reload, enables and restarts the bridge, and creates a template host file if it is missing. It checks that the key file exists with mode 600 but never reads it. On pi5 it disables `h5082-rssi-pi5`. |
| `scripts/h5082_rssi_scan.py --adapter hciN [--seconds 30]` | Read-only scan. For each plug it prints samples, best and average RSSI, and last seen, so you can see which Pi hears it best. It never connects and never reads keys, and it refuses `hci0` on the Pi 4. |

## Host file

`/home/n4s1/.config/h5082-bridge.env` (mode 600, owner `n4s1`). It holds no
secrets, but it is per host and stays out of git:

```text
# Pi 4
H5082_PLUGS=2F9D,3013,3EC9,9607,CF79,C061,C38D
```

```text
# Pi 5
H5082_PLUGS=82FB
H5082_ADAPTER=hci0
```

## Which Pi should own a plug

Run the helper on each Pi for the same 30 s, then give the plug to the Pi with
the better **best** and **avg** values and more samples:

```bash
cd /home/n4s1/victron-ble2mqtt-integration
/home/n4s1/govee-ble-venv/bin/python scripts/h5082_rssi_scan.py --adapter hci1 --seconds 30   # Pi 4
/home/n4s1/govee-ble-venv/bin/python scripts/h5082_rssi_scan.py --adapter hci0 --seconds 30   # Pi 5
```

A plug that a bridge is connected to stops advertising until its link goes idle
(about 2 min). A plug you just switched may therefore show 0 samples. Wait
2 minutes and run it again. The **Heard by** sensors in HA give the same hint
over a longer time. They are advice only: `H5082_PLUGS` decides which Pi drives
a plug.

## Move a plug to the other Pi later

Example: move `C061` from the Pi 4 to the Pi 5.

1. **Old Pi (Pi 4):** remove `C061` from `H5082_PLUGS` in
   `~/.config/h5082-bridge.env`, then `sudo systemctl restart h5082-mqtt`. Its
   log shows `OWNS` without `C061`. HA shows the `C061` sockets unavailable
   until the new Pi takes over.
2. **New Pi (Pi 5):** copy that plug's key line by hand (see "Copy a key line"
   below, with the plug's MAC) into `~/.govee-h5082-keys` (keep mode 600). Add `C061` to
   `H5082_PLUGS`, then run `sudo systemctl restart h5082-mqtt`. Its log shows
   `OWNS ... C061` and no `NO_KEY_OWNED C061`.
3. **HA:** reload MQTT (**Settings > Devices & services > MQTT > ⋮ > Reload**). HA can
   keep the old entity config (the old Pi's availability topic) until this is done.
4. Toggle a `C061` socket in HA, then run `journalctl -u h5082-mqtt -n 30` on the
   new Pi and look for `SET C061 <side> ON|OFF`. There must be no `OWNER_CONFLICT`
   on either Pi.
5. Optional: delete the moved line from the old Pi's key file. The bridge does
   not need it there any more.

Always remove the plug from the old Pi first, so that two Pis never drive one
plug.

## Copy a key line from one Pi to the other

The Pis have no SSH key between them (scp from the Pi 5 to the Pi 4 gave
`Permission denied (publickey)`), so copy the one line by hand. Use the plug's
full MAC (`82FB` is `D4:13:68:61:82:FB`, see `PLUGS` in `govee_h5082/mqtt_bridge.py`).

**On the Pi that has the key (Pi 4):** print only that line. It shows the key on
your screen; copy it into the other Pi's file and nowhere else.

```bash
grep -i '^D4:13:68:61:82:FB ' ~/.govee-h5082-keys
```

**On the Pi that needs it (Pi 5):**

```bash
[ -f ~/.govee-h5082-keys ] || install -m 600 /dev/null ~/.govee-h5082-keys   # only if missing
nano ~/.govee-h5082-keys          # paste that one line, save
chmod 600 ~/.govee-h5082-keys
wc -l ~/.govee-h5082-keys         # one line per plug this Pi owns
```

Optional alternative, only if this Pi has an SSH key on the other Pi:

```bash
umask 077
scp n4s1@192.168.0.223:.govee-h5082-keys ~/h5082-keys.pi4.tmp
grep -i '^D4:13:68:61:82:FB ' ~/h5082-keys.pi4.tmp >> ~/.govee-h5082-keys
rm -f ~/h5082-keys.pi4.tmp
chmod 600 ~/.govee-h5082-keys
```

## After starting or changing a bridge: reload MQTT in HA

After both bridges are up, and after any plug moves, reload the MQTT integration:
**Settings > Devices & services > MQTT > ⋮ > Reload**. On 2026-09-28 HA kept the old
`82FB` entity config and sent no commands for it until this reload. No entity edits
are needed.

## Checking logs and the broker

- Use `journalctl -u h5082-mqtt -n 30` (or `-f` while you toggle), not
  `--since "-2 min"`. The Pi 5 clock/timezone was an hour off, so `--since` showed
  nothing. Optional fix: `sudo timedatectl set-timezone America/New_York`.
- To see the claims and availability on the broker from the Pi 5 (not installed
  there by default):

  ```bash
  sudo apt install -y mosquitto-clients
  cd /home/n4s1/victron-ble2mqtt-integration
  set -a; source hosts/pi5/mqtt.env; set +a     # MQTT_HOST MQTT_PORT MQTT_USERNAME MQTT_PASSWORD
  mosquitto_sub -h "$MQTT_HOST" -p "${MQTT_PORT:-1883}" -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" \
    -t 'govee/h5082/+/owner' -t 'govee/h5082/bridge/+/status' -v -W 5
  ```

## Known limits

- The Pi 5 `hci0` is also scanned by Theengs. BlueZ merges scans from several
  clients, but on the Pi 5 onboard (Broadcom) radio, scanning while connecting
  can abort a connect. The bridge retries 3 times. If `82FB` still logs
  `SET_FAIL` from the Pi 5, use a USB dongle as `hci1` and set
  `H5082_ADAPTER=hci1`.
- Never list the same plug on both Pis. The claim topic warns you when it
  happens, but it does not stop a Pi.
- The old retained `govee/h5082/bridge/status` value (`offline`) stays on the
  broker once the Pi 4 has an allowlist. Nothing uses it any more.
