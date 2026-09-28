"""Site solar: settings survive restarts / reruns, every dump box has help (2026-09-28).

No live Home Assistant: YAML structure, pure helpers and fake websocket sessions.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / "config" / "packages"
DUMP_PKG = PACKAGES / "dump_control.yaml"
SEED = ROOT / "config" / "dashboards" / "solar-plant.yaml"
DOCS = ROOT / "docs" / "site-solar"
DOC_BASE = (
    "https://github.com/Curt-Alfrey-s-Org/victron-ble2mqtt-integration/blob/main/docs/site-solar/"
)
HELPER_DOMAINS = ("input_boolean", "input_number", "input_text", "input_select")
DUMP_WORDS = ("dump", "h5082")


def _load(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pkg(path: Path = DUMP_PKG) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


# ------------------------------------------------------------------ persistence


@pytest.mark.parametrize("path", sorted(PACKAGES.glob("*.yaml")), ids=lambda p: p.name)
def test_no_initial_on_any_user_set_helper(path: Path) -> None:
    data = _pkg(path)
    for domain in HELPER_DOMAINS:
        for key, cfg in (data.get(domain) or {}).items():
            assert "initial" not in (cfg or {}), f"{path.name}: {domain}.{key} has initial"


def test_dump_package_keeps_every_helper_id() -> None:
    data = _pkg()
    assert len(data["input_number"]) == 16  # + 2 booleans + 1 text = 19 helpers
    assert set(data["input_boolean"]) == {"dump_control_enabled", "dump_soc_unsynced"}
    assert set(data["input_text"]) == {"dump_notify_service"}
    assert len(data["input_select"]) == 16


def test_package_loads_logbook_for_reason_lines() -> None:
    assert "logbook" in _pkg()


def test_defaults_script_is_manual_only() -> None:
    data = _pkg()
    script = data["script"]["dump_load_recommended_defaults"]
    blob = json.dumps(script)
    assert "input_boolean.dump_control_enabled" not in blob
    assert "input_select." not in blob and "switch." not in blob
    assert "dump_notify_service" not in blob
    # Nothing calls it: no automation, no startup trigger.
    autos = json.dumps(data["automation dump_load"])
    assert "dump_load_recommended_defaults" not in autos
    assert "homeassistant" not in [
        t.get("trigger") for a in data["automation dump_load"] for t in a["triggers"]
    ]


def test_no_automation_writes_helpers_on_start_or_timer() -> None:
    for auto in _pkg()["automation dump_load"]:
        for trig in auto["triggers"]:
            assert trig.get("trigger") not in ("homeassistant", "time_pattern", "time", "event")
        blob = json.dumps(auto["actions"])
        for svc in ("input_number.set_value", "input_select.select_option", "input_text.set_value"):
            assert svc not in blob, auto["id"]


def test_label_helpers_created_without_initial_and_ids_unchanged() -> None:
    mod = _load("create_h5082_socket_labels")
    payloads = mod.helper_payloads()
    assert len(payloads) == 8 + 16 + 16
    for payload, entity_id in payloads:
        assert "initial" not in payload, entity_id
        slug = re.sub(r"[^a-z0-9]+", "_", payload["name"].lower()).strip("_")
        assert entity_id.split(".", 1)[1] == slug  # name -> entity id stays the same
    ids = mod.managed_entity_ids()
    assert "input_text.h5082_82fb_location" in ids
    assert "input_select.h5082_c38d_right_use" in ids


def test_strip_initial_keeps_everything_else() -> None:
    mod = _load("create_h5082_socket_labels")
    item = {
        "id": "h5082_82fb_left_use",
        "name": "My renamed use",
        "options": ["normal", "dump"],
        "initial": "normal",
        "icon": "mdi:toggle-switch",
    }
    body = mod.strip_initial_update("input_select", item)
    assert body == {
        "type": "input_select/update",
        "input_select_id": "h5082_82fb_left_use",
        "name": "My renamed use",
        "options": ["normal", "dump"],
        "icon": "mdi:toggle-switch",
    }
    assert mod.strip_initial_update("input_text", {"id": "x", "name": "x"}) is None


# ------------------------------------------------------------ dashboard save script


class _FakeSession:
    def __init__(self, live: dict | None, exists: bool = True) -> None:
        self.live = live
        self.exists = exists
        self.calls: list[dict] = []

    def call(self, payload: dict):
        self.calls.append(payload)
        kind = payload["type"]
        if kind == "lovelace/dashboards/list":
            return [{"url_path": "site-solar"}] if self.exists else []
        if kind == "lovelace/config":
            if self.live is None:
                raise RuntimeError("lovelace/config failed: config_not_found No config found.")
            return self.live
        return {}

    def close(self) -> None:
        pass


def _run_save(monkeypatch, tmp_path, live, argv, exists=True):
    mod = _load("save_solar_plant_storage_dashboard")
    settings = mod._settings()
    fake = _FakeSession(live, exists)
    settings.Session = lambda *_a, **_k: fake
    monkeypatch.setattr(mod, "_settings", lambda: settings)
    code = mod.main(["--backup-dir", str(tmp_path), *argv])
    return code, fake


def test_save_refuses_to_overwrite_without_force(monkeypatch, tmp_path) -> None:
    live = {"views": [{"title": "My edits", "cards": []}]}
    code, fake = _run_save(monkeypatch, tmp_path, live, [])
    assert code == 3
    assert not any(c["type"] == "lovelace/config/save" for c in fake.calls)
    backups = list(tmp_path.glob("*/dashboard-site-solar.json"))
    assert len(backups) == 1
    assert json.loads(backups[0].read_text()) == live


def test_save_with_force_backs_up_then_saves(monkeypatch, tmp_path) -> None:
    live = {"views": [{"title": "My edits", "cards": []}]}
    code, fake = _run_save(monkeypatch, tmp_path, live, ["--force"])
    assert code == 0
    kinds = [c["type"] for c in fake.calls]
    assert kinds.index("lovelace/config") < kinds.index("lovelace/config/save")
    assert list(tmp_path.glob("*/dashboard-site-solar.json"))


def test_save_dry_run_writes_nothing(monkeypatch, tmp_path) -> None:
    code, fake = _run_save(monkeypatch, tmp_path, {"views": [{}]}, ["--force", "--dry-run"])
    assert code == 0
    assert not any(c["type"] == "lovelace/config/save" for c in fake.calls)


def test_save_creates_new_dashboard_without_force(monkeypatch, tmp_path) -> None:
    code, fake = _run_save(monkeypatch, tmp_path, None, [], exists=False)
    assert code == 0
    kinds = [c["type"] for c in fake.calls]
    assert "lovelace/dashboards/create" in kinds and "lovelace/config/save" in kinds


def test_decide() -> None:
    mod = _load("save_solar_plant_storage_dashboard")
    seed = {"views": [{"title": "a"}]}
    assert mod.decide(None, seed, False) == "save"
    assert mod.decide(seed, seed, False) == "same"
    assert mod.decide({"views": [{"title": "b"}]}, seed, False) == "refuse"
    assert mod.decide({"views": [{"title": "b"}]}, seed, True) == "save"


def test_installer_no_longer_rewrites_site_solar_storage() -> None:
    text = (ROOT / "scripts" / "install_solar_plant_ha.sh").read_text(encoding="utf-8")
    run_lines = [
        line
        for line in text.splitlines()
        if "sync_site_solar_storage_from_seed" in line and not line.strip().startswith("#")
    ]
    assert run_lines == []
    for script in ("install_solar_plant_ha.sh", "install_dump_control_ha.sh"):
        body = (ROOT / "scripts" / script).read_text(encoding="utf-8")
        assert "save_solar_plant_storage_dashboard.py\n" not in body.replace(" --force", "")


def test_sync_seed_script_refuses_without_force(tmp_path) -> None:
    mod = _load("sync_site_solar_storage_from_seed")
    storage = tmp_path / "lovelace.site_solar"
    storage.write_text('{"data": {"config": {"views": [{"title": "mine"}]}}}')
    assert mod.main(["--storage", str(storage)]) == 3
    assert "mine" in storage.read_text()


def test_no_timer_or_cron_reruns_save_scripts() -> None:
    names = (
        "save_solar_plant_storage_dashboard",
        "sync_site_solar_storage_from_seed",
        "create_h5082_socket_labels",
        "save_solar_plant_energy_prefs",
    )
    for unit in (ROOT / "systemd").rglob("*"):
        if unit.is_file():
            body = unit.read_text(encoding="utf-8", errors="ignore")
            assert not any(n in body for n in names), unit


def test_energy_prefs_refuse_ui_edits() -> None:
    mod = _load("save_solar_plant_energy_prefs")
    want = mod.energy_save_payload()
    assert mod.energy_decide({}, False) == "save"
    stored = json.loads(json.dumps(want))
    stored["energy_sources"][0]["stat_cost"] = None  # HA adds defaults
    assert mod.energy_decide(stored, False) == "same"
    edited = json.loads(json.dumps(want))
    edited["energy_sources"].append({"type": "grid"})
    assert mod.energy_decide(edited, False) == "refuse"
    assert mod.energy_decide(edited, True) == "save"


def test_settings_backup_covers_user_helpers_and_restores_safely() -> None:
    mod = _load("site_solar_settings")
    for eid in (
        "input_text.h5082_82fb_location",
        "input_text.h5082_82fb_left_load",
        "input_select.h5082_82fb_left_use",
        "input_select.h5082_82fb_left_inverter",
        "input_number.dump_float_t2_v",
        "input_boolean.dump_control_enabled",
        "input_text.dump_notify_service",
    ):
        assert mod.is_site_solar_helper(eid), eid
    assert not mod.is_site_solar_helper("switch.ihoment_h5082_82fb_left")
    live = {"state": "normal", "options": ["normal", "dump"]}
    assert mod.restore_action("input_select.h5082_82fb_left_use", {"state": "dump"}, live) == (
        "input_select",
        "select_option",
        {"option": "dump"},
    )
    assert mod.restore_action("input_select.x", {"state": "bogus"}, live) is None
    assert mod.restore_action("input_number.dump_float_t2_v", {"state": "27.1"}, {"state": "27.0"}) == (
        "input_number",
        "set_value",
        {"value": 27.1},
    )
    assert mod.restore_action("input_text.a", {"state": "unknown"}, {"state": "x"}) is None
    assert mod.restore_action("input_text.a", {"state": "x"}, {"state": "x"}) is None
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".backups/" in gitignore
    assert mod.DEFAULT_BACKUP_ROOT.relative_to(ROOT).parts[0] == ".backups"


# --------------------------------------------------------------- help per dump box


def _sections():
    seed = yaml.safe_load(SEED.read_text(encoding="utf-8"))
    for view in seed["views"]:
        for section in view.get("sections") or []:
            yield view.get("path"), section


def _is_dump_box(section: dict) -> bool:
    blob = json.dumps(section.get("cards") or [])
    heading = next((c.get("heading", "") for c in section["cards"] if c.get("type") == "heading"), "")
    return any(w in blob for w in ("input_number.dump_", "input_boolean.dump_", "dump_", "h5082")) and (
        heading not in ("House",)
    )


def _dump_boxes():
    return [(v, s) for v, s in _sections() if _is_dump_box(s)]


def _entity_ids(node) -> set[str]:
    out: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("entity", "entity_id") and isinstance(value, str):
                out.add(value)
            else:
                out |= _entity_ids(value)
    elif isinstance(node, list):
        for value in node:
            out |= _entity_ids(value)
    return out


def test_every_dump_box_has_a_help_card_with_its_own_doc() -> None:
    boxes = _dump_boxes()
    assert len(boxes) >= 15
    docs_linked: list[str] = []
    for _view, section in boxes:
        cards = section["cards"]
        assert cards[0]["type"] == "heading", cards[0]
        help_card = cards[1]
        assert help_card["type"] == "markdown", cards[0]["heading"]
        links = re.findall(r"\]\((https://[^)]+)\)", help_card["content"])
        assert len(links) == 1, cards[0]["heading"]
        assert links[0].startswith(DOC_BASE), links[0]
        name = links[0][len(DOC_BASE) :]
        assert name.endswith(".md") and "/" not in name
        assert (DOCS / name).is_file(), name
        docs_linked.append(name)
        # 1-3 sentences, each on its own line, then the link line.
        text_lines = [ln for ln in help_card["content"].strip().splitlines() if "](" not in ln]
        assert 1 <= len(text_lines) <= 3, cards[0]["heading"]
        # The help card sits above the box it explains.
        assert len(cards) >= 3
    assert len(docs_linked) == len(set(docs_linked)), "one doc per box"
    assert sorted(docs_linked) == sorted(p.name for p in DOCS.glob("*.md"))


def _generic(eid: str) -> set[str]:
    if "*" in eid:  # auto-entities filter: the doc names the pattern's prefix
        return {eid, eid.split("*", 1)[0]}
    g = re.sub(r"h5082_[0-9a-f]{4}", "h5082_<id>", eid)
    forms = {eid, g, re.sub(r"_(left|right)(?=_|$)", "_<side>", g)}
    m = re.match(r"(.+_)(t2|ku|sph)(_ok|_v|_w)?$", eid)
    if m:
        forms.add(m.group(1) + "t2" + (m.group(3) or ""))
        forms.add(m.group(1) + "*")
    return forms


def test_each_doc_explains_every_entity_in_its_box() -> None:
    for _view, section in _dump_boxes():
        help_card = section["cards"][1]
        name = re.findall(r"docs/site-solar/([^)]+)\)", help_card["content"])[0]
        doc = (DOCS / name).read_text(encoding="utf-8")
        for heading in ("## What this box is for", "## Recommended first test", "## Example"):
            assert heading in doc, (name, heading)
        assert "dump_control.yaml" in doc or "solar-plant.yaml" in doc, name
        for eid in _entity_ids(section["cards"][2:]):
            if eid.startswith("script."):
                continue
            assert any(f in doc for f in _generic(eid)), (name, eid)


def test_monitoring_logbook_covers_sockets_and_automations() -> None:
    logbooks = []
    for _view, section in _sections():
        for card in section["cards"]:
            if card.get("type") == "custom:auto-entities" and card["card"]["type"] == "logbook":
                logbooks.append([f["entity_id"] for f in card["filter"]["include"]])
    assert any(
        "switch.ihoment_h5082_*" in inc and "automation.dump_*" in inc for inc in logbooks
    ), logbooks


def test_automations_have_clear_aliases_descriptions_and_log_reasons() -> None:
    for auto in _pkg()["automation dump_load"]:
        # Fresh installs derive the entity id from the alias: keep automation.dump_*.
        assert auto["alias"].lower().startswith("dump"), auto["id"]
        assert len(auto["description"].split()) >= 15, auto["id"]
        blob = json.dumps(auto["actions"])
        if "switch.turn_" in blob:
            assert "logbook.log" in blob, auto["id"]
