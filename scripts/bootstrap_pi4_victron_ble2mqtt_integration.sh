#!/usr/bin/env bash
# Bootstrap Raspberry Pi OS (64-bit) desktop: update OS, install git, clone
# this repo, seed optional swarm env files, then run the unified installer
# (Docker, Mosquitto, HA, BLE bridge).
#
# Run as your normal user (e.g. n4s1) — the script uses sudo where needed.
# From another machine you can copy this file, or on the Pi after minimal git:
#   curl -fsSL https://raw.githubusercontent.com/Curt-Alfrey-s-Org/victron-ble2mqtt-integration/main/scripts/bootstrap_pi4_victron_ble2mqtt_integration.sh | bash
# (Review scripts before piping to bash in production.)
#
# Overrides (optional):
#   REPO_URL=... INSTALL_DIR=~/victron-ble2mqtt-integration BRANCH=main bash ...

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Curt-Alfrey-s-Org/victron-ble2mqtt-integration.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/victron-ble2mqtt-integration}"
BRANCH="${BRANCH:-main}"

need_cmd() { command -v "$1" >/dev/null 2>&1; }

if [[ "$(id -u)" -eq 0 ]]; then
  echo "Run this as a normal user with sudo privileges, not as root." >&2
  exit 1
fi

if ! need_cmd sudo; then
  echo "sudo is required." >&2
  exit 1
fi

echo "[bootstrap] apt update / upgrade (noninteractive)..."
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -y
sudo apt-get upgrade -y -o Dpkg::Options::=--force-confold

echo "[bootstrap] installing git and curl..."
sudo apt-get install -y git ca-certificates curl

if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
  echo "[bootstrap] cloning ${REPO_URL} -> ${INSTALL_DIR} (branch ${BRANCH})..."
  git clone --branch "${BRANCH}" --single-branch "${REPO_URL}" "${INSTALL_DIR}"
else
  echo "[bootstrap] repo exists; pulling latest..."
  git -C "${INSTALL_DIR}" fetch origin "${BRANCH}"
  git -C "${INSTALL_DIR}" checkout "${BRANCH}"
  git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"
fi

cd "${INSTALL_DIR}"

# Optional: swarm/*.env for scripts that source them (e.g. bin/ble-run.sh). Main
# stack uses repo-root victron-secrets.env (created by deploy.sh if missing).
if [[ ! -f swarm/ha-discovery.env ]] && [[ -f swarm/ha-discovery.env.example ]]; then
  echo "[bootstrap] creating swarm/ha-discovery.env (localhost broker)..."
  sed 's/^MQTT_HOST=.*/MQTT_HOST=127.0.0.1/' swarm/ha-discovery.env.example > swarm/ha-discovery.env
  chmod 600 swarm/ha-discovery.env
fi
if [[ ! -f swarm/victron-secrets.env ]] && [[ -f swarm/victron-secrets.env.example ]]; then
  echo "[bootstrap] creating swarm/victron-secrets.env from example (edit ADVKEY_*)..."
  cp -n swarm/victron-secrets.env.example swarm/victron-secrets.env
  chmod 600 swarm/victron-secrets.env
fi

echo "[bootstrap] running upstream installer (Docker, Mosquitto, HA, victron)..."
echo "[bootstrap] This can take a long time on first run (Docker image build + HA pull)."
sudo bash scripts/deploy.sh

echo
echo "[bootstrap] Done."
echo "  - Edit ADVKEY_* in ${INSTALL_DIR}/victron-secrets.env (and swarm copy if you use swarm scripts), then:"
echo "      cd ${INSTALL_DIR} && sudo bash scripts/redeploy_victron.sh"
echo "  - If docker commands fail for your user until reboot: log out/in or: newgrp docker"
echo "  - Status: systemctl status victron-ble2mqtt.service"
echo "  - Logs:   journalctl -u victron-ble2mqtt.service -f"
echo "  - HA:     http://$(hostname -I 2>/dev/null | awk '{print $1}'):8123"
