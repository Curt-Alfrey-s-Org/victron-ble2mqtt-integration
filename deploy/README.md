Production deployment notes — Raspberry Pi (aarch64)

Goal
- Run victron-ble2mqtt and the tools stack on a Raspberry Pi (aarch64) in a reproducible, secure way.

Assumptions
- Host is Raspberry Pi OS / Debian-based aarch64 with Docker Engine and Docker Compose v2 installed.
- You have the repository checked out on the Pi at /home/<user>/victron-ble2mqtt-integration.
- Required secrets (MQTT credentials, ADVKEY_*) will be provided via .env or env_file and not committed to git.

Steps
1) Prepare the host
   - Install Docker and Compose v2 (e.g., from Docker's APT repo).
   - Add your user to the docker group and reboot (or use sudo for docker commands).
2) Build multi-arch images (recommended) on a build machine or use buildx on the Pi.
   - On the Pi (local build):
     docker buildx create --use --name mybuilder || true
     docker buildx build --platform linux/arm64 -t victron_ble2mqtt:pi-aarch64 --load .
   - Or build on an x86 builder and push to a registry with multi-arch manifests:
     docker buildx build --platform linux/amd64,linux/arm64 -t <your-registry>/victron_ble2mqtt:latest --push .
3) Configure secrets
   - Create a `.env` containing MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASSWORD and ADVKEY_<MAC_OR_NAME> entries.
   - Keep secrets out of repo; use environment-managed secrets in production if possible.
4) Runtime overlays
   - If you need to override device definitions, mount `override/` to `/work/override` (the compose files already do this).
   - Ensure `override/victron_ble2mqtt/user_settings_data.py` contains only non-secret device metadata.
5) Run the victron service
   - On the Pi, run:
     docker compose -f docker-compose.victron.yml up --build -d
   - Use `docker logs -f victron_ble2mqtt` to watch runtime logs.
6) Tools stack
   - Copy the `nginx` certs and `nginx/.htpasswd` to a secure location on the Pi (they're in the repo for now).
   - Run the tools stack (the compose file binds nginx:443 to host):
     docker compose -f docker-compose.tools.yml up -d
7) Make services persistent
   - If you want the compose stacks to start on boot, create a systemd unit that runs `docker compose -f <compose> up -d`.
8) Hardening checklist
   - Replace self-signed certs with Let's Encrypt if reachable from the internet, or a company CA for internal use.
   - Rotate the htpasswd entry to a strong password and limit access by firewall rules.
   - Enable docker daemon log rotation and limit container logging sizes (compose files already set json-file rotation options).
   - Ensure watchtower labels are set only on containers you want auto-updated.

Troubleshooting
- If BLE/BlueZ access fails, ensure the container has access to `/run/dbus/system_bus_socket` and that the user has proper privileges (the compose file mounts DBus).
- If port conflicts occur, check that no other service binds 443; the tools nginx expects to own 443.

Notes
- The `docker-entrypoint.sh` generates `/work/victron_ble2mqtt/user_settings.py` at container start and reads ADVKEY_<slug> environment variables rather than embedding secrets into the repo.
- For production, prefer building and pushing images to a registry and deploying with orchestration (docker stack or a minimal k3s) if you need higher availability.
