Repository inventory for victron-ble2mqtt-integration

Purpose
- Quick map of important files and suggested first refactors/moves so we can proceed safely.

Checklist (extracted from your request)
- Inventory all files and highlight high-impact files to move/change.  [Done]
- Propose a safe, minimal refactor plan.  [Next]
- Implement agreed changes and validate (lint/tests/build).  [Pending user approval]

Key findings

- `README.md`
  - Present and contains detailed run/debug instructions and notes.

- `DOCKER_SWARM.md`
  - File exists but is empty. It previously had edits that were undone. Needs restoration or replacement.

- `docker-compose.victron.yml`
  - File exists but is empty. Likely should contain a victron-specific compose/service definition.

- `Dockerfile`, `docker-entrypoint.sh`
  - Present at repo root; used by container workflows.

- `override/` (package)
  - `override/victron_ble2mqtt/` contains runtime entrypoint (`__main__.py`), `mqtt.py`, CLI app overrides and `user_settings.py` dataclass. Runtime appears to prefer `override` on PYTHONPATH.

- `victron_ble2mqtt` usages
  - The codebase executes `python -m victron_ble2mqtt` and imports `victron_ble2mqtt.*` throughout. `override` module collocates replacement modules.

- `user_settings` variants
  - `config/user_settings.example.py` (template)
  - `override/victron_ble2mqtt/user_settings.py` (dataclass used at runtime)
  - top-level `user_settings.py` also contains the same dataclass (duplicate/override). Consider consolidating into package.

- `config/` and `swarm/`
  - `config/` contains systemd unit and toml sample.
  - `swarm/` contains stacks, env examples and scripts referencing `victron_ble2mqtt` and container workflows.

Potential refactors (low-risk -> higher-risk)
1) Consolidate `user_settings` into single package location
   - Move `override/victron_ble2mqtt/user_settings.py` to `victron_ble2mqtt/user_settings.py` (or keep as `override` but remove duplicates at repo root). Reduces confusion.

2) Restore docs and compose files
   - Recreate `DOCKER_SWARM.md` from `swarm/` content and `README.md` notes.
   - Populate `docker-compose.victron.yml` from `swarm/victron-ble-bridge-stack.yml` or craft minimal compose for single-host use.

3) Normalize package layout
   - Ensure `victron_ble2mqtt` package exists in `override` or top-level and that `PYTHONPATH` usage is explicit in Dockerfiles/start scripts.

4) Add a tiny smoke test / run script
   - A one-line script to run `python -m victron_ble2mqtt` with a dry-run flag or limited scan for CI/local validation.

Risks & assumptions
- I assume `override` is intentionally used to patch/replace upstream `victron_ble2mqtt` package; moving files may change import order. If deployments rely on `PYTHONPATH` including `override`, we should preserve that behavior.
- I won't modify runtime code until you confirm which consolidation approach you prefer.

Suggested immediate next actions (pick one or more)
- A) Create a consolidated `REPO_INVENTORY.md` (this file) and then propose precise file moves. [Done]
- B) Restore `DOCKER_SWARM.md` content from the `swarm/` directory and `README.md`. [I can do this now]
- C) Populate `docker-compose.victron.yml` with a sensible single-host compose using existing stack fragments. [I can draft and validate]
- D) Consolidate `user_settings.py` into a single package location and remove duplicates. [requires confirmation]

What I will do next
- If you want, I can draft and apply one of the suggested immediate actions (B, C, or D). Tell me which to run first or say "proceed with your recommendation" and I'll implement the recommended minimal change (restore `DOCKER_SWARM.md` and populate `docker-compose.victron.yml`) and then run a quick smoke validation (lint/read checks).


Files scanned to produce this inventory
- README.md
- DOCKER_SWARM.md
- docker-compose.victron.yml
- Dockerfile
- docker-entrypoint.sh
- override/victron_ble2mqtt/*
- config/*
- swarm/*


End of inventory.
