"""Replay Site solar identities from the 21 Sep 2026 shot (no live HA)."""

from __future__ import annotations

import sys
from math import isclose
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from solar_watt_ledger import ku_equal_share_w, ku_unmetered_pv_residual  # noqa: E402


def test_21_sep_shot_git_identities() -> None:
    t2_solar = 227.6
    batt1_v = 27.9
    batt1_a = 1.5
    batt1_w = batt1_v * batt1_a
    sph_pv = 107.2
    sph_ac_out = 324.8
    sph_ac_out_v = 120.4
    sph_ac_out_a = 2.7
    batt2_w = -75.2
    batt2_v = 26.6
    batt2_a = -2.8
    a3_w = -62.5
    b3_w = 0.0
    trailer = abs(b3_w) if abs(b3_w) >= 0.5 else abs(a3_w)

    jumper = t2_solar - batt1_w
    jumper_at_t2 = -jumper
    ku_est = ku_unmetered_pv_residual(batt2_w, jumper, trailer)
    ku_share = ku_equal_share_w(ku_est)
    site_solar = t2_solar + sph_pv + max(ku_est or 0.0, 0.0)
    site_charge = max(batt1_w, 0.0) + max(batt2_w, 0.0) + max(0.0, 0.0)
    site_load = sph_ac_out

    assert isclose(batt1_w, 41.85, rel_tol=1e-4)
    assert isclose(abs(sph_ac_out_v * sph_ac_out_a), 325.08, rel_tol=1e-4)
    assert isclose(abs(sph_ac_out_v * sph_ac_out_a - sph_ac_out), 0.28, abs_tol=0.3)
    assert isclose(batt2_v * batt2_a, -74.48, rel_tol=1e-3)
    assert isclose(jumper, 185.75, rel_tol=1e-3)
    assert isclose(jumper_at_t2, -185.75, rel_tol=1e-3)
    assert trailer == 62.5
    assert ku_est is not None
    assert isclose(ku_est, -198.45, rel_tol=1e-3)
    assert ku_share is not None
    assert isclose(ku_share, ku_est / 3.0, rel_tol=1e-6)
    assert isclose(site_solar, 334.8, rel_tol=1e-3)
    assert isclose(site_charge, batt1_w, rel_tol=1e-6)
    assert site_load == sph_ac_out
    # Shunt-to-shunt: jumper is already in both nets; lossless transfer cancels
    # in batt1+batt2 and is not an extra Solar/Charge/Load addend.
    assert ku_est is not None
    assert isclose(batt1_w + batt2_w, t2_solar + ku_est - trailer, rel_tol=1e-6)
    assert isclose(site_solar, t2_solar + sph_pv, rel_tol=1e-6)
    assert jumper not in (site_solar, site_charge, site_load)

    shot_load_now = 656.5
    shot_solar_now = 147.0
    shot_ku_pv = 136.1
    shot_ku_share = 136.1
    shot_ac_in = 653.4
    shot_jumper_ku = 248.3
    assert shot_load_now != site_load
    assert shot_solar_now != site_solar
    assert shot_ku_pv != ku_est
    assert shot_ku_share == shot_ku_pv
    assert shot_ku_share != ku_share
    assert shot_ac_in != trailer
    assert shot_jumper_ku != jumper
    instant_w_sum = t2_solar + sph_ac_out + sph_pv
    assert isclose(instant_w_sum, 659.6, rel_tol=1e-4)
    assert isclose(shot_load_now, shot_ac_in, abs_tol=4.0)
