Docker / Swarm notes for victron-ble2mqtt-integration
This project contains a number of Docker and Docker Swarm helper files under `swarm/` used to run a victron BLE -> MQTT bridge in containers.
This file documents the recommended quick-compose usage for a single-host Docker setup and points to the existing swarm stacks for multi-host deployments.
Quick single-host compose (see `docker-compose.victron.yml`)
- Uses the repo Dockerfile and mounts `override/` into the container so runtime patches are available.
- Ensure you set the MQTT envs in a `.env` file or use `swarm/ha-discovery.env` and `swarm/victron-secrets.env` for secrets/keys.
Notes
- The original swarm stacks live in `swarm/` (look for `victron-ble-bridge-stack.yml`).
- The container entrypoint runs `python -m victron_ble2mqtt` and expects `victron_ble2mqtt` package modules available from the workspace (the container Dockerfile adds the repo into `/work`).
- If you use the compose below on a Pi, ensure Bluetooth access is available inside the container (privileged or host network/volumes as needed).
See `README.md` for debugging and one-shot run examples.
If you need a tailored swarm conversion or additional services (dozzle, health), tell me which pieces to include.
Docker / Swarm notes for victron-ble2mqtt-integration

This project contains a number of Docker and Docker Swarm helper files under `swarm/` used to run a victron BLE -> MQTT bridge in containers.

This file documents the recommended quick-compose usage for a single-host Docker setup and points to the existing swarm stacks for multi-host deployments.

Quick single-host compose (see `docker-compose.victron.yml`)

- Uses the repo Dockerfile and mounts `override/` into the container so runtime patches are available.
- Ensure you set the MQTT envs in a `.env` file or use `swarm/ha-discovery.env` and `swarm/victron-secrets.env` for secrets/keys.

Notes
- The original swarm stacks live in `swarm/` (look for `victron-ble-bridge-stack.yml`).
- The container entrypoint runs `python -m victron_ble2mqtt` and expects `victron_ble2mqtt` package modules available from the workspace (the container Dockerfile adds the repo into `/work`).
- If you use the compose below on a Pi, ensure Bluetooth access is available inside the container (privileged or host network/volumes as needed).

See `README.md` for debugging and one-shot run examples.

If you need a tailored swarm conversion or additional services (dozzle, health), tell me which pieces to include.
