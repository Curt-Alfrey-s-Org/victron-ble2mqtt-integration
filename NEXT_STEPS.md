# Next steps — victron-ble2mqtt-integration

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
