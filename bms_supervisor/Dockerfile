FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    udev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bms_supervisor ./bms_supervisor

ENV PYTHONUNBUFFERED=1 \
    HEARTBEAT_FILE=/tmp/bms_supervisor.heartbeat \
    BMS_SERIAL_DEVICE=/dev/vedirect

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD ["python", "-c", "import os,sys,time; p=os.environ.get('HEARTBEAT_FILE','/tmp/bms_supervisor.heartbeat'); max_age=180; m=os.path.getmtime(p) if os.path.exists(p) else 0; raise SystemExit(0 if time.time()-m<=max_age else 1)"]

CMD ["python", "-m", "bms_supervisor"]
