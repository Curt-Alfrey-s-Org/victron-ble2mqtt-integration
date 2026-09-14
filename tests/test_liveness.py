import importlib.util
import os
import time
from pathlib import Path


def _load_liveness():
    path = Path(__file__).resolve().parents[1] / "override/victron_ble2mqtt/liveness.py"
    spec = importlib.util.spec_from_file_location("victron_liveness", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _point_at_tmp(mod, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HEARTBEAT_FILE", str(tmp_path / "system.heartbeat"))
    monkeypatch.setenv("BLE_SCANNER_OK_FILE", str(tmp_path / "scanner_ok"))
    monkeypatch.setenv("BLE_PUBLISH_HEARTBEAT_FILE", str(tmp_path / "ble_publish"))
    return (
        os.environ["HEARTBEAT_FILE"],
        os.environ["BLE_SCANNER_OK_FILE"],
        os.environ["BLE_PUBLISH_HEARTBEAT_FILE"],
    )


def test_check_fails_when_files_missing(tmp_path, monkeypatch):
    leftover = Path("/tmp")
    leftover.mkdir(parents=True, exist_ok=True)
    for name in (
        "victron_ble2mqtt.heartbeat",
        "victron_ble2mqtt.scanner_ok",
        "victron_ble2mqtt.ble_publish",
    ):
        (leftover / name).write_text("host-leftover", encoding="utf-8")
    mod = _load_liveness()
    _point_at_tmp(mod, tmp_path, monkeypatch)
    monkeypatch.setenv("SYSTEM_POLL_THROTTLE_SEC", "60")
    monkeypatch.setenv("BLE_PUBLISH_MAX_AGE_SEC", "600")
    assert mod.check() == 1


def test_check_passes_when_all_fresh(tmp_path, monkeypatch):
    mod = _load_liveness()
    _point_at_tmp(mod, tmp_path, monkeypatch)
    monkeypatch.setenv("SYSTEM_POLL_THROTTLE_SEC", "60")
    monkeypatch.setenv("BLE_PUBLISH_MAX_AGE_SEC", "600")
    mod.touch_system_heartbeat()
    mod.touch_scanner_ok()
    mod.touch_ble_publish_heartbeat()
    assert mod.check() == 0


def test_check_fails_when_ble_publish_stale(tmp_path, monkeypatch):
    mod = _load_liveness()
    _hb, _scanner, ble_path = _point_at_tmp(mod, tmp_path, monkeypatch)
    monkeypatch.setenv("SYSTEM_POLL_THROTTLE_SEC", "60")
    monkeypatch.setenv("BLE_PUBLISH_MAX_AGE_SEC", "1")
    mod.touch_system_heartbeat()
    mod.touch_scanner_ok()
    ble = Path(ble_path)
    ble.write_text("", encoding="utf-8")
    old = time.time() - 30
    os.utime(ble, (old, old))
    assert mod.check() == 1


def test_check_fails_when_system_heartbeat_stale(tmp_path, monkeypatch):
    mod = _load_liveness()
    sys_path, _scanner, _ble = _point_at_tmp(mod, tmp_path, monkeypatch)
    monkeypatch.setenv("SYSTEM_POLL_THROTTLE_SEC", "1")
    monkeypatch.setenv("BLE_PUBLISH_MAX_AGE_SEC", "600")
    sys_hb = Path(sys_path)
    sys_hb.write_text("", encoding="utf-8")
    old = time.time() - 120
    os.utime(sys_hb, (old, old))
    mod.touch_scanner_ok()
    mod.touch_ble_publish_heartbeat()
    assert mod.check() == 1


def test_dockerfile_healthcheck_uses_liveness_check():
    src = (Path(__file__).resolve().parents[1] / "Dockerfile").read_text(encoding="utf-8")
    assert "from victron_ble2mqtt.liveness import check" in src
    assert "--start-period=180s" in src
    assert "|| exit 1" not in src


def test_compose_healthcheck_uses_exec_cmd():
    src = (Path(__file__).resolve().parents[1] / "docker-compose.victron.yml").read_text(
        encoding="utf-8"
    )
    assert "CMD-SHELL" not in src
    assert "- CMD" in src
    assert "AUTOHEAL_CONTAINER_LABEL: autoheal" not in src


def test_autoheal_label_env_is_label_name():
    src = (
        Path(__file__).resolve().parents[1] / "docker-compose.autoheal.yml"
    ).read_text(encoding="utf-8")
    assert "AUTOHEAL_CONTAINER_LABEL: autoheal" in src
    assert "AUTOHEAL_CONTAINER_LABEL: autoheal=true" not in src
