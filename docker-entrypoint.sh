#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
import os, re, json, ast, pathlib, sys, importlib
from textwrap import dedent

# Collect device entries from the canonical example file if present
repo_example = pathlib.Path("/app/user_settings.example.py")
devices = []
if repo_example.exists():
    txt = repo_example.read_text(errors="ignore")
    m = re.search(r"devices\s*=\s*\[", txt)
    if m:
        start = m.end()-1; depth = 0; end = None
        for i, ch in enumerate(txt[start:], start):
            if ch == '[': depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is not None:
            block = txt[start:end+1]
            for d in re.findall(r"\{.*?\}", block, flags=re.S):
                clean = re.sub(r"#.*", "", d)
                try:
                    obj = ast.literal_eval(clean)
                    if isinstance(obj, dict):
                        obj.pop("advertisement_key", None)
                        devices.append(obj)
                except Exception:
                    pass

# Also attempt to import device definitions from the runtime override module
# (mounted under /work/override), which some deployments use.
try:
    sys.path.insert(0, "/work/override")
    sys.path.insert(0, "/work")
    try:
        usd = importlib.import_module("victron_ble2mqtt.user_settings_data")
    except Exception:
        usd = None
    if usd and hasattr(usd, "devices"):
        for d in getattr(usd, "devices", []):
            if isinstance(d, dict):
                # copy and strip secrets so we don't write advertisement keys into the file
                obj = dict(d)
                obj.pop("advertisement_key", None)
                devices.append(obj)
except Exception:
    # Don't let import failures stop the entrypoint
    pass

mqtt_host = os.getenv("MQTT_HOST", "localhost")
mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
mqtt_user = os.getenv("MQTT_USER", "")
topic_root = os.getenv("TOPIC_ROOT", "victron")
outdir = pathlib.Path("/work/victron_ble2mqtt")
outdir.mkdir(parents=True, exist_ok=True)
content = dedent(f"""
# Auto-generated; NO secrets embedded.
import os, re
mqtt_host = {mqtt_host!r}
mqtt_port = {mqtt_port}
mqtt_username = {mqtt_user!r}
mqtt_password = os.getenv("MQTT_PASSWORD", "")
mqtt_topic_root = {topic_root!r}
devices = {json.dumps(devices, indent=2)}
def _slug(s:str)->str: return re.sub(r"[^A-Za-z0-9]+","_",(s or "").strip()).strip("_").upper()
for d in devices:
    name = d.get("name") or d.get("type") or ""
    mac  = (d.get("mac") or "").replace(":", "").upper()
    key = os.getenv("ADVKEY_"+_slug(name)) or (os.getenv("ADVKEY_"+mac) if mac else "")
    if key: d["advertisement_key"] = key
log_level = "INFO"
""").strip()+"\n"
(outdir / "user_settings.py").write_text(content)
print("Wrote", outdir / "user_settings.py", "with", len(devices), "devices")
PY

exec python -m victron_ble2mqtt.__main__
