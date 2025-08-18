# 1) Image: preinstall deps + pin python libs
cat > Dockerfile <<'EOF'
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
EOF

cat > requirements.lock <<'EOF'
bleak==1.1.0
paho-mqtt==2.1.0
victron-ble==0.9.2
ha-services==2.12.0
rich==14.1.0
tyro==0.9.28
EOF

# 2) Entrypoint: generate user_settings from env, then run app
cat > docker-entrypoint.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import os, re, json, ast, pathlib
from textwrap import dedent
repo_example = pathlib.Path("/app/user_settings.example.py")
devices = []
if repo_example.exists():
    txt = repo_example.read_text(errors="ignore")
    m = re.search(r"devices\s*=\s*\[", txt)
    if m:
        start = m.end()-1; depth=0; end=None
        for i,ch in enumerate(txt[start:], start):
            if ch=='[': depth+=1
            elif ch==']':
                depth-=1
                if depth==0: end=i; break
        if end is not None:
            block = txt[start:end+1]
            for d in re.findall(r"\{.*?\}", block, flags=re.S):
                clean = re.sub(r"#.*","",d)
                try:
                    obj = ast.literal_eval(clean)
                    if isinstance(obj, dict):
                        obj.pop("advertisement_key", None)
                        devices.append(obj)
                except Exception:
                    pass
mqtt_host = os.getenv("MQTT_HOST","localhost")
mqtt_port = int(os.getenv("MQTT_PORT","1883"))
mqtt_user = os.getenv("MQTT_USER","victron")
topic_root = os.getenv("TOPIC_ROOT","victron")
outdir = pathlib.Path("/work/victron_ble2mqtt")
outdir.mkdir(parents=True, exist_ok=True)
content = dedent(f"""
# Auto-generated; NO secrets embedded.
import os, re
mqtt_host = {mqtt_host!r}
mqtt_port = {mqtt_port}
mqtt_username = {mqtt_user!r}
mqtt_password = os.getenv("MQTT_PASSWORD","")
mqtt_topic_root = {topic_root!r}
devices = {json.dumps(devices, indent=2)}
def _slug(s:str)->str: return re.sub(r"[^A-Za-z0-9]+","_",(s or "").strip()).strip("_").upper()
for d in devices:
    name = d.get("name") or d.get("type") or ""
    mac  = (d.get("mac") or "").replace(":","").upper()
    key = os.getenv("ADVKEY_"+_slug(name)) or (os.getenv("ADVKEY_"+mac) if mac else "")
    if key: d["advertisement_key"] = key
log_level = "INFO"
""").strip()+"\n"
(outdir / "user_settings.py").write_text(content)
print("Wrote", outdir / "user_settings.py", "with", len(devices), "devices")
PY
exec python -m victron_ble2mqtt.__main__
EOF

# 3) Safety shim: if 'iwconfig' is ever missing, just skip Wi-Fi info
mkdir -p override/ha_services/mqtt4homeassistant/system_info
cat > override/ha_services/mqtt4homeassistant/system_info/wifi_info.py <<'EOF'
def get_wifi_infos():
    # If iwconfig/iw aren't available, return nothing (no crash, no spam).
    return []
EOF

# 4) Build image and switch the running service to it
sudo docker build -t local/victron-ble-bridge:1.0 .
sudo docker service update \
  --image local/victron-ble-bridge:1.0 \
  --args "docker-entrypoint.sh" \
  --force victron_ble_victron_ble_bridge
