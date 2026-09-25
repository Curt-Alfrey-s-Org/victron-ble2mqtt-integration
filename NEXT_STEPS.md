# Next steps — victron-ble2mqtt-integration

## Done in 2026-07 repo cleanup

- Untracked TLS key/cert (`ssl/tools.*`); see `SECURITY_REMOVE_SECRETS.md` for history purge.
- Pinned Home Assistant image (Phase 7.5); CI lints `override/` + package; retired soft-fail `ci-lint.yml`.
- Added `dotenv.sample`; corrected bootstrap path (alfa-ai) and clone URL; refreshed inventory / AI how-to stub.

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
