# Integration with TrueNAS hub, alfa-ai, and monitoring

This repo runs **edge IoT** workloads (Home Assistant + Victron BLE → MQTT) on a Raspberry Pi. It is **not** a Petals GPU worker, but it should follow the same **LAN-first artifact** and **observability** conventions as [alfa-ai](https://github.com/Curt-Alfrey-s-Org/alfa-ai) and [monitoring](https://github.com/Curt-Alfrey-s-Org/monitoring).

---

## 1. TrueNAS hub (`.111`)

Canonical policy lives in alfa-ai:

- [HUB_ARTIFACTS.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/HUB_ARTIFACTS.md) — **≥ 200 MB** binaries are seeded on the hub once; LAN clients read NFS `…/mnt/cluster/…` or SMB `\\GAMERBOYZ\…`.
- [CLUSTER_SHARED_STORAGE.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/CLUSTER_SHARED_STORAGE.md) — dataset layout under `/mnt/HDDs/Alfa-AI/`.

### What applies on the Pi

| Artifact | Typical size | On Pi |
|----------|----------------|--------|
| `python:3.11-bookworm` base layers | > 200 MB | Prefer **`docker pull` via registry mirror** on `.111` (`http://192.168.0.111:5000` when configured), or `docker load` a tarball from **`/mnt/cluster/docker/images/`** (or SMB `\\GAMERBOYZ\docker-images\`) after a one-time save on the hub. |
| `ghcr.io/home-assistant/home-assistant:stable` | Large | Same: mirror or **hub tarball** + `docker load`; avoid repeated multi-GB pulls from the public internet once the image exists on the LAN. |
| Victron app `pip` deps (`requirements.lock`) | Usually < 200 MB | May still use hub **wheels** if you standardize on offline `pip install --find-links` in a future Dockerfile revision. |

### NFS (optional)

If the Pi mounts cluster storage (same pattern as Linux workers in alfa-ai):

```bash
# Example only — use your NAS export and fstab policy.
sudo mkdir -p /mnt/cluster
sudo mount -t nfs 192.168.0.111:/mnt/HDDs/alfa-ai-cluster /mnt/cluster
```

Then stage image tarballs or use paths documented in `HUB_ARTIFACTS.md` for `docker load`.

### Docker Engine → mirror

Point the Pi’s Docker daemon at the pull-through registry on TrueNAS when that mirror is deployed (see alfa-ai / TrueNAS docs). After that, `docker compose` / `docker pull` on the Pi use LAN bandwidth instead of docker.io for cached layers.

---

## 2. alfa-ai (organization + inventory)

- **Repo:** [Curt-Alfrey-s-Org/alfa-ai](https://github.com/Curt-Alfrey-s-Org/alfa-ai) — distributed AI stack, hub scripts, and **NODE_INVENTORY**.
- **This Pi** should appear in [docs/NODE_INVENTORY.md](https://github.com/Curt-Alfrey-s-Org/alfa-ai/blob/main/docs/NODE_INVENTORY.md) once you assign a **static LAN IP** (summary table: *Raspberry Pi 4 — Victron / HA edge*).
- **Contributing:** develop Victron/HA changes here; keep **secrets** (MQTT passwords, `ADVKEY_*`) out of git — use `.env` / `victron-secrets.env` as today.

There is no runtime coupling between Petals/LiteLLM and this stack; integration is **operational** (artifacts, docs, monitoring).

---

## 3. monitoring (Prometheus on `.105`)

Central stack: [Curt-Alfrey-s-Org/monitoring](https://github.com/Curt-Alfrey-s-Org/monitoring) — Prometheus **9092**, Grafana **3000** on `192.168.0.105`.

### Host metrics on the Pi

1. Clone the monitoring repo on the Pi (or copy the folder from a workstation).
2. Run the edge helper (same pattern as `hosts/192.168.0.248`):

   ```bash
   cd monitoring/hosts/pi4-victron
   chmod +x run.sh setup-linux-metrics.sh
   ./run.sh
   sudo ./setup-linux-metrics.sh
   ```

3. On **192.168.0.105**, edit `prometheus/prometheus.yml`: under `job_name: node-remote`, add a target **`YOUR_PI_IP:9100`** with labels `instance: pi4-victron`, `host_role: iot-edge` (see commented template in that file).
4. Reload Prometheus: `curl -X POST http://127.0.0.1:9092/-/reload` (from `.105`, or via Docker).

### Home Assistant / MQTT

- HA UI and MQTT are **application** concerns; Prometheus does not scrape them by default. Optional follow-ups: blackbox probe to `http://PI_IP:8123/`, or an MQTT exporter if you add one cluster-wide.

### Firewall

Allow **TCP 9100** from `192.168.0.105` to the Pi if you use host firewall rules (`ufw` example is in `setup-linux-metrics.sh` output on other hosts).

---

## Quick checklist

- [ ] Static DHCP / fixed IP for the Pi; document it in alfa-ai `NODE_INVENTORY.md`.
- [ ] Large images (Python base, HA) via **hub or mirror**, not repeated cold pulls from the internet.
- [ ] `node_exporter` on Pi + **Prometheus** `node-remote` target on `.105`.
- [ ] (Optional) NFS `/mnt/cluster` on Pi for tarballs and backups.
