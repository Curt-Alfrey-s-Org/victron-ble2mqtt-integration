# Next steps — victron-ble2mqtt-integration

## Next step: host steps for "Solar tab -> Site solar" (plan, 2026-09-28)

From branch `site-solar-merge-solar-tab` (from main `018d780`, after #12). You asked to add every card from the sidebar **Solar** tab to **Site solar**, but only the ones that are not already there. The Solar tab (`/dashboard-solar`) exists only in the live HA, not in git, so this PR is the plan plus the tools:
- a read-only export (`site_solar_settings.py export-dashboard`);
- a compare-by-entities tool that can append only the missing cards as a new **Solar tab** view (`compare_solar_tab.py`).

The Site solar seed is unchanged, so merging changes nothing live. Plan and comparison table: `docs/SOLAR_TAB_MERGE_PLAN.md`.

Only `.105` (Home Assistant) is involved: Pi 4 `.223` and Pi 5 `.240` have nothing to do. Merging this PR changes nothing live, because the Site solar seed is untouched. HA must be up for every step that uses the token, so each phase waits for it first.

**Phase 1: export the Solar tab (after this PR is merged), on `.105`, in this order**

- [ ] **a.** `cd /home/ansible/victron-ble2mqtt-integration && git pull --ff-only origin main`
- [ ] **b.** Token file for the scripts (never commit it):
  `install -m 600 /dev/null ~/.ha_token && nano ~/.ha_token` (paste a long-lived HA token), then
  `export HA_TOKEN_FILE=~/.ha_token HA_URL=http://127.0.0.1:8123`
- [ ] **c.** Wait for HA: `until curl -s -o /dev/null http://127.0.0.1:8123; do sleep 5; done`
- [ ] **d.** Backup first: `python3 scripts/site_solar_settings.py export` (helper values + live Site solar, under `.backups/site-solar/`).
- [ ] **e.** Export the Solar tab (read-only; writes only `config/dashboards/exports/solar-tab.json`): `python3 scripts/site_solar_settings.py export-dashboard`.
  - If it prints `no dashboard with url_path 'dashboard-solar'`, it lists every dashboard. Rerun with the one titled Solar: `--url-path <that url_path>`.
  - Check any `redacted a token-like value at ...` lines. Values like that are replaced with `<redacted>`.
- [ ] **f.** Look at the comparison (read-only): `python3 scripts/compare_solar_tab.py config/dashboards/exports/solar-tab.json --markdown /tmp/solar-tab-table.md`
- [ ] **g.** Bring the export to the next session. It holds only card config: entity ids and headings, with no secrets. Either:
  - commit it on a branch from `.105`, if `.105` can push: `git checkout -b solar-tab-export && git add config/dashboards/exports/solar-tab.json && git commit -m "Solar tab export" && git push -u origin solar-tab-export && git checkout main`; or
  - `cat config/dashboards/exports/solar-tab.json` and paste it into the session.
  Then delete the local copy, so a later `git pull` that adds the same file does not stop on an untracked file: `rm config/dashboards/exports/solar-tab.json`.
- [ ] **h.** `rm ~/.ha_token && unset HA_TOKEN_FILE`

**Phase 2: add the missing cards (next session), then on `.105`**

In the session: `python3 scripts/compare_solar_tab.py config/dashboards/exports/solar-tab.json --apply` appends one new view, **Solar tab** (`/site-solar/solar-tab`), with only the missing cards. Then review each `no-entities` / `needs-decision` row, update the table in `docs/SOLAR_TAB_MERGE_PLAN.md`, run the tests, and update the PR. After it is merged:

- [ ] **a.** `cd /home/ansible/victron-ble2mqtt-integration && git pull --ff-only origin main` (if it stops on `config/dashboards/exports/solar-tab.json`, run `rm config/dashboards/exports/solar-tab.json` and pull again)
- [ ] **b.** `install -m 600 /dev/null ~/.ha_token && nano ~/.ha_token`, then `export HA_TOKEN_FILE=~/.ha_token HA_URL=http://127.0.0.1:8123`
- [ ] **c.** `until curl -s -o /dev/null http://127.0.0.1:8123; do sleep 5; done`
- [ ] **d.** `python3 scripts/site_solar_settings.py export` (backup of helpers + live Site solar)
- [ ] **e.** `python3 scripts/save_solar_plant_storage_dashboard.py --dry-run`, then `python3 scripts/save_solar_plant_storage_dashboard.py --force`. `--force` backs up the live dashboard first, then replaces it with the seed. Any Site solar UI edits made since the last seed are replaced too. Undo: `python3 scripts/site_solar_settings.py restore --from <folder> --dashboard`.
- [ ] **f.** `rm ~/.ha_token && unset HA_TOKEN_FILE`
- [ ] **g.** Check Site solar > **Solar tab**: every card from the old Solar tab is now either there or already elsewhere on Site solar (see the table). Now and History are unchanged.
- [ ] **h.** Your decision, no rush: **keep, hide or remove the old Solar tab.**
  - **Keep:** nothing to do.
  - **Hide:** Settings > Dashboards > Solar, turn off **Show in sidebar**.
  - **Remove:** Settings > Dashboards > Solar > Delete. Only do this after the Phase 1 export is committed. Also, `scripts/ha_label_sungold_solar.py` and `scripts/ha_label_victron_refoss.py` still write sections into that dashboard (`lovelace.dashboard_solar`) and fail if it is gone, so removing it needs a small follow-up change to those scripts first.

## Next step: host steps for "Pi 5 H5082 bridge" (2026-09-28)

From branch `pi5-h5082-bridge` (from main `90c762e`, merged with main after #10; independent of the dump manual hold). Plug `82FB` (the fan) fails from the Pi 4 (`GATT 82FB left ON try 1..3/3 TimeoutError`, then `SET_FAIL`). The Pi 5 hears it best. Now each Pi runs the bridge only for the plugs in its own allowlist, `H5082_PLUGS` in `/home/n4s1/.config/h5082-bridge.env` (outside git). A bridge ignores commands for plugs it does not own (`NOT_OWNER`) and publishes availability per host (`govee/h5082/bridge/<host>/status`). HA's command, state and discovery topics are unchanged. With no allowlist the Pi 4 behaves exactly as before. Plug timings did not change. Details: `docs/H5082_MULTI_BRIDGE.md`.

Hosts: Pi 4 `.223` (`n4s1@pi4`) and Pi 5 `.240` (`n4s1@raspberrypi`), both at `/home/n4s1/victron-ble2mqtt-integration`; Home Assistant on `.105`. Do the Pi 4 first, so no plug ever has two owners. `82FB` shows unavailable in HA from the Pi 4 restart until the Pi 5 bridge is up and HA's MQTT integration is reloaded. That is expected. Use `journalctl ... -n 30` instead of `--since`: the Pi 5 clock/timezone was an hour off, so `--since "-2 min"` showed nothing.

**Done live 2026-09-28** (with PR head `83e2b07`): Pi 4 owns `2F9D 3013 3EC9 9607 CF79 C061 C38D` (hci1). Pi 5 owns `82FB` (hci0) and switches it from HA. RSSI for `82FB` was pi5 −74 vs pi4 −90.

**Pi 4 `.223`** (keeps 7 plugs on `hci1`, stops handling `82FB`)

- [x] **1.** `cd /home/n4s1/victron-ble2mqtt-integration && git pull --ff-only origin main` (use `git pull` on the branch until PR #11 is merged)
- [x] **2.** Host allowlist (not secret, not in git):
  `mkdir -p ~/.config && install -m 600 /dev/null ~/.config/h5082-bridge.env && echo 'H5082_PLUGS=2F9D,3013,3EC9,9607,CF79,C061,C38D' > ~/.config/h5082-bridge.env`
- [x] **3.** `sudo bash scripts/install_h5082_bridge.sh --host pi4`. This installs the unit (it adds the optional `EnvironmentFile=-/home/n4s1/.config/h5082-bridge.env`), runs daemon-reload, and restarts `h5082-mqtt`. Add `--dry-run` first to see the commands. The script now stops first if `~/govee-ble-venv` cannot `import bleak, paho.mqtt, dbus_fast`.
- [x] **4.** `journalctl -u h5082-mqtt -n 30`. Expect `OWNS 2F9D 3013 3EC9 9607 CF79 C061 C38D listener=pi4 adapter=hci1 mode=per-host` (no `82FB`) and `DISCOVERY 8 listener=pi4`, and no `KEY_FILE` warning (`ls -l ~/.govee-h5082-keys` should show `-rw-------`).

**Pi 5 `.240`** (owns `82FB` on `hci0`)

- [x] **1.** `cd /home/n4s1/victron-ble2mqtt-integration && git pull --ff-only origin main`
- [x] **2.** Check the venv, MQTT file and adapter:
  - `~/govee-ble-venv/bin/python -c 'import bleak, paho.mqtt, dbus_fast'`. On 2026-09-28 this failed with `ModuleNotFoundError: No module named 'bleak'`: the venv had paho-mqtt 2.1.0 and dbus-fast only. Fix it as `n4s1` (not root): `~/govee-ble-venv/bin/pip install bleak paho-mqtt`. That installed bleak 3.0.2.
  - `ls -l hosts/pi5/mqtt.env`: the MQTT login (gitignored), with `MQTT_HOST`, `MQTT_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`.
  - `bluetoothctl list` or `hciconfig -a`: the onboard adapter should be `hci0`. If not, see step 4.
- [x] **3.** Copy only the `82FB` key line from the Pi 4 by hand. scp from the Pi 5 to the Pi 4 failed with `Permission denied (publickey)`, because there is no SSH key between the Pis.
  - **On the Pi 4**, print that one line: `grep -i '^D4:13:68:61:82:FB ' ~/.govee-h5082-keys`. It shows the key on your screen. Copy it only into the Pi 5 file.
  - **On the Pi 5**, paste it:
    ```bash
    [ -f ~/.govee-h5082-keys ] || install -m 600 /dev/null ~/.govee-h5082-keys   # only if missing
    nano ~/.govee-h5082-keys          # paste that one line, save
    chmod 600 ~/.govee-h5082-keys && wc -l ~/.govee-h5082-keys   # expect 1
    ```
  - Optional, only if the Pi 5 has an SSH key on the Pi 4: `umask 077; scp n4s1@192.168.0.223:.govee-h5082-keys ~/h5082-keys.pi4.tmp && grep -i '^D4:13:68:61:82:FB ' ~/h5082-keys.pi4.tmp >> ~/.govee-h5082-keys; rm -f ~/h5082-keys.pi4.tmp; chmod 600 ~/.govee-h5082-keys`
- [x] **4.** Host allowlist and adapter:
  `mkdir -p ~/.config && install -m 600 /dev/null ~/.config/h5082-bridge.env && printf 'H5082_PLUGS=82FB\nH5082_ADAPTER=hci0\n' > ~/.config/h5082-bridge.env`
  (If step 2 showed the onboard adapter under another name, put that name here.)
- [x] **5.** `sudo bash scripts/install_h5082_bridge.sh --host pi5`. It first checks the venv imports (and exits with the pip command if bleak is missing). Then it installs `systemd/h5082-mqtt-pi5.service` as `/etc/systemd/system/h5082-mqtt.service`, disables and stops `h5082-rssi-pi5` (the new bridge publishes the pi5 RSSI instead), and enables and restarts `h5082-mqtt`. To start it yourself instead: `sudo systemctl enable --now h5082-mqtt`.
- [x] **6.** `journalctl -u h5082-mqtt -n 30`. Expect `OWNS 82FB listener=pi5 adapter=hci0 mode=per-host` and `DISCOVERY 8 listener=pi5`, and no `ModuleNotFoundError`, `NO_KEY_OWNED`, `KEY_FILE` or `OWNER_CONFLICT`.

**Home Assistant `.105`** (after both bridges are up)

- [x] **7.** Reload MQTT: **Settings > Devices & services > MQTT > ⋮ > Reload**. On 2026-09-28 HA kept the old `82FB` entity config (the old availability topic) and sent no commands for it until this reload. No entity changes are needed.

**Checks**

- [x] **8.** SET test: in HA, toggle `switch.ihoment_h5082_82fb_left` (the fan) on and then off. Then run `journalctl -u h5082-mqtt -n 30` on the Pi 5. Expect `LINK_UP 82FB`, `SET 82FB left ON`, then `SET 82FB left OFF`, and no `SET_FAIL`. On the Pi 4, `journalctl -u h5082-mqtt -n 30` shows `NOT_OWNER 82FB left` and no `GATT 82FB`. Do the same for `_right` if you use it.
- [x] **9.** In HA, `switch.ihoment_h5082_82fb_*` is available (it now follows `govee/h5082/bridge/pi5/status`), and **Heard by** / pi5 RSSI keeps updating.
- [ ] **10.** Optional broker check from the Pi 5 (`mosquitto_sub` was not installed there):
  ```bash
  sudo apt install -y mosquitto-clients
  cd /home/n4s1/victron-ble2mqtt-integration
  set -a; source hosts/pi5/mqtt.env; set +a
  mosquitto_sub -h "$MQTT_HOST" -p "${MQTT_PORT:-1883}" -u "$MQTT_USERNAME" -P "$MQTT_PASSWORD" \
    -t 'govee/h5082/+/owner' -t 'govee/h5082/bridge/+/status' -v -W 5
  ```
  Expect `govee/h5082/d413686182fb/owner pi5`, seven `... pi4` claims, and `govee/h5082/bridge/pi4/status online` / `.../pi5/status online`. (`-W 5` stops after 5 s. The `Timed out` at the end is normal.)

**Still open**

- [ ] **11.** Pull this follow-up on both Pis (`git pull`) and restart: `sudo systemctl restart h5082-mqtt`. The `OWNS` line now ends in `bleak=<version>`. The bridge now pins the adapter on any bleak version: bleak 3.x (Pi 5, 3.0.2) takes `bluez={"adapter": ...}`, and older bleak gets `adapter=` instead. Before this, older bleak ignored the bluez form and could fall back to the default adapter, which is `hci0` (Victron) on the Pi 4. On the Pi 4, check `~/govee-ble-venv/bin/pip show bleak | head -2`. If it is older than 3.0, that restart is when the Pi 4 bridge really starts connecting on `hci1`. Toggle one Pi 4 socket and expect `SET <id> ...`.
- [ ] **12.** Optional, Pi 5 clock: `timedatectl` (check the time zone and "System clock synchronized: yes"), then `sudo timedatectl set-timezone America/New_York`.

**Move a plug between Pis later** (see `docs/H5082_MULTI_BRIDGE.md`)

- [ ] Choose the Pi first (optional): run `/home/n4s1/govee-ble-venv/bin/python scripts/h5082_rssi_scan.py --adapter hci1 --seconds 30` on the Pi 4 and the same with `--adapter hci0` on the Pi 5. Pick the Pi with the better best/avg RSSI. The script is read-only.
- [ ] **Old Pi:** remove the id from `H5082_PLUGS` in `~/.config/h5082-bridge.env`, then `sudo systemctl restart h5082-mqtt`.
- [ ] **New Pi:** copy that plug's key line by hand as in Pi 5 step 3: on the old Pi run `grep -i '^<MAC> ' ~/.govee-h5082-keys`, then on the new Pi paste it with `nano ~/.govee-h5082-keys`, then `chmod 600` and `wc -l`. scp is fine only if SSH keys exist. Add the id to `H5082_PLUGS`, then `sudo systemctl restart h5082-mqtt`.
- [ ] HA: reload MQTT (**Settings > Devices & services > MQTT > ⋮ > Reload**).
- [ ] Check with `journalctl -u h5082-mqtt -n 30` on both Pis: `OWNS` lists the plug on one Pi only, there is no `OWNER_CONFLICT`, and a toggle in HA logs `SET <id> ...` on the new Pi.

**Undo** (Pi 5 back to RSSI only): on the Pi 5, `sudo systemctl disable --now h5082-mqtt && sudo systemctl enable --now h5082-rssi-pi5`. On the Pi 4, `rm ~/.config/h5082-bridge.env && sudo systemctl restart h5082-mqtt` (it owns all 8 again on the old availability topic). Then reload MQTT in HA.

## Next step: host steps for "dump manual hold" (2026-09-28)

From branch `dump-manual-hold` (after #9). When a dump socket is switched by hand (Plugs button, the plug's own button, any change dump control did not ask for), dump control leaves it alone for **Dump manual hold** minutes, then resumes. New: `input_number.dump_manual_hold_min` (0-720 min, 0 = off), `input_boolean.dump_hold_blocks_turn_off`, 16 `timer.h5082_<id>_<side>_hold`, `sensor.dump_control_switching`, automations `Dump HOLD start` / `Dump HOLD end`, `script.dump_clear_holds`, a **Dump manual hold** box on Site solar. No `initial:`: the new number starts at **0 = hold off** and the new toggle **off**, so nothing changes until you set them. Your current values are kept. Only `.105` changes. **Pi 4 `.223`: nothing to do** (the bridge is untouched).

**`.105`, in this order**

- [ ] **a.** `cd /home/ansible/victron-ble2mqtt-integration && git pull --ff-only origin main`
- [ ] **b.** Token file for the scripts (never commit it):
  `install -m 600 /dev/null ~/.ha_token && nano ~/.ha_token` (paste a long-lived HA token), then
  `export HA_TOKEN_FILE=~/.ha_token HA_URL=http://127.0.0.1:8123`
- [ ] **c.** Backup first: `python3 scripts/site_solar_settings.py export`
- [ ] **d.** `bash scripts/install_dump_control_ha.sh` (copies the package, runs check_config, restarts HA).
- [ ] **e.** The dashboard seed changed (new Dump manual hold box, hold on the Plugs button label, Dump timers box without the hold timers, help text), so: `python3 scripts/save_solar_plant_storage_dashboard.py --dry-run`, then `python3 scripts/save_solar_plant_storage_dashboard.py --force` (backs the live dashboard up first).
- [ ] **f.** `rm ~/.ha_token && unset HA_TOKEN_FILE`
- [ ] **g.** In HA, Site solar > **Dump manual hold**: set **Hold after a hand switch** (recommended 60 min) and choose **Hold also blocks turn-offs** (recommended on = a held socket is left alone even by solar gone / stop volts / battery limit / sheds; off = those still turn it off). Set these two by hand: **Dump master switch > Load recommended starting values** also sets them (60 / on) but replaces **every** tuned dump number.
- [ ] **h.** Check: tap a dump socket's Plugs button. The Dump activity log shows `switched ... by hand ... Hold N min`, the button label shows `hold to HH:MM`, and its row under **Holds (per socket)** is active. **Clear all holds** logs `hold ended (cleared)`. A dump rule's own switching must **not** start a hold (no "by hand" line after a `turning ON` / `turned OFF by` line).

## Next step: host steps for "House inverter option" (2026-09-28)

From branch `house-inverter-option` (after #8). Some Govee plugs are used in the house on grid power, so each socket's **Inverter** select (`input_select.h5082_<id>_<side>_inverter`, 16 selects) gets a 4th option, **House**. Dump control never switches a House socket, on or off, even if its Use is dump: every socket pick in `dump_control.yaml` now tests "Use is dump **and** Inverter is not House". You can still switch a House socket yourself (Plugs button or the plug's own button). No `initial:` was added. Your current Inverter choices stay (Sungold / T2 / KU are still valid options, so HA restores them). Only `.105` changes. **Pi 4 `.223`: nothing to do.**

**`.105`, in this order**

- [ ] **a.** `cd /home/ansible/victron-ble2mqtt-integration && git pull --ff-only origin main`
- [ ] **b.** Token file for the scripts (never commit it):
  `install -m 600 /dev/null ~/.ha_token && nano ~/.ha_token` (paste a long-lived HA token), then
  `export HA_TOKEN_FILE=~/.ha_token HA_URL=http://127.0.0.1:8123`
- [ ] **c.** Backup first: `python3 scripts/site_solar_settings.py export`
- [ ] **d.** `bash scripts/install_dump_control_ha.sh` (copies the package, runs check_config, restarts HA). After the restart each Inverter select offers House.
- [ ] **e.** The dashboard seed changed (Socket inverter / Socket Use help, Dump sockets by name, plug-button label and gold border), so: `python3 scripts/save_solar_plant_storage_dashboard.py --dry-run`, then `python3 scripts/save_solar_plant_storage_dashboard.py --force` (backs the live dashboard up first).
- [ ] **f.** `rm ~/.ha_token && unset HA_TOKEN_FILE`
- [ ] **g.** In HA, Site solar > **Socket inverter**: set **House** on every socket whose plug is on house grid power. Setting its Use to normal too keeps the rows clear. If dump control had one of those sockets on, it stays on: switch it yourself if needed.
- [ ] **h.** Checks: a House socket shows `house` on its Plugs button (no gold border); if its Use is dump, **Dump sockets by name** lists it as "House (grid power): never switched by dump control" and `sensor.dump_sockets` does not count it.

## Next step: host steps for "C38D dump sockets" (2026-09-28)

From branch `c38d-dump-sockets` (after #7). C38D was paired on the Pi 4 on 2026-09-28 (`~/bin/h5082_pair_c38d.py`, `hci1`; key file now 8 lines) and both sockets logged `SET C38D ... OK` from HA. This change makes C38D a dump-capable plug like the other seven: 16 sockets in every dump list, plus `input_select.h5082_c38d_{left,right}_inverter` and `timer.h5082_c38d_{left,right}_{min_on,cooldown}`. No `initial:` was added. **C38D Use stays `normal`**, so nothing switches C38D until you choose dump. Your current Where / Load / Use / Inverter values are kept. Only `.105` changes. **Pi 4 `.223`: nothing to do** (bridge and key file are already done). If the "no hard-coded plug loads" steps below were not run yet, these steps cover them too.

**`.105`, in this order**

- [ ] **a.** `cd /home/ansible/victron-ble2mqtt-integration && git pull --ff-only origin main`
- [ ] **b.** Token file for the scripts (never commit it):
  `install -m 600 /dev/null ~/.ha_token`, then `nano ~/.ha_token` and paste a long-lived HA token, then
  `export HA_TOKEN_FILE=~/.ha_token HA_URL=http://127.0.0.1:8123`
- [ ] **c.** Backup first: `python3 scripts/site_solar_settings.py export` (every Where / Load / Use / Inverter value and the live dashboard).
- [ ] **d.** `bash scripts/install_dump_control_ha.sh` (copies the package, runs check_config, restarts HA). The new C38D Inverter selects and timers appear after this restart.
- [ ] **e.** Dashboard: `python3 scripts/save_solar_plant_storage_dashboard.py --dry-run`, then `python3 scripts/save_solar_plant_storage_dashboard.py --force` (backs the live dashboard up to `.backups/site-solar/<stamp>-before-seed/` first).
- [ ] **f.** `rm ~/.ha_token` and `unset HA_TOKEN_FILE`.
- [ ] **g.** In HA, Site solar > **Socket inverter**: set **C38D left / right** Inverter to the bus each socket is really on **before** setting its Use to dump (a new select starts on the first option, `Sungold`). Then, only if you want HA to switch it, set C38D Use to dump in **Socket Use**. Use defaults to `normal`.
- [ ] **h.** Checks: **Socket inverter** shows 16 rows; **Dump timers** lists the C38D timers; with a C38D socket set to dump, `sensor.dump_sockets` counts it and **Dump sockets by name** lists it.

## Next step: host steps for "no hard-coded plug loads" (2026-09-28)

From branch `fix/no-hardcoded-plug-loads` (after #6). The Pi 4 is **not** plugged into a Govee plug, and loads and locations will change, so the repo no longer says what is plugged into any H5082 socket or where any plug is. The dashboard and the Dump control logbook lines read the live **Where** / **Load** helpers (`input_text.h5082_<id>_location`, `input_text.h5082_<id>_<side>_load`) and show the plug id and side when one is blank. Entity ids, helper values and dump logic are unchanged, and no `initial:` was added. **Your current Where / Load / Use / Inverter values are kept**: nothing in this change writes to them. Only `.105` changes. **Pi 4 `.223` / Pi 5 `.240`: nothing to do** (the bridge is untouched).

Token: every script reads `HA_TOKEN` or `HA_TOKEN_FILE` (never commit it). Use `HA_URL=http://127.0.0.1:8123` on `.105`.

**`.105`, in this order**

- [ ] **a.** `cd /home/ansible/victron-ble2mqtt-integration && git pull --ff-only origin main`
- [ ] **b.** Export first (keeps a copy of every Where / Load / Use / Inverter value and the live dashboard):
  `HA_TOKEN_FILE=~/.ha_token HA_URL=http://127.0.0.1:8123 python3 scripts/site_solar_settings.py export`
- [ ] **c.** `bash scripts/install_dump_control_ha.sh`: copies `dump_control.yaml` (the logbook lines now start with the socket's live name; one description no longer names a load), runs check_config, and restarts HA.
- [ ] **d.** Dashboard: `HA_TOKEN_FILE=~/.ha_token HA_URL=http://127.0.0.1:8123 python3 scripts/save_solar_plant_storage_dashboard.py --dry-run`, then run the same command with `--force`. The live `/site-solar` config is backed up to `.backups/site-solar/<stamp>-before-seed/` first. Any UI edits made since the last forced save are replaced; undo with `python3 scripts/site_solar_settings.py restore --from <that folder> --dashboard`. Needs HACS `auto-entities` (already used).
- [ ] **e.** Check:
  - **Plug names > Current names (live)** lists your current Where / Left load / Right load (`_not set_` when blank).
  - **Socket Use** / **Socket inverter** rows read `<Load> (<ID> <side>) at <Where>`, or `<ID> <side>` when Load is blank.
  - The C38D card title is just `C38D`, and no button carries the old Pi label any more.
  - **Dump status > Dump sockets by name (live)** names the next socket to add or shed.
  - The next **Dump control** logbook line starts with the socket's name.
  - To confirm no value changed, export again and compare `state` with step b: `python3 -c "import json,sys; a,b=(json.load(open(f)) for f in sys.argv[1:]); [print(k, a[k]['state'], '->', b.get(k,{}).get('state')) for k in a if a[k]['state']!=b.get(k,{}).get('state')]" .backups/site-solar/<b>/helpers.json .backups/site-solar/<e>/helpers.json` (no output means nothing changed).
- [ ] **f.** If any Where / Load you typed earlier still says the Pi 4 is on a plug (for example C38D's Load), change it in **Plug names**. From now on, when you move a plug or plug in something else, change Where / Load there; no repo change is needed.

**Tests:** `pytest tests/` gives 189 passed, 2 skipped, 2 failed. The 2 failures are the same pre-existing ones (`test_solar_ku_estimates::test_now_view_has_ku_est_tile`, `test_solar_plant_ha::test_device_policy_doc`). New: `tests/test_no_hardcoded_plug_loads.py` (25).

## Next step: host steps for Site solar settings persistence + per-box help (2026-09-28)

From branch `fix/site-solar-persist-and-help`. Fixes Site solar settings (dump volts / limits / confirm, Ignore SoC, alert service, and each plug's Where / Load / Use) that reset to the old defaults or blanks, and the dashboard edits that the repo seed overwrote. Adds a help card and a Help page for every dump box. Only `.105` changes. **Pi 4 `.223` / Pi 5 `.240`: nothing to do** (the H5082 bridge is untouched). No new env vars, no `requirements*.txt` change, Node-RED unchanged.

Token: every script below reads `HA_TOKEN` or `HA_TOKEN_FILE` (never commit it). Use `HA_URL=http://127.0.0.1:8123` on `.105`.

**`.105`, in this order**

- [ ] **a. Before pulling anything**, back up the raw HA files:
  `sudo cp -a /opt/homeassistant/.storage ~/ha-storage-backup-$(date +%Y%m%d-%H%M%S)` and
  `sudo cp -a /opt/homeassistant/packages ~/ha-packages-backup-$(date +%Y%m%d-%H%M%S)`.
  Optional extra copy of the dashboard: `sudo cp -a /opt/homeassistant/.storage/lovelace.site_solar ~/lovelace.site_solar.$(date +%Y%m%d-%H%M%S)`.
- [ ] **b.** `cd /home/ansible/victron-ble2mqtt-integration && git pull --ff-only origin main`.
- [ ] **c.** Export the live values (new script, so after the pull):
  `HA_TOKEN_FILE=... HA_URL=http://127.0.0.1:8123 python3 scripts/site_solar_settings.py export`
  → `.backups/site-solar/<stamp>/` (git-ignored): `helpers.json`, `helper-definitions.json`, `dashboards.json`, `dashboard-site-solar.json`.
- [ ] **d.** Strip `initial` from the H5082 storage helpers **before any HA restart**:
  `HA_TOKEN_FILE=... HA_URL=http://127.0.0.1:8123 python3 scripts/create_h5082_socket_labels.py --dry-run` (expect `WOULD STRIP initial` for the `_location`, `_load` and `_use` helpers), then the same command without `--dry-run`. Values are not changed and no restart is needed.
- [ ] **e.** Re-enter any Where / Load / Use that was lost (Site solar > **Plug names** and **Socket Use**). Old text is still in each helper's History. To put back an earlier export instead: `python3 scripts/site_solar_settings.py restore --from LATEST --helpers --dry-run`, then without `--dry-run` (it exports the current values first).
- [ ] **f.** `bash scripts/install_dump_control_ha.sh` (copies the package without `initial:`, runs check_config, restarts HA). After this restart HA keeps the values that were live just before it.
- [ ] **g.** Check the values survived: `python3 scripts/site_solar_settings.py export` again and compare the `state` of each helper with step c (names change because the helpers were renamed; `last_changed` changes at every restart):
  `python3 -c "import json,sys; a,b=(json.load(open(f)) for f in sys.argv[1:]); [print(k, a[k]['state'], '->', b.get(k,{}).get('state')) for k in a if a[k]['state']!=b.get(k,{}).get('state')]" .backups/site-solar/<c>/helpers.json .backups/site-solar/<g>/helpers.json`
  (no output = every value survived). Set any dump number you had tuned before (they had been snapping back to 27.0 / 26.8 / 2000 / 50 / 95 / 5 / 25), or press **Dump master switch > Recommended defaults** once.
- [ ] **h.** Site solar dashboard (pick one):
  - keep the live dashboard and add the new help / log cards by hand, **or**
  - `HA_TOKEN_FILE=... HA_URL=http://127.0.0.1:8123 python3 scripts/save_solar_plant_storage_dashboard.py --dry-run`, then `--force` to load the repo seed. It backs the live config up to `.backups/site-solar/<stamp>-before-seed/` first; undo with `python3 scripts/site_solar_settings.py restore --from <that folder> --dashboard`.
  Without `--force` the script now refuses to overwrite an existing, different dashboard (exit 3). `install_solar_plant_ha.sh` no longer rewrites `.storage/lovelace.site_solar`; `sync_site_solar_storage_from_seed.py` is offline-only (`--force`, HA stopped).
- [ ] **i.** Energy: `save_solar_plant_energy_prefs.py` now backs up and refuses to replace configured prefs without `--force`. Nothing to run unless you want the repo prefs.
- [ ] **j.** Checks:
  - `grep -n 'initial:' /opt/homeassistant/packages/dump_control.yaml` → comment lines only.
  - `sudo grep -c '"initial"' /opt/homeassistant/.storage/input_text /opt/homeassistant/.storage/input_select` → 0 for the `h5082_*` helpers.
  - Settings → Automations: the dump automations now read "Dump ON: ...", "Dump OFF ...", "Dump SHED ...", "Dump ALERT ..." (same ids, no `_2`), all enabled.
  - Settings → System → Logs: no `logbook` / `ServiceNotFound` errors (the package enables `logbook:`).
  - Site solar > **Dump settings change log** shows no value steps at the restart time; **Dump activity log** shows "Dump control" reasons when a socket switches.
- [ ] Optional: review how often `ha-watchdog.timer` / autoheal restart HA (each restart used to re-apply the defaults), and whether the alfa-ai brain / Ask ALFa writes dump helpers (`ha_set_number` / `ha_select_option`); its writes show in the settings change log.
- Note: HA saves restore state every 15 minutes and at a clean stop. A value changed just before an unclean kill (power loss, `docker kill`) can come back as the previous value.

**Tests:** `pytest tests/` → 164 passed, 2 skipped, 2 failed (the same 2 pre-existing failures: `test_solar_ku_estimates::test_now_view_has_ku_est_tile`, `test_solar_plant_ha::test_device_policy_doc`). New: `tests/test_site_solar_persist_and_help.py` (25).

## Next step: host steps from the 2026-09-28 H5082 reliability + sim removal

From the 2026-09-28 PR (branch `fix/h5082-reliability-remove-sim`, after #4). The H5082 bridge keeps one BLE link per plug, retries failed commands, and handles plugs independently. The simulated dump plugs are gone, and dump control now drives the real H5082 sockets whose **Use** is `dump` (`config/packages/dump_control.yaml`). No new env vars and no `requirements*.txt` change. Node-RED flows did not change.

Hosts: Pi 4 `.223` and Pi 5 `.240` (`/home/n4s1/victron-ble2mqtt-integration`); Home Assistant + MQTT broker on `.105` (`/home/ansible/victron-ble2mqtt-integration`).

**Pi 4 `.223`** (`h5082-mqtt`, adapter `hci1`)

- [ ] `cd /home/n4s1/victron-ble2mqtt-integration && git pull`.
- [ ] Deps: no change (the bridge runs from `/home/n4s1/govee-ble-venv`, same bleak as today). Nothing to reinstall.
- [ ] `sudo systemctl restart h5082-mqtt`, then `journalctl -u h5082-mqtt -f` and toggle each socket from HA. Expect `LINK_UP <id>`, then `SET <id> <side> ON|OFF` (`... try 2`/`try 3` when a retry saved it; each failed try logs `GATT <id> <side> ... try n/3 <Exception>: <message>`). A link closes after 120 s idle (`LINK_IDLE`) so the plug advertises again. There should be no `SET_FAIL` on in-range plugs. (At the time C38D still logged `NO_KEY`; it was paired 2026-09-28 and now logs `SET C38D ... OK`.)
- [ ] Optional: `H5082_IDLE_DISCONNECT_S=0` in the unit keeps links open until they drop. Leave it at the default unless you want that: a connected plug stops advertising, so button presses and RSSI/"heard by" for it pause.

**Pi 5 `.240`** (`h5082-rssi-pi5`, RSSI only)

- Note 2026-09-28: after the "Pi 5 H5082 bridge" steps above, the Pi 5 runs `h5082-mqtt` (owned plugs + pi5 RSSI) instead of `h5082-rssi-pi5`.

- [ ] `cd /home/n4s1/victron-ble2mqtt-integration && git pull && sudo systemctl restart h5082-rssi-pi5` (it runs the same `govee_h5082` module; RSSI-only behaviour is unchanged). Check `journalctl -u h5082-rssi-pi5 -n 20` shows `DISCOVERY 8 listener=pi5`.

**`.105`** (Home Assistant + MQTT broker)

- [ ] `cd /home/ansible/victron-ble2mqtt-integration && git pull --ff-only origin main`.
- [ ] If `/opt/homeassistant/packages/sim_dump_control.yaml` or `sim_dump_plugs.yaml` exists: `sudo rm -f /opt/homeassistant/packages/sim_dump_*.yaml`, then HA check config (`docker exec homeassistant python -m homeassistant --script check_config -c /config`) and `docker restart homeassistant`.
- [ ] In Settings → Entities (search `sim_` / `dump_plug_`, status "not provided"), delete the orphaned entities: `switch.sim_ac_plug_*`, `sensor.sim_ac_plug_*_power`, `sensor.sim_dump_load_power`, `input_boolean.sim_ac_plug_*_internal`, `input_text.dump_plug_*_power_entity`, `input_select.dump_plug_*_inverter`, `timer.dump_plug_*`, `sensor.dump_plug_*_last_w`, and the old `automation.dump_load_*` entries (their unique IDs start with `sim_dump_`). If `sensor.sim_dump_energy_kwh` exists as a UI helper, delete it too. Doing this before the next step keeps the new automations from getting `_2` ids.
- [ ] If the per-socket selects are missing: `python3 scripts/create_h5082_socket_labels.py` (HA token; skips the ones that exist and, since the persistence fix, strips `initial`).
- [ ] Install dump control: `bash scripts/install_dump_control_ha.sh` (removes any sim package, copies `dump_control.yaml`, runs check config, restarts HA).
- [ ] Site solar dashboard: `python3 scripts/save_solar_plant_storage_dashboard.py` (HA token) to load the repo seed. **Superseded by step h above: the script now needs `--force` and backs up first.** If you edited it in the UI, replace the **Dump dwell** card (now auto-entities over `timer.h5082_*`) and delete **Dump plug wiring** by hand instead. Then confirm there are no red "entity not available" cards and each Plugs card has an **Inverter** row (not C38D at the time; C38D has Inverter selects since 2026-09-28).
- [ ] Energy: `python3 scripts/save_solar_plant_energy_prefs.py --force` (backs up first; or remove the **Sim dump** device in Settings → Energy).
- [ ] Dump automations: Settings → Automations shows `Dump load turn on`, `... turn off solar gone`, `... shed while not float`, `... shed Sungold load above site solar`, the six re-bulk/battery turn-offs and the notify, all **enabled** and with no `_2` suffix. `sensor.dump_next_plug` / `sensor.dump_shed_plug` show `none` or a `switch.ihoment_h5082_*` id.
- [ ] Set **Use = dump** on the dump sockets (plan: 4 sockets = 2 plugs), set each one's **Inverter**, and check `sensor.dump_sockets` counts them. Leave `input_boolean.dump_control_enabled` off until one dump socket has been switched by hand and by the automation (H5082_INSTALL_PLAN.md Checkpoint 7).
- [ ] Node-RED: flows unchanged, no redeploy.

**Tests:** `pytest tests/` → 139 passed, 2 skipped, 2 failed. The 2 failures were already on `main` and are listed under the 09-26 decisions below (`test_solar_ku_estimates::test_now_view_has_ku_est_tile`, `test_solar_plant_ha::test_device_policy_doc`). `tests/test_sim_dump_control.py` is gone with the sim package.

## Done in 2026-07 repo cleanup

- Untracked TLS key/cert (`ssl/tools.*`); see `SECURITY_REMOVE_SECRETS.md` for history purge.
- Pinned Home Assistant image (Phase 7.5); CI lints `override/` + package; retired soft-fail `ci-lint.yml`.
- Added `dotenv.sample`; corrected bootstrap path (alfa-ai) and clone URL; refreshed inventory / AI how-to stub.

## Next step: post-merge host steps from the 2026-09-26 review (PR #4 fixes; no deps PR)

From [#4](https://github.com/Curt-Alfrey-s-Org/victron-ble2mqtt-integration/pull/4) (open for review 2026-09-26: purge script crash, RSSI cache growth, silent startup failure, H5082 rediscovery, ruff CI fix). There is no deps PR this round (`pip-audit` on the lockfile is clean). No new env vars, nothing to rotate.

Hosts: Pi 4 `.223` and Pi 5 `.240` (`/home/n4s1/victron-ble2mqtt-integration`); the steps below run on the Pi 4, and the Pi 5 runs nothing this PR changes. MQTT broker + Home Assistant are on `.105` (`/home/ansible/victron-ble2mqtt-integration`).

**Before pulling**

- [ ] Nothing to back up (no tracked files removed).

**After merging PR #4 (fixes)** — on the Pi 4 `.223` (`/home/n4s1/victron-ble2mqtt-integration`):

- [ ] `cd /home/n4s1/victron-ble2mqtt-integration && git pull`.
- [ ] **Rebuild/recreate the victron container:** `docker compose -f docker-compose.victron.yml up -d --build` (or the usual `sudo bash scripts/redeploy_victron.sh`). Check `docker logs victron_ble2mqtt`: a startup failure now logs CRITICAL and exits 1, so `restart: unless-stopped` restarts it right away instead of sitting idle.
- [ ] **H5082 bridge:** `sudo systemctl restart h5082-mqtt` (runs `govee_h5082` from this checkout). Plugs that come into range later are now picked up within ~60 s; confirm the 16 H5082 switches in Home Assistant (.105) still update.
- [ ] **Purge script** (`scripts/purge_solar_plant_ha_history.py`, needs an HA admin token via `HA_TOKEN` or `--token-file`; default URL `http://192.168.0.105:8123`): run `python scripts/purge_solar_plant_ha_history.py --dry-run` first and review the entity list (it now also includes the removed computed sensors). Only then `--apply`. It deletes Home Assistant recorder history/statistics.
- [ ] Run `pytest tests/` locally (GitHub Actions is off): expect 124 passed, 2 skipped, 3 failed (the HA config tests below).

**Decisions for you**

- [ ] **3 failing HA config tests vs your 09-24..09-26 HA edits** — for each, update the test or restore the config:
  - `tests/test_sim_dump_control.py::test_surplus_template_and_charge_ok` expects the removed computed sensor `sensor.site_solar_power` (the template now uses device sensors).
  - `tests/test_solar_ku_estimates.py::test_now_view_has_ku_est_tile`: the Site solar dashboard no longer has the "PWM+MPPT est" tile added on 09-24.
  - `tests/test_solar_plant_ha.py::test_device_policy_doc` expects the word "device-native" in the policy doc.
- [ ] `govee_h5082/` isn't in the CI ruff paths and has 9 style-only ruff findings; add it to CI or leave it.
- [ ] Majors available, not applied: rich 14.1 → 15.0, tyro 0.9.28 → 1.0.16 (ha-services stays < 2.15.3 on purpose; it needs Python 3.12).
- [ ] Yesterday's workflow items (ci-trivy deps, ghcr owner) still need a token with `workflow` scope, and the open decision above on re-enabling GitHub Actions still stands.

## Next step: post-merge host steps from the 2026-09-25 security review

From [#2](https://github.com/Curt-Alfrey-s-Org/victron-ble2mqtt-integration/pull/2) (merged 2026-09-25). On the Pi:

- [ ] **Before `git pull`**, back up `nginx/.htpasswd` and `swarm/auto-discovery.env` if in use (now untracked; the pull deletes the working-tree copies). Restore them afterwards (git-ignored).
- [ ] **Rotate** the credential(s) that were in `nginx/.htpasswd` (hashes stay in git history; change the password anywhere it's reused), plus any MQTT credentials ever put in `swarm/auto-discovery.env`. Optional history purge: `SECURITY_REMOVE_SECRETS.md` step 5 (needs a force-push).
- [ ] **Secrets** in `.env` or `victron-secrets.env`: `MQTT_PASSWORD` whenever `MQTT_USER` is set, and at least one `ADVKEY_*`. The bridge now exits at startup naming the missing variable.
- [ ] **Redeploy:** `sudo bash scripts/redeploy_victron.sh`. For offline builds (`PIP_OFFLINE=1`) resync `./wheels` from the hub first (`cli-base-utilities`, `tomlkit`). Confirm the HA Victron sensors update and `docker logs victron_ble2mqtt` shows no callback `TypeError`.
- [ ] Run `pytest tests/` locally (GitHub Actions is disabled for this repo).

**Open decision:** re-enable GitHub Actions? Image publish also needs the org to allow `GITHUB_TOKEN` to create packages; the image is now `ghcr.io/curt-alfrey-s-org/victron-ble2mqtt-integration`.

## Recommended next (in order)

1. **History purge + rotate** — if `ssl/tools.key` was ever pushed, run `git filter-repo` (see `SECURITY_REMOVE_SECRETS.md`) and issue a new cert on the Pi.
2. **Hub reseed HA pin** — on `.111`, pull `ghcr.io/home-assistant/home-assistant:2026.7.3` and publish `home-assistant-2026.7.3.tar.gz`.
3. **Unify package tree** — collapse `override/victron_ble2mqtt` into `victron_ble2mqtt/` (or the reverse) so there is one runtime source.
4. **Phase 5 threat model** — short LAN threat paragraph in `DEPLOY.md` (Dockge `:5006`, MQTT plaintext, Watchtower socket).
5. **Optional audit pass** — research/audit under `docs/audit/` using the alfa-ai pattern (still valid; not blocking).

## Canonical docs

| Doc | Use |
|-----|-----|
| `DEPLOY.md` | Install / redeploy |
| `docs/ENGINEERING_STANDARDS_PLAN.md` | Standards roadmap |
| `REPO_INVENTORY.md` | Layout map |
