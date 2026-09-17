"""End-to-end watt hops from panel current/power through conversion losses.

Keep a copy in victron-ble2mqtt-integration/scripts/solar_watt_ledger.py.

Battery charge is storage, not loss. KU Victron / PWM D/C is unmetered, so the
combined loss total is incomplete until those strings have HA power.

Formula source: victron docs/SOLAR_POWER_BALANCE.md. SmartShunt sign:
https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html
SPH energy split: reprint §4.1 AC INPUT + PV vs battery input + INV OUTPUT LOAD.
"""

from __future__ import annotations

from typing import Any

_SOLAR_IDS = (
    "sensor.solar_controller_solar_power",
    "sensor.solar_controller_solar",
)
_CHARGE_IDS = ("sensor.solar_controller_charging_power",)
_MPPT_LOAD_IDS = ("sensor.solar_controller_load_power",)
_MPPT_V_IDS = ("sensor.solar_controller_battery",)
_MPPT_A_IDS = ("sensor.solar_controller_battery_charging",)
_BATT1_W_IDS = ("sensor.battery_1_power",)
_BATT1_V_IDS = ("sensor.battery_1_voltage", "sensor.battery_1_battery_voltage")
_BATT1_A_IDS = ("sensor.battery_1_current", "sensor.battery_1_battery_current")
_BATT2_W_IDS = ("sensor.battery_2_power",)
_BATT2_V_IDS = ("sensor.battery_2_voltage", "sensor.battery_2_battery_voltage")
_BATT2_A_IDS = ("sensor.battery_2_current", "sensor.battery_2_battery_current")
_A3_IDS = ("sensor.em16_a3_power",)
_A3_V_IDS = ("sensor.em16_a3_voltage",)
_A3_A_IDS = ("sensor.em16_a3_current",)
_B3_IDS = ("sensor.em16_b3_power",)
_SG_PV_IDS = ("sensor.sungold_sph302480a_pv_power",)
_SG_PV_V_IDS = ("sensor.sungold_sph302480a_pv_voltage",)
_SG_PV_A_IDS = ("sensor.sungold_sph302480a_pv_current",)
_SG_BATT_IDS = ("sensor.sungold_sph302480a_charging_power",)
_SG_LOAD_IDS = (
    "sensor.sungold_sph302480a_load_active_power",
    "sensor.sungold_sph302480a_load_power",
)
_SG_GRID_V_IDS = ("sensor.sungold_sph302480a_grid_voltage",)
_SG_GRID_A_IDS = ("sensor.sungold_sph302480a_grid_current",)


def _parse_float_state(state_row: dict[str, Any] | None) -> float | None:
    if not state_row:
        return None
    raw = str(state_row.get("state") or "").strip().lower()
    if raw in ("unavailable", "unknown", "", "none", "nan"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _first_w(states: dict[str, dict[str, Any]], entity_ids: tuple[str, ...]) -> float | None:
    for eid in entity_ids:
        val = _parse_float_state(states.get(eid))
        if val is not None:
            return val
    return None


def _va_w(v: float | None, a: float | None) -> float | None:
    if v is None or a is None:
        return None
    return abs(v * a)


_KU_UNMETERED_PV_REASON = (
    "KU combined PV lower bound uses A3 A/C as KU Renogy DC proxy "
    "(DC in >= AC out; no invented efficiency); each charger tile is "
    "equal 1/3 by suitcase count (est. only; PWM likely less than MPPT); "
    "not ha_solar_entity"
)


def ku_unmetered_pv_residual(
    batt2_w: float | None,
    jumper_w: float | None,
    ku_renogy_dc_w: float | None,
) -> float | None:
    """Combined KU Victron 2+3 + PWM D/C from shunt balance.

    batt2_W ≈ KU_PV + jumper_into_KU - KU_Renogy_DC
    jumper_w is signed T2 to KU positive (solar_W - T2_Renogy - batt1_W).
    SmartShunt +charge / -discharge:
    https://www.victronenergy.com/media/pg/SmartShunt/en/operation.html

    Returns None when any term is missing. Live site has no KU Renogy DC clamp;
    callers may pass trailer A/C (|A3|) as a **lower bound** for KU_Renogy_DC
    (inverter DC in >= AC out). Do not invent efficiency. Do not substitute 0
    when A/C is missing.
    """
    if batt2_w is None or jumper_w is None or ku_renogy_dc_w is None:
        return None
    return batt2_w - jumper_w + ku_renogy_dc_w


KU_EQUAL_SHARE_CHARGERS = 3


def ku_equal_share_w(combined_pv_w: float | None) -> float | None:
    """Equal 1/3 of combined KU PV. Two MPPT + one PWM, two suitcases each.

    Not (batt2 + load) / 3 -- that drops the jumper. PWM likely harvests less
    than MPPT (Victron 81 W vs 100 W at 25 C) but there is no site derate.
    https://www.victronenergy.com/upload/documents/Technical-Information-Which-solar-charge-controller-PWM-or-MPPT.pdf
    """
    if combined_pv_w is None:
        return None
    return combined_pv_w / float(KU_EQUAL_SHARE_CHARGERS)


def ku_est_amps(watts: float | None, volts: float | None) -> float | None:
    if watts is None or volts is None or volts == 0:
        return None
    return watts / volts


_CONVERSION_HOP_IDS = frozenset({"t2_mppt", "sungold"})
_DC_VDROP_HOP_IDS = frozenset({"t2_mppt_vdrop", "t2_ku_jumper"})
_AC_VDROP_HOP_IDS = frozenset({"ac_a3_uti"})


def _vdrop_fields(
    v_up: float | None,
    v_down: float | None,
    current: float | None,
) -> tuple[float | None, float | None, bool]:
    """Metered ΔV and conductor loss. Incomplete when V or I is missing.

    Victron Wiring Unlimited §2.7: V = I×R; cable loss P = I²R.
    With both-end voltages, ΔV = V_up − V_down and P ≈ |ΔV × I|
    (same as I²R when ΔV = I×R). Never invent AWG or length.
    https://www.victronenergy.com/media/pg/The_Wiring_Unlimited_book/en/theory.html
    """
    if v_up is None or v_down is None:
        return None, None, True
    delta = v_up - v_down
    if delta < 0:
        return 0.0, 0.0 if current is not None else None, False
    abs_dv = abs(delta)
    if current is None:
        return abs_dv, None, True
    return abs_dv, abs(abs_dv * current), False


def _hop(
    hop_id: str,
    label: str,
    watts_in: float | None,
    watts_out: float | None,
    *,
    stored_w: float | None = None,
    note: str = "",
    unmetered: bool = False,
    vdrop_v: float | None = None,
    vdrop_loss_w: float | None = None,
    vdrop_incomplete: bool = False,
    bus: str = "",
) -> dict[str, Any]:
    loss_w: float | None = None
    if not unmetered and watts_in is not None and watts_out is not None and stored_w is None:
        raw = watts_in - watts_out
        if raw < 0:
            note = note or "meter disagree"
            loss_w = 0.0
        else:
            loss_w = raw
    return {
        "id": hop_id,
        "label": label,
        "watts_in": watts_in,
        "watts_out": watts_out,
        "loss_w": loss_w,
        "stored_w": stored_w,
        "unmetered": unmetered,
        "note": note,
        "vdrop_v": vdrop_v,
        "vdrop_loss_w": vdrop_loss_w,
        "vdrop_incomplete": vdrop_incomplete,
        "bus": bus,
    }


def build_watt_ledger(states: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Panel current/power in, then per-hop in/out. Combined loss is metered conversion only."""
    t2_v = _first_w(states, _MPPT_V_IDS)
    t2_a = _first_w(states, _MPPT_A_IDS)
    t2_pv = _first_w(states, _SOLAR_IDS)
    if t2_pv is None:
        t2_pv = _va_w(t2_v, t2_a)

    mppt_charge = _first_w(states, _CHARGE_IDS)
    mppt_load = _first_w(states, _MPPT_LOAD_IDS)

    batt1 = _first_w(states, _BATT1_W_IDS)
    if batt1 is None:
        b1v = _first_w(states, _BATT1_V_IDS)
        b1a = _first_w(states, _BATT1_A_IDS)
        if b1v is not None and b1a is not None:
            batt1 = b1v * b1a

    batt2 = _first_w(states, _BATT2_W_IDS)
    if batt2 is None:
        b2v = _first_w(states, _BATT2_V_IDS)
        b2a = _first_w(states, _BATT2_A_IDS)
        if b2v is not None and b2a is not None:
            batt2 = b2v * b2a

    jumper_w: float | None = None
    if t2_pv is not None and batt1 is not None:
        jumper_w = t2_pv - batt1

    jumper_flowing = jumper_w is not None and abs(jumper_w) >= 1.0
    mppt_out: float | None = None
    mppt_note = "solar in vs charge plus MPPT load out"
    if mppt_charge is not None and (mppt_charge > 0.5 or not jumper_flowing):
        mppt_out = mppt_charge + (mppt_load or 0.0)
    elif jumper_flowing:
        mppt_note = "MPPT charge 0/missing with jumper; skip conversion loss"

    a3 = _first_w(states, _A3_IDS)
    a3_v = _first_w(states, _A3_V_IDS)
    a3_a = _first_w(states, _A3_A_IDS)
    b3 = _first_w(states, _B3_IDS)
    trailer_w: float | None = None
    if b3 is not None and abs(b3) >= 0.5:
        trailer_w = abs(b3)
    elif a3 is not None:
        trailer_w = abs(a3)

    sg_grid_v = _first_w(states, _SG_GRID_V_IDS)
    sg_grid_a = _first_w(states, _SG_GRID_A_IDS)
    sg_ac_in = _va_w(sg_grid_v, sg_grid_a)
    vent_fan_w: float | None = None
    vent_unmetered = False
    if trailer_w is not None and sg_ac_in is not None:
        vent_fan_w = max(0.0, trailer_w - sg_ac_in)
    else:
        vent_unmetered = True

    sg_pv = _first_w(states, _SG_PV_IDS)
    if sg_pv is None:
        sg_pv = _va_w(_first_w(states, _SG_PV_V_IDS), _first_w(states, _SG_PV_A_IDS))
    sg_batt = _first_w(states, _SG_BATT_IDS)
    sg_load = _first_w(states, _SG_LOAD_IDS)

    b1v = _first_w(states, _BATT1_V_IDS)
    b2v = _first_w(states, _BATT2_V_IDS)
    mppt_dv, mppt_vdw, mppt_vd_inc = _vdrop_fields(t2_v, b1v, t2_a)
    jumper_dv, jumper_vdw, jumper_vd_inc = _vdrop_fields(b1v, b2v, None)
    ac_dv, ac_vdw, ac_vd_inc = _vdrop_fields(a3_v, sg_grid_v, a3_a if a3_a is not None else sg_grid_a)

    hops: list[dict[str, Any]] = []
    hops.append(_hop("t2_mppt", "T2 MPPT", t2_pv, mppt_out, note=mppt_note, vdrop_v=mppt_dv, vdrop_loss_w=mppt_vdw, vdrop_incomplete=mppt_vd_inc, bus="dc"))

    hops.append(
        _hop(
            "t2_battery",
            "Battery 1 T2",
            None,
            None,
            stored_w=batt1,
            note="SmartShunt net; +charge / -discharge (not conversion loss)",
        )
    )

    jumper_abs = abs(jumper_w) if jumper_w is not None else None
    jumper_note = "estimate solar_W - batt1_W; no jumper clamp"
    if jumper_w is not None and jumper_w > 0:
        jumper_note = "T2 to KU; " + jumper_note
    elif jumper_w is not None and jumper_w < 0:
        jumper_note = "KU to T2; " + jumper_note
    hops.append(
        _hop(
            "t2_ku_jumper",
            "T2-KU jumper",
            jumper_abs,
            jumper_abs,
            note=jumper_note,
            vdrop_v=jumper_dv,
            vdrop_loss_w=jumper_vdw,
            vdrop_incomplete=jumper_vd_inc,
            bus="dc",
        )
    )

    hops.append(
        _hop(
            "ku_victron_pwm",
            "KU Victron + PWM D/C",
            None,
            None,
            unmetered=True,
            note=_KU_UNMETERED_PV_REASON,
        )
    )

    hops.append(
        _hop(
            "ku_battery",
            "Battery 2 KU",
            None,
            None,
            stored_w=batt2,
            note="SmartShunt net; +charge / -discharge; load line is KU Renogy A/C est",
        )
    )

    hops.append(
        _hop(
            "ku_renogy_ac",
            "KU Renogy A/C",
            trailer_w,
            trailer_w,
            note="est. from A3/B3 trailer A/C (no DC clamp); DC in >= AC out; Battery 2 load uses this same W",
        )
    )

    hops.append(
        _hop(
            "trailer_outlet",
            "Trailer outlet",
            trailer_w,
            (sg_ac_in + vent_fan_w) if (sg_ac_in is not None and vent_fan_w is not None) else None,
            note="A3/B3 hot leg splits to Sungold A/C in and cargo-trailer vent fan",
        )
    )
    hops.append(
        _hop(
            "vent_fan",
            "Trailer vent fan",
            vent_fan_w,
            vent_fan_w,
            unmetered=vent_unmetered,
            note=(
                "max(0, trailer_outlet_W - SPH A/C INPUT); sibling of Sungold on KU outlet"
                if not vent_unmetered
                else "unmetered sibling load on trailer outlet; A3 is not Sungold-only"
            ),
        )
    )

    sg_in: float | None = None
    sg_out: float | None = None
    if sg_ac_in is not None:
        sg_in = sg_ac_in + (sg_pv or 0.0)
        if sg_batt is not None or sg_load is not None:
            sg_out = (sg_batt or 0.0) + (sg_load or 0.0)
    hops.append(
        _hop(
            "sungold",
            "Sungold SPH",
            sg_in,
            sg_out,
            note="SPH A/C INPUT (V*A) + PV minus (battery input + A/C out); not A3",
        )
    )
    hops.append(
        _hop(
            "ac_a3_uti",
            "A/C trailer to SPH",
            sg_ac_in,
            sg_ac_in,
            note="SPH A/C INPUT branch only; A3 residual is vent fan, not this hop loss",
            vdrop_v=ac_dv,
            vdrop_loss_w=ac_vdw,
            vdrop_incomplete=ac_vd_inc,
            bus="ac",
        )
    )
    hops.append(
        _hop(
            "pi4",
            "Pi4 on SPH A/C out",
            sg_load,
            sg_load,
            unmetered=True,
            note="always-on Victron BLE radio; no HA watt entity; not a sim dump plug",
        )
    )

    combined = 0.0
    for hop in hops:
        if hop.get("id") not in _CONVERSION_HOP_IDS:
            continue
        loss = hop.get("loss_w")
        if isinstance(loss, (int, float)):
            combined += float(loss)

    vdrop_dc = 0.0
    vdrop_ac = 0.0
    vdrop_w = 0.0
    vdrop_incomplete = False
    for hop in hops:
        dv = hop.get("vdrop_v")
        if hop.get("vdrop_incomplete"):
            vdrop_incomplete = True
        if isinstance(dv, (int, float)):
            if hop.get("bus") == "dc":
                vdrop_dc += float(dv)
            elif hop.get("bus") == "ac":
                vdrop_ac += float(dv)
        vl = hop.get("vdrop_loss_w")
        if isinstance(vl, (int, float)):
            vdrop_w += float(vl)
        elif hop.get("vdrop_v") is not None and hop.get("vdrop_loss_w") is None:
            vdrop_incomplete = True

    path_total = combined + vdrop_w
    panel_parts = [p for p in (t2_pv, sg_pv) if p is not None]
    panel_in = sum(panel_parts) if panel_parts else None
    ku_pv = ku_unmetered_pv_residual(batt2, jumper_w, trailer_w)
    ku_share = ku_equal_share_w(ku_pv)

    return {
        "watt_hops": hops,
        "combined_losses_w": combined,
        "combined_vdrop_v": vdrop_dc,
        "combined_vdrop_ac_v": vdrop_ac,
        "combined_vdrop_loss_w": vdrop_w,
        "combined_path_losses_w": path_total,
        "combined_losses_incomplete": True,
        "combined_vdrop_incomplete": vdrop_incomplete,
        "panel_in_w": panel_in,
        "jumper_w": jumper_w,
        "trailer_outlet_w": trailer_w,
        "sungold_ac_in_w": sg_ac_in,
        "vent_fan_w": vent_fan_w,
        "ku_renogy_ac_est_w": trailer_w,
        "ku_unmetered_pv_est_w": ku_pv,
        "ku_unmetered_pv_est_kind": (
            "ac_lower_bound" if trailer_w is not None else None
        ),
        "ku_charger_equal_share_w": ku_share,
        "ku_charger_equal_share_a": ku_est_amps(ku_share, b2v),
    }


def apply_ledger_to_meta(
    meta: dict[str, Any],
    states: dict[str, dict[str, Any]],
    surplus: float | None,
) -> float | None:
    """Copy hop ledger onto dump-tick meta. Returns surplus minus combined conversion losses."""
    ledger = build_watt_ledger(states)
    meta["watt_hops"] = ledger["watt_hops"]
    meta["combined_losses_w"] = ledger["combined_losses_w"]
    meta["combined_vdrop_v"] = ledger["combined_vdrop_v"]
    meta["combined_vdrop_ac_v"] = ledger["combined_vdrop_ac_v"]
    meta["combined_vdrop_loss_w"] = ledger["combined_vdrop_loss_w"]
    meta["combined_path_losses_w"] = ledger["combined_path_losses_w"]
    meta["combined_losses_incomplete"] = ledger["combined_losses_incomplete"]
    meta["combined_vdrop_incomplete"] = ledger["combined_vdrop_incomplete"]
    meta["panel_in_w"] = ledger["panel_in_w"]
    meta["jumper_w"] = ledger["jumper_w"]
    meta["trailer_outlet_w"] = ledger["trailer_outlet_w"]
    meta["sungold_ac_in_w"] = ledger["sungold_ac_in_w"]
    meta["vent_fan_w"] = ledger["vent_fan_w"]
    meta["ku_renogy_ac_est_w"] = ledger["ku_renogy_ac_est_w"]
    meta["ku_unmetered_pv_est_w"] = ledger["ku_unmetered_pv_est_w"]
    meta["ku_unmetered_pv_est_kind"] = ledger["ku_unmetered_pv_est_kind"]
    meta["ku_charger_equal_share_w"] = ledger["ku_charger_equal_share_w"]
    meta["ku_charger_equal_share_a"] = ledger["ku_charger_equal_share_a"]
    path_losses = float(ledger.get("combined_path_losses_w") or 0.0)
    if surplus is None:
        meta["surplus_after_path_losses_w"] = None
        return None
    after = surplus - path_losses
    meta["surplus_after_path_losses_w"] = after
    return after
