"""Two H5082 bridges (Pi 4 + Pi 5): each owns only its allowlisted plugs.

No BlueZ and no broker: the MQTT client is a Mock and BLE is never opened.
"""

from __future__ import annotations

import asyncio
import json
import types
from pathlib import Path
from unittest.mock import Mock

import pytest

govee_main = pytest.importorskip("govee_h5082.__main__")
from govee_h5082.mqtt_bridge import (  # noqa: E402
    AVAIL_LEGACY,
    PLUGS,
    avail_topic,
    discovery_payload,
    discovery_topic,
    key_file_problem,
    load_keys,
    owner_topic,
    parse_owned,
    state_topic,
)

ROOT = Path(__file__).resolve().parents[1]
FAN = PLUGS[5][0]  # 82FB, heard best by the Pi 5
OTHER = PLUGS[0][0]  # 2F9D, stays on the Pi 4
TOKEN = "00112233445566778899aabbccddeeff"
PI4_PLUGS = "2F9D,3013,3EC9,9607,CF79,C061,C38D"


def _make(monkeypatch, *, listener=None, adapter=None, plugs=None, keys=None):
    monkeypatch.setenv("MQTT_HOST", "broker.invalid")
    monkeypatch.setenv("MQTT_USER", "u")
    monkeypatch.setenv("MQTT_PASSWORD", "p")
    for name, value in (
        ("H5082_LISTENER", listener),
        ("H5082_ADAPTER", adapter),
        ("H5082_PLUGS", plugs),
    ):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)
    monkeypatch.delenv("H5082_RSSI_ONLY", raising=False)
    found = {address: TOKEN for address, _name in PLUGS} if keys is None else keys
    monkeypatch.setattr(govee_main, "load_keys", lambda: dict(found))
    client = Mock()
    client.is_connected.return_value = True
    monkeypatch.setattr(govee_main.mqtt, "Client", lambda *_a, **_k: client)
    br = govee_main.Bridge()
    assert br._client is client
    return br


def _publishes(br):
    return [(c.args[0], c.args[1], c.kwargs) for c in br._client.publish.call_args_list]


def _discovery(br):
    return {
        topic: json.loads(payload)
        for topic, payload, _kw in _publishes(br)
        if topic.startswith("homeassistant/switch/")
    }


def _msg(topic, payload):
    return types.SimpleNamespace(topic=topic, payload=payload.encode())


# --- allowlist parsing -----------------------------------------------------------


def test_parse_owned_accepts_ids_macs_and_separators():
    assert parse_owned(None) is None
    assert parse_owned("  ") is None
    assert parse_owned("82fb") == {FAN}
    assert parse_owned("82FB, 2f9d") == {FAN, OTHER}
    assert parse_owned("82FB 2F9D") == {FAN, OTHER}
    assert parse_owned(FAN.lower()) == {FAN}
    assert parse_owned("all") == {address for address, _name in PLUGS}
    assert parse_owned("none") == set()
    assert len(parse_owned(PI4_PLUGS)) == 7
    assert FAN not in parse_owned(PI4_PLUGS)


def test_parse_owned_rejects_unknown_plug():
    with pytest.raises(ValueError, match="unknown H5082 plug 'BEEF'"):
        parse_owned("82FB,BEEF")


def test_topics():
    assert avail_topic(None) == AVAIL_LEGACY == "govee/h5082/bridge/status"
    assert avail_topic("pi5") == "govee/h5082/bridge/pi5/status"
    assert owner_topic(FAN) == "govee/h5082/d413686182fb/owner"
    address, name = PLUGS[5]
    assert discovery_payload(address, name, "left", "Left")["availability_topic"] == AVAIL_LEGACY
    assert (
        discovery_payload(address, name, "left", "Left", "govee/h5082/bridge/pi5/status")[
            "availability_topic"
        ]
        == "govee/h5082/bridge/pi5/status"
    )


# --- legacy (no allowlist) is exactly the old Pi 4 bridge ------------------------


def test_no_allowlist_keeps_pi4_behaviour(monkeypatch):
    br = _make(monkeypatch)
    assert br._adapter == "hci1" and br._listener == "pi4"
    assert br._avail == AVAIL_LEGACY
    br._client.will_set.assert_called_with(AVAIL_LEGACY, "offline", qos=1, retain=True)
    br.publish_config()
    found = _discovery(br)
    assert len(found) == 16
    assert {p["availability_topic"] for p in found.values()} == {AVAIL_LEGACY}
    topics = [t for t, _p, _k in _publishes(br)]
    assert AVAIL_LEGACY in topics
    assert not [t for t in topics if t.endswith("/owner")]  # no claims in legacy mode
    subs = [c.args[0] for c in br._client.subscribe.call_args_list]
    assert subs == ["govee/h5082/+/+/set"]
    assert br.describe().startswith("OWNS 2F9D 3013 3EC9 9607 CF79 82FB C061 C38D listener=pi4")


def test_timings_are_unchanged():
    assert govee_main.CONNECT_TIMEOUT_S == 20
    assert govee_main.ACK_TIMEOUT_S == 8
    assert govee_main.FIND_TIMEOUT_S == 20
    assert govee_main.RETRIES == 3
    assert govee_main.HOLD_S == 20


# --- owner mode --------------------------------------------------------------------


def test_pi5_owns_only_its_plug(monkeypatch):
    br = _make(monkeypatch, listener="pi5", adapter="hci0", plugs="82FB", keys={FAN: TOKEN})
    avail = "govee/h5082/bridge/pi5/status"
    assert br._avail == avail
    br._client.will_set.assert_called_with(avail, "offline", qos=1, retain=True)
    br.publish_config()
    found = _discovery(br)
    assert set(found) == {discovery_topic(FAN, "left"), discovery_topic(FAN, "right")}
    for payload in found.values():
        # Same command / state topics as the Pi 4 used: HA keeps the same entity.
        assert payload["availability_topic"] == avail
        assert payload["command_topic"].startswith("govee/h5082/d413686182fb/")
    pubs = _publishes(br)
    assert (avail, "online", {"qos": 1, "retain": True}) in pubs
    assert (owner_topic(FAN), "pi5", {"qos": 1, "retain": True}) in pubs
    assert AVAIL_LEGACY not in [t for t, _p, _k in pubs]
    subs = [c.args[0] for c in br._client.subscribe.call_args_list]
    assert subs == ["govee/h5082/+/+/set", "govee/h5082/+/owner"]
    # RSSI discovery is still published for every plug this Pi can hear.
    rssi = [t for t, _p, _k in pubs if t.startswith("homeassistant/sensor/")]
    assert len(rssi) == len(PLUGS)


def test_pi4_allowlist_drops_the_fan(monkeypatch):
    br = _make(monkeypatch, plugs=PI4_PLUGS)
    br.publish_config()
    found = _discovery(br)
    assert len(found) == 14
    assert discovery_topic(FAN, "left") not in found
    assert {p["availability_topic"] for p in found.values()} == {"govee/h5082/bridge/pi4/status"}
    assert "82FB" not in br.describe()


def test_foreign_plug_commands_are_ignored(monkeypatch, capsys):
    br = _make(monkeypatch, plugs=PI4_PLUGS)
    br._loop = Mock()
    sent = []
    monkeypatch.setattr(govee_main.asyncio, "run_coroutine_threadsafe", lambda coro, _l: sent.append(coro) or Mock())
    br._on_message(None, None, _msg("govee/h5082/d413686182fb/left/set", "ON"))
    assert sent == []
    assert "NOT_OWNER 82FB left" in capsys.readouterr().out

    br._on_message(None, None, _msg("govee/h5082/" + OTHER.replace(":", "").lower() + "/left/set", "ON"))
    assert len(sent) == 1
    sent[0].close()


def test_command_for_foreign_plug_never_touches_ble(monkeypatch, capsys):
    br = _make(monkeypatch, listener="pi5", adapter="hci0", plugs="82FB", keys={FAN: TOKEN})
    asyncio.run(br.command(OTHER, "right", True))
    assert br._workers == {} and br._links == {}
    assert "NOT_OWNER 2F9D right" in capsys.readouterr().out


def test_foreign_plug_advertisements_publish_no_state(monkeypatch):
    br = _make(monkeypatch, listener="pi5", adapter="hci0", plugs="82FB", keys={FAN: TOKEN})
    br.note_advertisement(OTHER, 3)
    br.note_advertisement(FAN, 2)
    topics = [t for t, _p, _k in _publishes(br)]
    assert state_topic(OTHER, "left") not in topics
    assert state_topic(FAN, "left") in topics


def test_owner_conflict_and_stale_claim_release(monkeypatch, capsys):
    br = _make(monkeypatch, plugs=PI4_PLUGS)
    fan_mac = FAN.replace(":", "").lower()
    other_mac = OTHER.replace(":", "").lower()
    # The Pi 5 claims the fan: fine, the Pi 4 does not own it.
    br._on_message(None, None, _msg(f"govee/h5082/{fan_mac}/owner", "pi5"))
    assert br._client.publish.call_count == 0
    # Our own retained claim from before the allowlist: released (empty retained).
    br._on_message(None, None, _msg(f"govee/h5082/{fan_mac}/owner", "pi4"))
    br._client.publish.assert_called_once_with(owner_topic(FAN), "", qos=1, retain=True)
    # Someone else claims a plug we own: loud warning, nothing deleted.
    br._on_message(None, None, _msg(f"govee/h5082/{other_mac}/owner", "pi5"))
    out = capsys.readouterr().out
    assert "OWNER_RELEASE 82FB" in out
    assert "OWNER_CONFLICT 2F9D also claimed by pi5" in out
    assert br._client.publish.call_count == 1
    # Empty (released) claims and junk topics are ignored.
    br._on_message(None, None, _msg(f"govee/h5082/{other_mac}/owner", ""))
    br._on_message(None, None, _msg("govee/h5082/xyz/owner", "pi5"))
    assert br._client.publish.call_count == 1


def test_startup_report_flags_missing_owned_key(monkeypatch, capsys):
    br = _make(monkeypatch, listener="pi5", adapter="hci0", plugs="82FB,C061", keys={FAN: TOKEN})
    br._key_problem = None
    br.startup_report()
    out = capsys.readouterr().out
    assert "OWNS 82FB C061 listener=pi5 adapter=hci0 mode=per-host" in out
    assert "NO_KEY_OWNED C061" in out
    assert "NO_KEY_OWNED 82FB" not in out
    assert TOKEN not in out


# --- adapter / listener rules ------------------------------------------------------


def test_pi4_must_stay_on_hci1(monkeypatch):
    with pytest.raises(SystemExit, match="hci1"):
        _make(monkeypatch, listener="pi4", adapter="hci0", plugs=PI4_PLUGS)


def test_pi5_adapter_is_configurable(monkeypatch):
    br = _make(monkeypatch, listener="pi5", adapter="hci1", plugs="82FB")
    assert br._adapter == "hci1"
    with pytest.raises(SystemExit, match="hciN"):
        _make(monkeypatch, listener="pi5", adapter="usb0", plugs="82FB")


def test_second_bridge_without_allowlist_refuses_to_start(monkeypatch):
    with pytest.raises(SystemExit, match="H5082_PLUGS is required on pi5"):
        _make(monkeypatch, listener="pi5", adapter="hci0")


def test_rssi_only_listener_needs_no_allowlist(monkeypatch):
    monkeypatch.setenv("H5082_RSSI_ONLY", "1")
    monkeypatch.setenv("H5082_LISTENER", "pi5")
    monkeypatch.setenv("H5082_ADAPTER", "hci0")
    monkeypatch.delenv("H5082_PLUGS", raising=False)
    monkeypatch.setenv("MQTT_HOST", "broker.invalid")
    monkeypatch.setenv("MQTT_USER", "u")
    monkeypatch.setenv("MQTT_PASSWORD", "p")
    monkeypatch.setattr(govee_main, "load_keys", dict)
    br = govee_main.Bridge()
    assert br._rssi_only


def test_unknown_plug_in_allowlist_refuses_to_start(monkeypatch):
    with pytest.raises(SystemExit, match="unknown H5082 plug"):
        _make(monkeypatch, listener="pi5", adapter="hci0", plugs="82FC")


# --- key file ----------------------------------------------------------------------


def test_key_path_env_and_mode_check(monkeypatch, tmp_path):
    keys = tmp_path / "keys"
    keys.write_text(f"{FAN} ihoment_H5082_82FB {TOKEN}\n")
    keys.chmod(0o644)
    monkeypatch.setenv("H5082_KEY_PATH", str(keys))
    assert load_keys() == {FAN: TOKEN}
    assert key_file_problem(str(keys)) == "mode 644, want 600"
    keys.chmod(0o600)
    assert key_file_problem(str(keys)) is None
    assert key_file_problem(str(tmp_path / "nope")) == "missing"


# --- units, install script, helper --------------------------------------------------


def _unit(name):
    return (ROOT / "systemd" / name).read_text()


def test_units_read_the_host_file_outside_git():
    pi4 = _unit("h5082-mqtt.service")
    assert "Environment=H5082_LISTENER=pi4" in pi4
    assert "Environment=H5082_ADAPTER=hci1" in pi4
    # Optional on the Pi 4 ("-"): no file = old behaviour.
    assert "EnvironmentFile=-/home/n4s1/.config/h5082-bridge.env" in pi4
    pi5 = _unit("h5082-mqtt-pi5.service")
    assert "Environment=H5082_LISTENER=pi5" in pi5
    assert "Environment=H5082_ADAPTER=hci0" in pi5
    assert "EnvironmentFile=/home/n4s1/.config/h5082-bridge.env" in pi5
    assert "hosts/pi5/mqtt.env" in pi5
    assert "H5082_RSSI_ONLY" not in pi5
    # The host file comes after Environment= so it can override the adapter.
    assert pi5.index("h5082-bridge.env") > pi5.index("H5082_ADAPTER=hci0")
    for text in (pi4, pi5):
        assert "H5082_PLUGS=" not in text  # ownership is per host, not in git


def test_install_script_dry_run_never_touches_keys():
    text = (ROOT / "scripts" / "install_h5082_bridge.sh").read_text()
    assert "--host pi4|pi5" in text
    assert "h5082-mqtt-pi5.service" in text
    assert "disable --now h5082-rssi-pi5" in text
    assert "cat \"$KEYS\"" not in text and "scp" not in text


def test_rssi_scan_helper_is_read_only_and_guards_victron(monkeypatch):
    import importlib.util  # noqa: PLC0415

    path = ROOT / "scripts" / "h5082_rssi_scan.py"
    spec = importlib.util.spec_from_file_location("h5082_rssi_scan", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.delenv("H5082_ADAPTER", raising=False)
    with pytest.raises(SystemExit):
        mod.parse_args(["--host", "pi4", "--adapter", "hci0"])
    with pytest.raises(SystemExit):
        mod.parse_args(["--host", "pi5"])  # adapter required
    args = mod.parse_args(["--host", "pi5", "--adapter", "hci0", "--seconds", "5"])
    assert (args.adapter, args.seconds) == ("hci0", 5.0)
    tally = mod.Tally()
    tally.add(FAN.lower(), -59, 10.0)
    tally.add(FAN, -55, 12.0)
    tally.add("AA:BB:CC:DD:EE:FF", -40, 12.0)  # not a plug
    rows = tally.rows(15.0)
    fan_row = next(r for r in rows if r.startswith("82FB"))
    assert fan_row.split() == ["82FB", "2", "-55", "-57.0", "3s"]
    assert next(r for r in rows if r.startswith("2F9D")).split()[1] == "0"
    source = path.read_text()
    assert "connect(" not in source and "write_gatt_char" not in source
    assert ".govee-h5082-keys" not in source


# --- bleak versions (Pi 5 got bleak 3.0.2; the Pi 4 venv may be older) -------------


def test_adapter_kwargs_pin_the_adapter_on_old_and_new_bleak():
    kwargs = govee_main.adapter_kwargs
    assert kwargs("hci0", "3.0.2") == {"bluez": {"adapter": "hci0"}}
    assert kwargs("hci1", "4.1") == {"bluez": {"adapter": "hci1"}}
    # bleak < 3 ignores bluez={"adapter"} and would fall back to hci0 (Victron).
    assert kwargs("hci1", "0.22.3") == {"adapter": "hci1"}
    assert kwargs("hci1", "2.1.1") == {"adapter": "hci1"}
    assert kwargs("hci1", "missing") == {"bluez": {"adapter": "hci1"}}


def test_install_script_checks_the_venv_before_systemd():
    text = (ROOT / "scripts" / "install_h5082_bridge.sh").read_text()
    assert "import bleak, paho.mqtt, dbus_fast" in text
    assert "pip install bleak paho-mqtt" in text
    assert text.index("import bleak") < text.index("systemctl daemon-reload")
