#!/usr/bin/env bash
# victron-runner.sh
# Long-running runner used by systemd to start the compose stack and monitor health.
set -eu
WORKDIR="/home/n4s1/victron-ble2mqtt-integration"
cd "$WORKDIR"

# Bring up the compose stack (build if necessary)
/usr/bin/docker compose -f docker-compose.victron.yml up -d --build

# Monitor the main container health and exit only on failure
MAIN_SERVICE=victron_ble2mqtt
while true; do
  sleep 5
  if docker ps --filter "name=${MAIN_SERVICE}" --format '{{.Names}}' | grep -q "${MAIN_SERVICE}"; then
    # check health status
    HEALTH=$(docker inspect --format='{{.State.Health.Status}}' ${MAIN_SERVICE} 2>/dev/null || echo unknown)
    if [ "$HEALTH" = "healthy" ]; then
      sleep 30
      continue
    elif [ "$HEALTH" = "starting" ]; then
      # keep waiting
      sleep 5
      continue
    elif [ "$HEALTH" = "unhealthy" ]; then
      echo "${MAIN_SERVICE} reported unhealthy, restarting stack" >&2
      /usr/bin/docker compose -f docker-compose.victron.yml down
      /usr/bin/docker compose -f docker-compose.victron.yml up -d
      sleep 10
      continue
    else
      # unknown or no healthcheck set
      sleep 10
      continue
    fi
  else
    echo "${MAIN_SERVICE} not running, starting stack" >&2
    /usr/bin/docker compose -f docker-compose.victron.yml up -d
    sleep 5
  fi
done
