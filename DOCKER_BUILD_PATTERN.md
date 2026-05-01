# Docker build pattern — victron-ble2mqtt-integration

This image is **small**: `python:3.11-bookworm` plus `pip install -r requirements.lock` inside the Dockerfile. It does **not** use the Alfa **CUDA / multi‑GB wheel** hub path.

| Situation | What to do |
|-----------|------------|
| Normal Pi / LAN with internet | `sudo bash scripts/deploy.sh` (default `docker build`). |
| Airgap / hub-only pulls | Stage base images on TrueNAS per **alfa-ai** [`docs/HUB_ARTIFACTS.md`](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HUB_ARTIFACTS.md); use `docker load` or a private registry on `.111`. |

Shared pattern vocabulary (dep-cache vs hub): on the dev server, **`/home/ansible/docs/DOCKER_BUILD_PATTERNS.md`**.
