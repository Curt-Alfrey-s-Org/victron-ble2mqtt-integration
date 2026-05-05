# Same LAN as Alfa — hub, alfa-ai, monitoring (no Petals on the Pi)

This repo runs on a **Raspberry Pi** (or similar) as a **home / Victron / MQTT / Home Assistant** edge. It is **not** part of the **Petals** distributed GPU cluster or the **CPU worker fleet** unless you explicitly choose to repurpose that host.

---

## alfa-ai — see, analyze, and edit this repo in Cursor

On the development host (e.g. **web-sites** / `.105`), keep clones as **siblings** so one Cursor workspace can index all of them:

| Repo | Typical path |
|------|----------------|
| **alfa-ai** | `/home/ansible/alfa-ai` |
| **victron-ble2mqtt-integration** | `/home/ansible/victron-ble2mqtt-integration` |
| **monitoring** | `/home/ansible/monitoring` |

**Cursor:** **File → Add Folder to Workspace…** and add the two other folders (or open a multi-root `.code-workspace` that lists all three). Agents and search then apply across repos without merging git histories.

**Doc-first for alfa-ai:** When a change touches **cluster storage, hub policy, or worker deploy**, read the relevant files under `alfa-ai/docs/` (e.g. `HUB_ARTIFACTS.md`, `CLUSTER_SHARED_STORAGE.md`, `NODE_INVENTORY.md`) before editing **this** repo’s deploy scripts so paths and policy stay consistent.

Pointer from alfa-ai back to this repo: `alfa-ai/docs/RELATED_VICTRON_HOMEAUTO.md`.

---

## TrueNAS hub (.111)

Alfa’s **canonical hub** policy and paths are documented in:

- `alfa-ai` repo: [`docs/HUB_ARTIFACTS.md`](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HUB_ARTIFACTS.md)
- Shared pattern reference (on the dev server): `/home/ansible/docs/DOCKER_BUILD_PATTERNS.md`

**victron-ble2mqtt-integration** builds a **small** app image (`python:3.11-bookworm` + locked pip deps). On the Pi, **`scripts/deploy.sh`**:

1. **Docker Hub pulls** — merges **`registry-mirrors: ["http://192.168.0.111:5000"]`** into **`/etc/docker/daemon.json`** (disable with **`ENABLE_DOCKER_REGISTRY_MIRROR=0`**).
2. **PyPI wheels** — when NFS **`/mnt/cluster/wheels/victron`** is mounted, runs **`scripts/sync-victron-wheels-from-hub.sh`** into repo **`./wheels`** and builds with **`PIP_OFFLINE=1`** (see **`DOCKER_BUILD_PATTERN.md`**). Seed on `.111`: **`alfa-ai/scripts/seed-victron-wheels-truenas.sh`**.
3. **Home Assistant (GHCR)** — the hub mirror does **not** proxy GHCR. Seed on `.111`: `docker pull ghcr.io/home-assistant/home-assistant:stable` then **`alfa-ai/scripts/publish-built-image-to-hub.sh`** … **`home-assistant-stable.tar.gz`**. On the Pi, **`deploy.sh`** runs **`docker load`** from **`/mnt/cluster/docker-images/home-assistant-stable.tar.gz`** (or alternate hub paths / **`HA_IMAGE_TARBALL`**) before Compose starts HA.

Mount **`/mnt/cluster`** per **`alfa-ai/docs/CLUSTER_SHARED_STORAGE.md`** so these paths resolve.

Do **not** treat the Pi as a worker that should `pip install` multi‑GB CUDA stacks from the hub; that is unrelated to this stack.

---

## monitoring (Prometheus on `.105`)

Central stack: **monitoring** repo on **192.168.0.105** (see `monitoring/README.md`).

**On the Pi:**

1. Clone **monitoring** (or copy the host folder from a machine that already has it).
2. Run **`hosts/pi4-victron/run.sh`** then **`sudo ./setup-linux-metrics.sh`** (installs `node_exporter` on **:9100** and documents firewall).
3. On **.105**, edit **`monitoring/prometheus/prometheus.yml`**: uncomment the **`node-remote`** target for the Pi and set the real LAN IP; optionally add the Pi to **`blackbox-icmp`** and add an HTTP probe for Home Assistant (`http://<pi-ip>:8123/`) under **`blackbox-http-lan`** or a small dedicated job.
4. Reload Prometheus: `curl -X POST http://127.0.0.1:9092/-/reload`

Details and verification: **`monitoring/hosts/pi4-victron/README.md`**.

---

## Summary

| Concern | Where it lives |
|--------|----------------|
| Cursor / agents across repos | Multi-root: alfa-ai + victron + monitoring |
| Hub / large artifacts | `alfa-ai/docs/HUB_ARTIFACTS.md` |
| Pi metrics in Grafana | `monitoring` + `hosts/pi4-victron/` |
| **Not** in scope | Petals swarm membership, worker wheel variants, GPU fleet |
