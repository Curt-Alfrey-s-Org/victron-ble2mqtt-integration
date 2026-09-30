"""scripts/site_solar_session.sh: one .105 session (pull, token, wait, backup, action).

Runs the real script in a throw-away repo copy with stub git / curl / python3 / editor,
so nothing talks to HA or git.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "site_solar_session.sh"
EXPORT_REL = "config/dashboards/exports/solar-tab.json"


def _stub(path: Path, body: str) -> None:
    path.write_text("#!/usr/bin/env bash\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def env(tmp_path):
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "config" / "dashboards" / "exports").mkdir(parents=True)
    shutil.copy(SCRIPT, repo / "scripts" / SCRIPT.name)
    home = tmp_path / "home"
    home.mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    _stub(bin_dir / "git", f'echo "git $*" >> {log}\n')
    _stub(bin_dir / "curl", f'echo "curl $*" >> {log}\n[[ -z "${{CURL_FAIL:-}}" ]]\n')
    _stub(
        bin_dir / "python3",
        f'echo "python3 $* token=${{HA_TOKEN_FILE:-}} url=${{HA_URL:-}}" >> {log}\n'
        f'if [[ "$2" == export-dashboard ]]; then echo "{{}}" > {EXPORT_REL}; fi\n'
        'if [[ "$*" == *"--dry-run"* && "$*" != *"--force"* ]]; then exit "${DRY_RC:-0}"; fi\n',
    )
    _stub(bin_dir / "fake-editor", 'echo "not-a-real-token" > "$1"\n')
    base = {
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "HOME": str(home),
        "EDITOR": str(bin_dir / "fake-editor"),
    }
    return {"repo": repo, "home": home, "log": log, "env": base}


def _run(env, *args, extra=None):
    run_env = dict(env["env"], **(extra or {}))
    res = subprocess.run(
        ["bash", str(env["repo"] / "scripts" / SCRIPT.name), *args],
        capture_output=True,
        text=True,
        env=run_env,
        check=False,
    )
    calls = env["log"].read_text(encoding="utf-8").splitlines() if env["log"].exists() else []
    return res, calls


def test_syntax_is_valid():
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "#!/usr/bin/env bash"
    assert "set -euo pipefail" in text
    assert "read -rs" not in text and "read -s" not in text  # tokens only via a file
    assert "install -m 600 /dev/null" in text
    assert "trap cleanup EXIT" in text


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck not installed")
def test_shellcheck_clean():
    subprocess.run(["shellcheck", str(SCRIPT)], check=True)


def test_backup_creates_token_and_removes_it_at_the_end(env):
    res, calls = _run(env, "backup")
    assert res.returncode == 0, res.stderr
    token = env["home"] / ".ha_token"
    assert not token.exists()  # created by this run -> removed
    assert "removed" in res.stdout and "not-a-real-token" not in res.stdout + res.stderr
    assert calls[0] == "git pull --ff-only origin main"
    assert calls[1].startswith("curl -s -o /dev/null http://127.0.0.1:8123")
    assert calls[2] == f"python3 scripts/site_solar_settings.py export token={token} url=http://127.0.0.1:8123"
    assert len(calls) == 3
    for header in ("==> git pull", "==> token file", "==> wait for Home Assistant", "==> backup"):
        assert header in res.stdout


def test_keep_token_and_existing_token_are_kept(env):
    res, _ = _run(env, "--keep-token", "--no-pull", "backup")
    assert res.returncode == 0, res.stderr
    token = env["home"] / ".ha_token"
    assert token.exists() and stat.S_IMODE(token.stat().st_mode) == 0o600
    # A token file that already existed is never removed.
    res, calls = _run(env, "--no-pull", "backup")
    assert res.returncode == 0 and token.exists()
    assert not any(c.startswith("git ") for c in calls)


def test_ha_token_file_env_is_used_as_is(env, tmp_path):
    mine = tmp_path / "my-token"
    mine.write_text("x\n", encoding="utf-8")
    res, calls = _run(env, "--no-pull", "backup", extra={"HA_TOKEN_FILE": str(mine), "HA_URL": "http://ha:8123"})
    assert res.returncode == 0, res.stderr
    assert mine.exists() and not (env["home"] / ".ha_token").exists()
    assert calls[-1].endswith(f"token={mine} url=http://ha:8123")


def test_solar_compare_removes_its_export_unless_kept(env):
    res, calls = _run(env, "--no-pull", "solar-compare")
    assert res.returncode == 0, res.stderr
    assert [c.split(" token=")[0] for c in calls[2:]] == [
        "python3 scripts/site_solar_settings.py export-dashboard",
        f"python3 scripts/compare_solar_tab.py {EXPORT_REL}",
    ]
    assert not (env["repo"] / EXPORT_REL).exists()
    res, _ = _run(env, "--no-pull", "--keep-export", "solar-compare")
    assert (env["repo"] / EXPORT_REL).exists()
    # An export that existed before the run is left alone.
    res, _ = _run(env, "--no-pull", "solar-compare")
    assert (env["repo"] / EXPORT_REL).exists()


def test_dashboard_dry_run_and_apply_use_the_save_script(env):
    res, calls = _run(env, "--no-pull", "dashboard-dry-run", extra={"DRY_RC": "3"})
    assert res.returncode == 0, res.stderr
    tail = [c.split(" token=")[0] for c in calls[2:]]
    assert tail == [
        "python3 scripts/save_solar_plant_storage_dashboard.py --dry-run",
        "python3 scripts/save_solar_plant_storage_dashboard.py --dry-run --force",
    ]
    env["log"].unlink()
    res, calls = _run(env, "--no-pull", "dashboard-apply")
    assert res.returncode == 0, res.stderr
    assert calls[-1].startswith("python3 scripts/save_solar_plant_storage_dashboard.py --force token=")
    assert "restore --from" in res.stdout


def test_restore_passthrough(env):
    res, calls = _run(env, "--no-pull", "restore", "--from", "LATEST", "--dashboard", "--dry-run")
    assert res.returncode == 0, res.stderr
    assert calls[-1].startswith("python3 scripts/site_solar_settings.py restore --from LATEST --dashboard --dry-run")


def test_waits_for_ha_and_gives_up_with_a_message(env):
    res, calls = _run(env, "--no-pull", "--wait", "0", "backup", extra={"CURL_FAIL": "1"})
    assert res.returncode != 0
    assert "did not answer" in res.stderr
    assert not any(c.startswith("python3") for c in calls)
    assert not (env["home"] / ".ha_token").exists()  # cleanup ran on failure too


def test_unknown_action_is_refused(env):
    res, calls = _run(env, "deploy")
    assert res.returncode != 0 and "unknown action" in res.stderr
    assert calls == []
