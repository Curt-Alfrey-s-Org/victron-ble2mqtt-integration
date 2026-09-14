#!/usr/bin/env bash
# Deploy bms_supervisor sidecar when ENABLE_BMS_SUPERVISOR=1 (Pi4 or Pi5).
# Sourced/called from scripts/deploy.sh and scripts/deploy_pi5.sh.
set -Eeuo pipefail

: "${ENABLE_BMS_SUPERVISOR:=0}"
: "${BMS_SERIAL_DEVICE:=/dev/vedirect}"

install_vedirect_udev_rule() {
  if [[ ! -f "$ROOT_DIR/udev/99-vedirect-usb.rules" ]]; then
    echo "[deploy] WARN: udev/99-vedirect-usb.rules missing -- skip VE.Direct udev install." >&2
    return 0
  fi
  echo "[deploy] Installing VE.Direct USB udev rule (/dev/vedirect) ..."
  sudo install -m 0644 -D "$ROOT_DIR/udev/99-vedirect-usb.rules" /etc/udev/rules.d/99-vedirect-usb.rules
  sudo udevadm control --reload-rules 2>/dev/null || true
  sudo udevadm trigger --subsystem-match=tty 2>/dev/null || true
}

bms_supervisor_serial_device_ready() {
  local dev="${BMS_SERIAL_DEVICE:-/dev/vedirect}"
  [[ -e "$dev" ]] || [[ -e /dev/vedirect ]]
}

deploy_bms_supervisor_stack_if_enabled() {
  [[ "${ENABLE_BMS_SUPERVISOR:-0}" == "1" ]] || return 0
  if [[ ! -f "$ROOT_DIR/docker-compose.bms-supervisor.yml" ]]; then
    echo "[deploy] ENABLE_BMS_SUPERVISOR=1 but docker-compose.bms-supervisor.yml missing -- skip." >&2
    return 0
  fi
  install_vedirect_udev_rule
  if ! bms_supervisor_serial_device_ready; then
    echo "[deploy] ENABLE_BMS_SUPERVISOR=1 but no USB serial device yet (${BMS_SERIAL_DEVICE:-/dev/vedirect})."
    echo "[deploy] Plug VE.Direct USB cable (ASS030530000), confirm FTDI 0403:6015 (lsusb), set BMS_SERIAL_DEVICE in .env, re-run deploy."
    return 0
  fi
  echo "[deploy] Building and starting bms_supervisor (read-only VE.Direct -> MQTT) ..."
  if [[ "${ENABLE_DOCKGE:-0}" == "1" ]] && declare -F write_dockge_stack_wrapper >/dev/null 2>&1; then
    write_dockge_stack_wrapper bms-supervisor "$ROOT_DIR/docker-compose.bms-supervisor.yml"
    (cd /opt/stacks/bms-supervisor && docker compose up -d --build)
  else
    (cd "$ROOT_DIR" && docker compose -f docker-compose.bms-supervisor.yml up -d --build)
  fi
}
