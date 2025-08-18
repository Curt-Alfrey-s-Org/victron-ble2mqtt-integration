FROM python:3.11-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    wireless-tools bluez libglib2.0-0 dbus libbluetooth3 \
 && rm -rf /var/lib/apt/lists/*
COPY requirements.lock /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/override:/app:/work
WORKDIR /app
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
CMD ["docker-entrypoint.sh"]
