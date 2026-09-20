"""Solar-flow SVG stack is retired; HA Energy is canonical."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_solar_flow_runtime_removed() -> None:
    assert not (ROOT / "scripts" / "solar_flow_server.py").exists()
    assert not (ROOT / "systemd" / "solar-flow.service").exists()
    assert not (ROOT / "web" / "solar-flow").exists()


def test_retired_doc_and_uninstall_script() -> None:
    stub = (ROOT / "docs" / "SOLAR_FLOW_DASHBOARD.md").read_text(encoding="utf-8")
    assert "Retired" in stub
    assert "SOLAR_HA_DASHBOARD.md" in stub
    assert "DUMP_LOAD_HA_CONTROL.md" in stub
    script = (ROOT / "scripts" / "uninstall_solar_flow.sh").read_text(encoding="utf-8")
    assert "disable --now" in script
    assert "solar-flow.service" in script
    assert "serve reset" not in script
    assert "tailscale serve --https=443 --set-path=/ off" in script
    assert "http://192.168.0.105:8123/energy" in script
