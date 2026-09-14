import importlib.util
from pathlib import Path


def _load_instant_readout():
    path = Path(__file__).resolve().parents[1] / "override/victron_ble2mqtt/instant_readout.py"
    spec = importlib.util.spec_from_file_location("victron_instant_readout", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_prepare_seen_data_skips_within_throttle():
    mod = _load_instant_readout()
    seen = {b"\x10abc"}
    ok = mod.prepare_seen_data_for_republish(
        payload=b"\x10abc",
        seen_data=seen,
        last_pub=10.0,
        now=11.0,
        pub_gap=3.0,
    )
    assert ok is False
    assert b"\x10abc" in seen


def test_prepare_seen_data_discards_after_throttle():
    mod = _load_instant_readout()
    seen = {b"\x10abc"}
    ok = mod.prepare_seen_data_for_republish(
        payload=b"\x10abc",
        seen_data=seen,
        last_pub=10.0,
        now=14.0,
        pub_gap=3.0,
    )
    assert ok is True
    assert b"\x10abc" not in seen
