# Engineering standards implementation plan

This document is the **single roadmap** for aligning **victron-ble2mqtt-integration** with maintainable, auditable practices grounded in **official manuals** (Docker, Docker Compose, systemd, Debian packaging, Python packaging) and common **industry defaults** (Twelve-Factor config, least-privilege secrets, CI gates).

**Scope:** deploy scripts, Compose stacks, systemd units, Python bridge, shell helpers, and overlap with **monitoring** (`monitoring/hosts/pi4-victron/README.md`) after operational changes.

**Non-goals:** turning the Pi into a Petals/GPU worker; changing Victron protocol behavior unless required for reliability.

---

## Phase 0 — Baseline and references (no code churn)

**Status:** Done — **`DEPLOY.md` Notes** now include a **sources of truth** bullet (Compose paths, Mosquitto/systemd, secret files). Manual anchors remain as listed below.

**Deliverables**

- Short **“sources of truth”** note in `DEPLOY.md` or `README.md`: which file owns Mosquitto config, which Compose files Dockge includes, where secrets live (`.env`, `victron-secrets.env`, `/etc/mosquitto/watchdog.env`).
- Confirm **manual anchors** the repo claims to follow:
  - [Docker Compose — Compose file reference](https://docs.docker.com/reference/compose-file/) (`healthcheck`, `restart`, logging).
  - [Docker — Configure logging drivers](https://docs.docker.com/engine/logging/configure/) (json-file rotation already used — keep consistent limits across stacks).
  - [systemd.service — Restart=](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) for native `mosquitto.service`.
  - [Twelve-Factor — Config](https://12factor.net/config) for env vs baked secrets.

**Acceptance:** Maintainer can answer “where do I change X?” without reading `deploy.sh` end-to-end.

---

## Phase 1 — Container supervision (replace overlapping watchdogs with standard patterns)

**Status:** Done — **`docker-compose.autoheal.yml`** (`willfarrell/autoheal:1.2.0`), **`autoheal=true`** labels on **`homeassistant`** and **`victron_ble2mqtt`**, **`ENABLE_AUTOHEAL=1`** (default), **`ENABLE_HA_WATCHDOG=0`** (default); **`deploy.sh`** disables legacy **`ha-watchdog.timer`** on redeploy when watchdog off; **`ENABLE_HA_WATCHDOG=1`** remains documented legacy path.

**Verification:** `docker compose … config` for **`docker-compose.autoheal.yml`**, **`docker-compose.victron.yml`**, **`docker-compose.homeassistant.yml`**; **`docker compose up -d`** for **`autoheal`** succeeds on target Docker host. Full wedged-container drill remains operator QA on the Pi (**`DEPLOY.md`**).

**Current state**

- `docker-compose.homeassistant.yml` already defines a **`healthcheck`** (HTTP on port 8123).
- `docker-compose.victron.yml` defines a **`healthcheck`** (import smoke).
- Compose **`restart: unless-stopped`** only restarts on **container exit**, not on **`unhealthy`** ([healthcheck semantics](https://docs.docker.com/reference/compose-file/services/#healthcheck)).
- **`scripts/ha-watchdog.sh`** + **`ha-watchdog.timer`** duplicate HTTP liveness outside Compose.

**Industry-aligned direction**

1. **Introduce a single “unhealthy container recovery” path** for Docker-managed services:
   - Add a small **`autoheal`** (or equivalent) service per [common Compose patterns](https://github.com/willfarrell/docker-autoheal): mount **read-only** Docker socket, **`AUTOHEAL_CONTAINER_LABEL=all`** or label only `homeassistant` and `victron_ble2mqtt`, set sane poll interval (e.g. 30–60s).
   - Add Compose labels on services that should be restarted when unhealthy (avoid restarting unrelated stacks).

2. **After autoheal is proven on the Pi**, make **`ENABLE_HA_WATCHDOG` default `0`** (or remove install path) so HTTP probing happens **once** (Compose healthcheck + autoheal), not twice per minute from systemd.

3. **Keep MQTT broker watchdog until Mosquitto supervision is equivalent or better:**
   - Mosquitto runs under **systemd**, not Compose; `Restart=on-failure` / `Restart=always` handles **process exit**, not **wedged broker**.
   - Options (pick **one** in implementation):
     - **A (minimal change):** Add a **drop-in** for `mosquitto.service` with `Restart=always` and tight `StartLimitIntervalSec` / `StartLimitBurst` to avoid restart storms; **retain** `mqtt-watchdog` until metrics show no false positives.
     - **B (larger):** Run Mosquitto in Compose with **`healthcheck`** (subscribe to `$SYS/broker/uptime`) + autoheal — only if operator accepts broker-in-Docker operational model on this hardware.

**Manual alignment:** Docker documents **HEALTHCHECK** for images; Compose **`healthcheck`** is the stack-level equivalent. Recovery on **`unhealthy`** is **not** Compose core behavior — autoheal (or an orchestrator) is the usual supplement.

**Acceptance**

- With HA intentionally wedged (simulate failure), **container becomes healthy → unhealthy → restarted** without relying on `ha-watchdog.timer`.
- Documentation lists **`ENABLE_HA_WATCHDOG=1`** only as legacy escape hatch.
- No duplicate HTTP probes unless justified (document why).

---

## Phase 2 — `deploy.sh` structure and systemd units (maintainability)

**Status:** Done — **`systemd/docker-prune.{service,timer}`**, **`systemd/mqtt-watchdog.{service,timer}`**, **`scripts/mqtt-watchdog.sh`** are tracked; **`deploy.sh`** installs via **`install -m`** (no inline heredocs for those units). **`vscode-server-cleanup`**, **`ha-watchdog`**, **`wifi-failover-monitor`** were already tracked templates where applicable.

**Problem:** Inline heredocs for units (e.g. `mqtt-watchdog`, `docker-prune`) are hard to review, diff, and validate.

**Direction**

- Move generated units to **`systemd/*.service` / `systemd/*.timer`** in the repo (same pattern as `ha-watchdog.*`).
- `deploy.sh` **installs** files with `install -m`, optionally **`systemctl edit --full`** only when templating user/path is required.
- Run **`shellcheck`** on all `scripts/*.sh` in CI (Phase 4); fix warnings in deploy paths touched by Phase 1–2.

**Acceptance:** Every timer/service under `/etc/systemd/system/` that this repo owns has a **matching tracked file** under `systemd/` or `scripts/` with a clear header comment.

---

## Phase 3 — Python bridge quality (packaging, typing, tests)

**Status:** Partial — **`[dependency-groups] dev`** added to **`pyproject.toml`**; Ruff config migrated to **`[tool.ruff.lint]`**; **`victron_ble2mqtt/test_helpers.py`** fixed for Ruff; CI runs **`pytest`** + **`ruff check victron_ble2mqtt`** (tests lint deferred — many intentional lazy imports).

**Direction** (incremental, highest ROI first)

1. **Extend existing `pyproject.toml`:** add or consolidate **dev** dependency groups (`pytest`, `ruff`, optional `mypy`) per [Python packaging guidance](https://packaging.python.org/).
2. **`ruff`** (or `flake8` + `black` — pick **one** formatter/linter family): enforce on `victron_ble2mqtt/` and `tests/`.
3. **`pytest`** in CI for offline-safe tests; mark BLE/integration tests as **`@pytest.mark.integration`** and skip by default on CI if hardware required.
4. **Logging:** use **`logging`** module with structured context where helpful; avoid **`print`** in hot paths (align with Docker json-file logging).

**Acceptance:** CI fails on lint regressions; `pytest` passes without Pi BLE.

---

## Phase 4 — CI/CD pipeline (GitHub Actions or equivalent)

**Status:** Minimal workflow added — **`.github/workflows/ci.yml`** (Python 3.11, **`requirements.lock`**, Ruff on **`victron_ble2mqtt/`**, pytest **`tests/`**). **`CONTRIBUTING.md`** mirrors local commands.

**Minimal workflow**

- **shellcheck** → `scripts/**/*.sh`
- **pytest** → `tests/` (non-integration)
- **docker compose config** validation → `docker compose ... config` for each tracked compose file (catches YAML/schema drift)
- Optional **hadolint** `Dockerfile`

**Acceptance:** PRs show green checks; contributors see commands mirrored in `CONTRIBUTING.md` (short).

---

## Phase 5 — Security and operations (OWASP-style hygiene for edge)

**Direction**

- **Secrets:** document **`chmod 600`** for `.env`, `victron-secrets.env`, `/etc/mosquitto/watchdog.env`; never log passwords (audit `deploy.sh` / scripts for `set -x` in credential sections).
- **Docker socket:** autoheal (if added) gets **read-only** socket mount; document blast radius.
- **Watchtower:** already label-gated — document required labels for production containers to avoid surprise upgrades.
- **Unattended upgrades / prune timers:** ensure **`docker-prune`** filters match retention policy and **do not** prune volumes needed by HA (`DEPLOY.md` already mentions conservative prune — keep explicit).

**Acceptance:** Threat-model paragraph in `DEPLOY.md` (Pi LAN edge, Docker socket, MQTT auth).

---

## Phase 6 — Observability alignment

**Direction**

- After changing health/rest behavior, update **`monitoring/hosts/pi4-victron/README.md`** targets and alert rules if Prometheus scrapes node-exporter or blackbox on the Pi.
- Prefer **one** restart path so logs/metrics explain failures (avoid systemd restart fighting Compose restart).

**Acceptance:** Monitoring README matches deployed timers/services.

---

## Suggested implementation order

| Order | Phase | Rationale |
|-------|--------|-----------|
| 1 | 0 | Avoid rework from undocumented assumptions |
| 1 | 4 (minimal) | CI catches regressions while refactoring deploy |
| 2 | 1 | Biggest operational simplification; removes duplicate HA probes |
| 3 | 2 | Makes Phase 1 changes reviewable |
| 4 | 3 | Code quality debt paid incrementally |
| 5 | 5–6 | Security narrative + fleet observability |

---

## Rollback / flags

- **`ENABLE_HA_WATCHDOG=1`** — restore legacy timer during transition.
- **`ENABLE_MQTT_WATCHDOG=0`** — only after systemd/Compose Mosquitto story is validated.
- **`ENABLE_TOOLS=0`** — disable Watchtower/autoheal stack slices independently per operator preference.

---

## Related repo docs

- `DEPLOY.md` — installer flags and behavior
- `docs/ALFA_CLUSTER_INTEGRATION.md` — hub wheels / NFS / Prometheus touchpoints
- `AGENTS.md` — Cursor/agent scope for this repo
