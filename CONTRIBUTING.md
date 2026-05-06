# Contributing

## Checks (mirror CI)

Python **3.11** matches `Dockerfile`. From the repo root:

```bash
python -m pip install --upgrade pip
pip install ruff pytest
pip install -r requirements.lock
ruff check victron_ble2mqtt
pytest tests/ -q
```

CI runs the same checks (`tests/` are exercised by pytest; package lint is scoped to `victron_ble2mqtt/` until test modules adopt stricter Ruff rules).
