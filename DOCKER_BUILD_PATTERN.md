# Docker build pattern — victron-ble2mqtt-integration

This image uses **`python:3.11-bookworm`** plus **`pip install -r requirements.lock`**. When the Pi has **`./wheels`** populated from the TrueNAS hub, builds use **`PIP_OFFLINE=1`** (`--no-index --find-links`) — same convention as **alfa-ai** Petals workers ([`docs/HUB_ARTIFACTS.md`](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HUB_ARTIFACTS.md)).

| Situation | What to do |
|-----------|------------|
| Normal Pi / internet | `sudo bash scripts/deploy.sh` — **`PIP_OFFLINE=0`** if `./wheels` has no `.whl` files. |
| LAN + NFS **`/mnt/cluster`** mounted | **`deploy.sh`** runs **`scripts/sync-victron-wheels-from-hub.sh`** when **`/mnt/cluster/wheels/victron`** exists; if wheels land in **`./wheels`**, build uses **`PIP_OFFLINE=1`**. |
| Seed wheels on `.111` | `sudo bash alfa-ai/scripts/seed-victron-wheels-truenas.sh` (arm64 + amd64). |
| Large base images | **`deploy.sh`** merges **`registry-mirrors: ["http://192.168.0.111:5000"]`** into **`daemon.json`** so Docker Hub pulls use the LAN mirror. **Home Assistant** comes from **GHCR** — mirror it via **`docker pull`** on `.111` then **`alfa-ai/scripts/publish-built-image-to-hub.sh`** → **`home-assistant-stable.tar.gz`**; **`deploy.sh`** **`docker load`**s from **`/mnt/cluster/docker-images/`** when present. |

Manual rebuild:

```bash
bash scripts/sync-victron-wheels-from-hub.sh   # when hub mounted
export PIP_OFFLINE=1    # if wheels present
docker compose -f docker-compose.victron.yml build --build-arg PIP_OFFLINE="${PIP_OFFLINE:-0}"
```

Shared vocabulary: **`/home/ansible/docs/DOCKER_BUILD_PATTERNS.md`** on the dev server.
