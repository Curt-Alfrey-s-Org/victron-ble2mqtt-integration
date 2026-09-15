import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).resolve().parents[1] / "scripts/pi4_ble_exclusive.py"
    spec = importlib.util.spec_from_file_location("pi4_ble_exclusive", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_disabled_by_default():
    mod = _load()
    ok, reason = mod.may_start_pi4_theengs("0", "hci0", "hci1")
    assert ok is False
    assert "ENABLE_PI4_THEENGS" in reason


def test_empty_flag_is_disabled():
    mod = _load()
    ok, _reason = mod.may_start_pi4_theengs(None, None, None)
    assert ok is False


def test_same_hci_blocked_even_when_enabled():
    mod = _load()
    ok, reason = mod.may_start_pi4_theengs("1", "", "")
    assert ok is False
    assert "hci0" in reason


def test_explicit_same_names_blocked():
    mod = _load()
    ok, _reason = mod.may_start_pi4_theengs("1", "hci0", "HCI0")
    assert ok is False


def test_different_hci_allowed_when_enabled():
    mod = _load()
    ok, reason = mod.may_start_pi4_theengs("1", "hci0", "hci1")
    assert ok is True
    assert "hci0" in reason
    assert "hci1" in reason


def test_cli_exit_codes(monkeypatch, capsys):
    mod = _load()
    monkeypatch.setenv("ENABLE_PI4_THEENGS", "0")
    monkeypatch.delenv("BLE_ADAPTER", raising=False)
    monkeypatch.delenv("THEENGS_ADAPTER", raising=False)
    assert mod.main([]) == 1
    monkeypatch.setenv("ENABLE_PI4_THEENGS", "1")
    monkeypatch.setenv("BLE_ADAPTER", "hci0")
    monkeypatch.setenv("THEENGS_ADAPTER", "hci1")
    assert mod.main([]) == 0
    out = capsys.readouterr().out
    assert "differ" in out


def test_pi4_theengs_compose_uses_profile():
    src = (
        Path(__file__).resolve().parents[1] / "hosts/pi4/docker-compose.theengs.yml"
    ).read_text(encoding="utf-8")
    assert 'profiles: ["solar-theengs"]' in src
    assert "ADAPTER: ${THEENGS_ADAPTER:-hci0}" in src
    assert "healthcheck:" not in src


def test_dotenv_sample_defaults_theengs_off():
    src = (Path(__file__).resolve().parents[1] / "dotenv.sample").read_text(encoding="utf-8")
    assert "ENABLE_PI4_THEENGS=0" in src
    assert "THEENGS_ADAPTER" in src


def test_deploy_sh_hooks_pi4_theengs_guard():
    src = (Path(__file__).resolve().parents[1] / "scripts/deploy.sh").read_text(encoding="utf-8")
    assert "start_pi4_theengs_if_enabled.sh" in src
    assert "deploy_pi4_theengs_stack_if_enabled" in src
    assert ': "${ENABLE_PI4_THEENGS:=0}"' in src


def test_start_script_uses_profile_and_args():
    src = (
        Path(__file__).resolve().parents[1] / "scripts/start_pi4_theengs_if_enabled.sh"
    ).read_text(encoding="utf-8")
    assert "--profile solar-theengs" in src
    assert '"$@"' in src
    assert "down --remove-orphans" not in src
    assert "up -d --remove-orphans" not in src
