FROM python:3.11-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    wireless-tools bluez libglib2.0-0 dbus libbluetooth3 \
 && rm -rf /var/lib/apt/lists/*

# Hub wheels (sync via scripts/sync-victron-wheels-from-hub.sh); empty dir = PyPI-only build.
ARG PIP_OFFLINE=0
COPY wheels /tmp/wheels
COPY requirements.lock /tmp/requirements.txt

RUN set -eu; \
    if [ "${PIP_OFFLINE}" = "1" ]; then \
      pip install --no-cache-dir --no-index --find-links=/tmp/wheels -r /tmp/requirements.txt; \
    else \
      pip install --no-cache-dir --find-links=/tmp/wheels -r /tmp/requirements.txt; \
    fi && rm -rf /tmp/wheels /tmp/requirements.txt

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/override:/app:/work
WORKDIR /app
COPY victron_ble2mqtt /app/victron_ble2mqtt
COPY override/victron_ble2mqtt /app/override/victron_ble2mqtt
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
# Liveness: victron_ble2mqtt.liveness.check (system + BLE scanner + BLE publish).
# https://docs.docker.com/reference/compose-file/services/#healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=180s --retries=3 \
    CMD ["python", "-c", "from victron_ble2mqtt.liveness import check; raise SystemExit(check())"]
CMD ["docker-entrypoint.sh"]
