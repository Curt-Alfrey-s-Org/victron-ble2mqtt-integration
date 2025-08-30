FROM python:3.11-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    wireless-tools bluez libglib2.0-0 dbus libbluetooth3 \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.lock /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/override:/app:/work
WORKDIR /app
# Copy source code into the image
COPY victron_ble2mqtt /app/victron_ble2mqtt
COPY override/victron_ble2mqtt /app/override/victron_ble2mqtt
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys; import importlib; importlib.import_module('victron_ble2mqtt'); sys.exit(0)" || exit 1
CMD ["docker-entrypoint.sh"]
