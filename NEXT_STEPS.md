# Next steps — victron-ble2mqtt-integration

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
