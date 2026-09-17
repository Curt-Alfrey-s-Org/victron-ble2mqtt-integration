#!/usr/bin/env python3
"""Solar-flow LAN dashboard: static files + GET /api/snapshot from Home Assistant REST.

Official:
  HA REST: https://developers.home-assistant.io/docs/api/rest/
  http.server: https://docs.python.org/3/library/http.server.html
  urllib.request: https://docs.python.org/3/library/urllib.request.html

Token stays server-side (HA_TOKEN, HA_TOKEN_FILE, or HA_LONG_LIVED_TOKEN_FILE).
Default bind 127.0.0.1:8765; use --lan for 0.0.0.0 (operator LAN only).
"""
from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlparse
from urllib.request import Request, urlopen

from solar_watt_ledger import apply_ledger_to_meta

ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web" / "solar-flow"
DEMO_SNAPSHOT = WEB_ROOT / "demo-snapshot.json"

_SIM_PLUG_ALLOWLIST = (
    "switch.sim_ac_plug_1,switch.sim_ac_plug_2,switch.sim_ac_plug_3,"
    "switch.sim_ac_plug_4,switch.sim_ac_plug_5,switch.sim_ac_plug_6"
)
_SIM_PLUG_WATTS = (
    "switch.sim_ac_plug_1=180,switch.sim_ac_plug_2=300,switch.sim_ac_plug_3=1200,"
    "switch.sim_ac_plug_4=130,switch.sim_ac_plug_5=130,switch.sim_ac_plug_6=300"
)
# HA template aggregate; 0 plant AC load until a real KU house EM16 channel is configured.
_SIM_DUMP_LOAD_ENTITY = "sensor.sim_dump_load_power"
_LEGACY_SIM_DUMP_LOAD_ENTITY = "sensor.sim_soak_load_power"
# Sim dump load entity prefixes (HA package or demo-file fallback for missing ids).
_SIM_DUMP_ENTITY_PREFIXES: tuple[str, ...] = (
    "switch.sim_ac_plug_",
    "sensor.sim_ac_plug_",
    "sensor.sim_dump_",
    "sensor.sim_soak_",
)

DEFAULT_SETTINGS: dict[str, str] = {
    "ha_solar_dump_enabled": "true",
    "ha_switch_allowlist": _SIM_PLUG_ALLOWLIST,
    "ha_switch_watts": _SIM_PLUG_WATTS,
    "ha_never_auto": "",
    "ha_solar_entity": "sensor.solar_controller_solar_power",
    "ha_load_entity": _SIM_DUMP_LOAD_ENTITY,
    "ha_soc_entity": "sensor.battery_1_soc",
    "ha_shunt_voltage_entity": "sensor.battery_1_voltage",
    "ha_shunt_current_entity": "sensor.battery_1_current",
    "ha_soc_unsynced": "true",
    "ha_charge_state_entity": "sensor.solar_controller_battery_state",
    "ha_charge_states_ok": "float,absorption",
    "ha_min_soc_percent": "85",
    "ha_min_surplus_watts": "200",
    "ha_off_surplus_watts": "50",
    "ha_max_concurrent_on": "6",
    "ha_min_on_seconds": "600",
    "ha_min_off_seconds": "300",
}

# Lovelace / MQTT names that differ from dump-load canonical ids.
# Live Solar dashboard uses sensor.solar_controller_solar (tests/test_ha_label_victron_refoss.py).
# MQTT discovery names: Solar power, Battery state, State of charge
# (override/victron_ble2mqtt/mqtt.py SolarChargerHandler / BatteryMonitorHandler).
# Sungold live ids: scripts/ha_label_sungold_solar.py + .105 entity registry 16 Sep 2026.
ENTITY_ALIASES: dict[str, tuple[str, ...]] = {
    "sensor.solar_controller_solar_power": ("sensor.solar_controller_solar",),
    "sensor.solar_controller_battery_state": ("sensor.solar_controller_charge_state",),
    "sensor.battery_1_soc": ("sensor.battery_1_state_of_charge",),
    "sensor.battery_2_soc": ("sensor.battery_2_state_of_charge",),
    "sensor.battery_1_voltage": ("sensor.battery_1_battery_voltage",),
    "sensor.battery_2_voltage": ("sensor.battery_2_battery_voltage",),
    "sensor.battery_1_current": ("sensor.battery_1_battery_current",),
    "sensor.battery_2_current": ("sensor.battery_2_battery_current",),
    "sensor.sungold_sph302480a_load_power": (
        "sensor.sungold_sph302480a_load_active_power",
    ),
    "sensor.sim_dump_load_power": ("sensor.sim_soak_load_power",),
}

# Snapshot includes every HA row under these prefixes (not only REQUIRED).
# input_boolean.sim_ac_plug_*_internal is excluded (duplicates the switches).
SNAPSHOT_PREFIXES: tuple[str, ...] = (
    "sensor.solar_controller_",
    "sensor.battery_1_",
    "sensor.battery_2_",
    "sensor.em16_",
    "sensor.sungold_sph302480a_",
    "binary_sensor.sungold_sph302480a_",
    "sensor.sim_ac_plug_",
    "sensor.sim_dump_",
    "sensor.sim_soak_",  # leftover HA unique_id; never printed in UI copy
    "switch.sim_ac_plug_",
)

REQUIRED_ENTITY_IDS: frozenset[str] = frozenset(
    [
        "sensor.solar_controller_solar_power",
        "sensor.solar_controller_battery_state",
        "sensor.solar_controller_battery",
        "sensor.solar_controller_battery_charging",
        "sensor.solar_controller_charging_power",
        "sensor.solar_controller_load",
        "sensor.solar_controller_load_power",
        "sensor.solar_controller_yield_today",
        "sensor.solar_controller_rssi",
        "sensor.em16_a3_power",
        "sensor.em16_a3_voltage",
        "sensor.em16_a3_current",
        "sensor.battery_1_soc",
        "sensor.battery_1_voltage",
        "sensor.battery_1_current",
        "sensor.battery_1_power",
        "sensor.battery_1_consumed_ah",
        "sensor.battery_1_remaining_minutes",
        "sensor.battery_2_soc",
        "sensor.battery_2_voltage",
        "sensor.battery_2_current",
        "sensor.battery_2_power",
        "sensor.battery_2_consumed_ah",
        "sensor.battery_2_remaining_minutes",
        "sensor.sungold_sph302480a_pv_power",
        "sensor.sungold_sph302480a_pv_voltage",
        "sensor.sungold_sph302480a_pv_current",
        "sensor.sungold_sph302480a_battery_soc",
        "sensor.sungold_sph302480a_battery_voltage",
        "sensor.sungold_sph302480a_battery_current",
        "sensor.sungold_sph302480a_charging_power",
        "sensor.sungold_sph302480a_charge_state",
        "sensor.sungold_sph302480a_grid_voltage",
        "sensor.sungold_sph302480a_grid_current",
        "sensor.sungold_sph302480a_load_power",
        "sensor.sungold_sph302480a_inverter_state",
        "switch.sim_ac_plug_1",
        "switch.sim_ac_plug_2",
        "switch.sim_ac_plug_3",
        "switch.sim_ac_plug_4",
        "switch.sim_ac_plug_5",
        "switch.sim_ac_plug_6",
        "sensor.sim_ac_plug_1_power",
        "sensor.sim_ac_plug_2_power",
        "sensor.sim_ac_plug_3_power",
        "sensor.sim_ac_plug_4_power",
        "sensor.sim_ac_plug_5_power",
        "sensor.sim_ac_plug_6_power",
        "sensor.sim_dump_load_power",
    ]
)

DumpDecision = tuple[str, Literal["on", "off", "skip"], str]

logger = logging.getLogger("solar_flow_server")

# Proxy-only history window cap in hours (not HA recorder purge_keep_days).
HISTORY_HOURS_MAX = 10
HISTORY_RECORDER_DISABLED_MSG = (
    "HA recorder or history integration is not enabled"
)


def _parse_entity_list(raw: str) -> frozenset[str]:
    if not (raw or "").strip():
        return frozenset()
    out: set[str] = set()
    for part in raw.split(","):
        token = part.strip()
        if token:
            out.add(token)
    return frozenset(out)


def _parse_switch_watts(raw: str) -> dict[str, int]:
    if not (raw or "").strip():
        return {}
    out: dict[str, int] = {}
    for part in raw.split(","):
        token = part.strip()
        if not token or "=" not in token:
            continue
        eid_raw, watts_raw = token.split("=", 1)
        eid = eid_raw.strip()
        try:
            watts = int(watts_raw.strip())
        except ValueError:
            continue
        if watts < 0 or watts > 100000:
            continue
        out[eid] = watts
    return out


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


def _entity_is_on(state_row: dict[str, Any] | None) -> bool:
    if not state_row:
        return False
    return str(state_row.get("state") or "").strip().lower() in ("on", "true", "1")


def _charge_ok(state_row: dict[str, Any] | None, allowed: frozenset[str]) -> bool:
    if not state_row:
        return False
    stage = str(state_row.get("state") or "").strip().lower()
    return stage in allowed


def _sim_on_watts(states: dict[str, dict[str, Any]], watts_map: dict[str, int]) -> int:
    total = 0
    for entity_id, rated_w in watts_map.items():
        if _entity_is_on(states.get(entity_id)):
            total += rated_w
    return total


def _effective_load_watts(
    load_w: float | None,
    states: dict[str, dict[str, Any]],
    watts_map: dict[str, int],
    *,
    load_entity: str = _SIM_DUMP_LOAD_ENTITY,
) -> float | None:
    sim_w = _sim_on_watts(states, watts_map)
    if load_entity in (_SIM_DUMP_LOAD_ENTITY, _LEGACY_SIM_DUMP_LOAD_ENTITY):
        if load_w is not None:
            return load_w
        if watts_map:
            return float(sim_w)
        return None
    if load_w is not None:
        return load_w + sim_w
    if watts_map:
        return float(sim_w)
    return None


def _setting_on(raw: str | None) -> bool:
    return (raw or "").strip().lower() in ("1", "true", "yes", "on")


def _state_row(states: dict[str, dict[str, Any]], entity_id: str) -> dict[str, Any] | None:
    row = states.get(entity_id)
    if row:
        return row
    for alias in ENTITY_ALIASES.get(entity_id, ()):
        aliased = states.get(alias)
        if aliased:
            return aliased
    return None


def decide_dump(
    *,
    states: dict[str, dict[str, Any]],
    settings: dict[str, str],
    now: float,
    last_toggle: dict[str, tuple[str, float]] | None = None,
) -> tuple[list[DumpDecision], dict[str, Any]]:
    """Pure dump-load decision (mirrors alfa-ai src/ops/solar_dump.decide_dump)."""
    toggles = last_toggle if last_toggle is not None else {}
    enabled = _setting_on(
        settings.get("ha_solar_dump_enabled")
        or settings.get("ha_solar_soak_enabled")
        or "false"
    )
    allowlist = _parse_entity_list(settings.get("ha_switch_allowlist", ""))
    never_auto = _parse_entity_list(settings.get("ha_never_auto", ""))
    charge_ok_states = frozenset(
        tok.strip().lower()
        for tok in (settings.get("ha_charge_states_ok") or "").split(",")
        if tok.strip()
    )
    min_soc = int(settings.get("ha_min_soc_percent", "85"))
    min_surplus = int(settings.get("ha_min_surplus_watts", "200"))
    off_surplus = int(settings.get("ha_off_surplus_watts", "50"))
    max_on = int(settings.get("ha_max_concurrent_on", "2"))
    min_on_sec = int(settings.get("ha_min_on_seconds", "600"))
    min_off_sec = int(settings.get("ha_min_off_seconds", "300"))

    solar_e = settings.get("ha_solar_entity", DEFAULT_SETTINGS["ha_solar_entity"])
    load_e = settings.get("ha_load_entity", DEFAULT_SETTINGS["ha_load_entity"])
    soc_e = settings.get("ha_soc_entity", DEFAULT_SETTINGS["ha_soc_entity"])
    volt_e = settings.get(
        "ha_shunt_voltage_entity", DEFAULT_SETTINGS["ha_shunt_voltage_entity"]
    )
    curr_e = settings.get(
        "ha_shunt_current_entity", DEFAULT_SETTINGS["ha_shunt_current_entity"]
    )
    charge_e = settings.get("ha_charge_state_entity", DEFAULT_SETTINGS["ha_charge_state_entity"])
    soc_unsynced = _setting_on(settings.get("ha_soc_unsynced", "true"))

    solar_w = _parse_float_state(_state_row(states, solar_e))
    load_w = _parse_float_state(_state_row(states, load_e))
    soc = _parse_float_state(_state_row(states, soc_e))
    shunt_v = _parse_float_state(_state_row(states, volt_e))
    shunt_a = _parse_float_state(_state_row(states, curr_e))
    t2_shunt_v = shunt_v
    t2_shunt_a = shunt_a
    ku_shunt_v = _parse_float_state(_state_row(states, "sensor.battery_2_voltage"))
    ku_shunt_a = _parse_float_state(_state_row(states, "sensor.battery_2_current"))
    charge_row = _state_row(states, charge_e)
    watts_map = _parse_switch_watts(settings.get("ha_switch_watts", ""))
    sim_plug_w = _sim_on_watts(states, watts_map)
    effective_load_w = _effective_load_watts(
        load_w, states, watts_map, load_entity=load_e
    )

    meta: dict[str, Any] = {
        "enabled": enabled,
        "solar_w": solar_w,
        "load_w": load_w,
        "sim_plug_w": sim_plug_w,
        "effective_load_w": effective_load_w,
        "soc": soc,
        "shunt_v": shunt_v,
        "shunt_a": shunt_a,
        "t2_shunt_v": t2_shunt_v,
        "t2_shunt_a": t2_shunt_a,
        "ku_shunt_v": ku_shunt_v,
        "ku_shunt_a": ku_shunt_a,
        "soc_unsynced": soc_unsynced,
        "charge_state": str(charge_row.get("state") if charge_row else ""),
        "allowlist_count": len(allowlist),
    }

    surplus: float | None = None
    if solar_w is not None and effective_load_w is not None:
        surplus = solar_w - effective_load_w
        meta["surplus_w"] = surplus
    decision_surplus = apply_ledger_to_meta(meta, states, surplus)

    if not enabled:
        return [], {**meta, "skipped": "ha_solar_dump_enabled=false"}

    if not allowlist:
        return [], {**meta, "skipped": "empty ha_switch_allowlist"}

    if solar_w is None:
        return [], {**meta, "skipped": "solar sensor unavailable"}

    if effective_load_w is None:
        return [], {**meta, "skipped": "load sensor unavailable and no ha_switch_watts map"}

    if decision_surplus is None:
        return [], {**meta, "skipped": "solar sensor unavailable"}

    if soc_unsynced:
        meta["soc_gate"] = "skipped_unsynced"
    elif soc is None or soc < min_soc:
        return [], {**meta, "skipped": f"soc below {min_soc}"}

    if not _charge_ok(charge_row, charge_ok_states):
        return [], {
            **meta,
            "skipped": f"charge state not in {','.join(sorted(charge_ok_states))}",
        }

    eligible = [e for e in sorted(allowlist) if e not in never_auto]
    concurrent_on = sum(1 for e in eligible if _entity_is_on(states.get(e)))

    decisions: list[DumpDecision] = []
    for entity_id in eligible:
        current_on = _entity_is_on(states.get(entity_id))
        target: Literal["on", "off", "skip"] = "skip"
        reason = "hysteresis hold"

        losses = float(meta.get("combined_losses_w") or 0.0)
        if decision_surplus > min_surplus:
            target = "on"
            reason = (
                f"surplus {surplus:.0f}W minus {losses:.0f}W path losses "
                f"= {decision_surplus:.0f}W > {min_surplus}W"
            )
        elif decision_surplus <= off_surplus:
            target = "off"
            reason = (
                f"surplus {surplus:.0f}W minus {losses:.0f}W path losses "
                f"= {decision_surplus:.0f}W <= {off_surplus}W"
            )

        if target == "on" and current_on:
            decisions.append((entity_id, "skip", "already on"))
            continue
        if target == "off" and not current_on:
            decisions.append((entity_id, "skip", "already off"))
            continue
        if target == "skip":
            decisions.append((entity_id, "skip", reason))
            continue

        last = toggles.get(entity_id)
        if last:
            last_action, last_ts = last
            elapsed = now - last_ts
            if target == "off" and last_action == "on" and elapsed < min_on_sec:
                decisions.append(
                    (entity_id, "skip", f"min_on {min_on_sec}s not met ({elapsed:.0f}s)")
                )
                continue
            if target == "on" and last_action == "off" and elapsed < min_off_sec:
                decisions.append(
                    (entity_id, "skip", f"min_off {min_off_sec}s not met ({elapsed:.0f}s)")
                )
                continue

        if target == "on" and not current_on and concurrent_on >= max_on:
            decisions.append(
                (entity_id, "skip", f"max_concurrent_on {max_on} reached")
            )
            continue

        decisions.append((entity_id, target, reason))
        if target == "on" and not current_on:
            concurrent_on += 1

    return decisions, meta


def _shunt_current_flow(amps: float) -> str:
    if amps > 0:
        return "charging"
    if amps < 0:
        return "discharging"
    return "idle"


def _shunt_thinking_bits(meta: dict[str, Any]) -> list[str]:
    bits: list[str] = []
    t2v = meta.get("t2_shunt_v")
    t2a = meta.get("t2_shunt_a")
    kuv = meta.get("ku_shunt_v")
    kua = meta.get("ku_shunt_a")
    if t2v is not None:
        bits.append(
            f"T2 HQ2239CQYT2 shunt {t2v:.1f}V "
            "(LiTime absorb 28.4-29.2 V nameplate, not a Victron SoC)."
        )
    if t2a is not None:
        bits.append(
            f"T2 HQ2239CQYT2 shunt {t2a:+.1f}A "
            f"({_shunt_current_flow(t2a)}; +charge/-discharge)."
        )
    if kuv is not None:
        bits.append(f"KU HQ2239JTRKU shunt {kuv:.1f}V.")
    if kua is not None:
        bits.append(
            f"KU HQ2239JTRKU shunt {kua:+.1f}A "
            f"({_shunt_current_flow(kua)}; +charge/-discharge)."
        )
    return bits


def _build_thinking(meta: dict[str, Any]) -> str:
    skipped = meta.get("skipped")
    charge = meta.get("charge_state") or "unknown"
    shunt_bits = _shunt_thinking_bits(meta)

    if skipped:
        solar_w = meta.get("solar_w")
        soc = meta.get("soc")
        surplus = meta.get("surplus_w")
        bits = [f"Dump load skipped: {skipped}."]
        if surplus is not None:
            bits.append(f"Surplus would be {surplus:.0f}W.")
            losses = meta.get("combined_losses_w")
            after = meta.get("surplus_after_path_losses_w")
            if losses is not None:
                bits.append(
                    f"Path losses {losses:.0f}W (metered conversion hops; KU Victron/PWM D/C unmetered)."
                )
            if after is not None:
                bits.append(f"Surplus after losses {after:.0f}W.")
        elif solar_w is not None and meta.get("effective_load_w") is not None:
            eff = meta["effective_load_w"]
            bits.append(f"Solar {solar_w:.0f}W minus effective load {eff:.0f}W.")
        if meta.get("soc_unsynced"):
            bits.append("SoC gate skipped: unsynced; using V/A + charge state only.")
        elif soc is not None:
            bits.append(f"SoC {soc:.0f}%.")
        bits.append(f"Charge state {charge}.")
        bits.extend(shunt_bits)
        return " ".join(bits)

    surplus = meta.get("surplus_w")
    if surplus is None:
        return "Insufficient sensor data for dump load evaluation."
    bits = [f"Surplus {surplus:.0f}W with charge state {charge}."]
    losses = meta.get("combined_losses_w")
    after = meta.get("surplus_after_path_losses_w")
    if losses is not None:
        bits.append(
            f"Conversion losses {losses:.0f}W (metered hops; KU Victron/PWM D/C unmetered)."
        )
    vdrop_w = meta.get("combined_vdrop_loss_w")
    if vdrop_w is not None:
        bits.append(f"Voltage-drop loss {vdrop_w:.0f}W (D/C and A/C ΔV kept separate).")
    path_total = meta.get("combined_path_losses_w")
    if path_total is not None:
        bits.append(f"Combined path losses {path_total:.0f}W.")
    vent = meta.get("vent_fan_w")
    if vent is not None:
        bits.append(f"Trailer vent fan residual {vent:.0f}W (A3 is not Sungold-only).")
    ku_ac = meta.get("ku_renogy_ac_est_w")
    if ku_ac is not None:
        bits.append(
            f"Battery 2 load {ku_ac:.0f}W same as KU Renogy A/C est (A3; DC >= AC)."
        )
    ku_pv = meta.get("ku_unmetered_pv_est_w")
    share = meta.get("ku_charger_equal_share_w")
    if ku_pv is not None:
        bits.append(
            f"KU PV combined lower bound {ku_pv:.0f}W "
            f"(batt2 minus jumper plus load; not (batt2+load)/3)."
        )
        if share is not None:
            bits.append(
                f"Equal 1/3 est {share:.0f}W each on two MPPT plus PWM "
                "(PWM likely less than MPPT; no site derate; not dump solar)."
            )
    if after is not None:
        bits.append(f"Surplus after losses {after:.0f}W (dump ON/OFF uses this).")
    if meta.get("soc_unsynced"):
        bits.append("SoC gate skipped: unsynced; using V/A + charge state only.")
        soc = meta.get("soc")
        if soc is not None:
            bits.append(f"SoC tile {soc:.0f}% not used for control.")
    elif meta.get("soc") is not None:
        bits.append(f"SoC {meta['soc']:.0f}%.")
    bits.extend(shunt_bits)
    bits.append(
        "Decisions follow dump load thresholds (min surplus 200W, off at 50W)."
    )
    return " ".join(bits)


def decide_dump_view(
    *,
    states: dict[str, dict[str, Any]],
    settings: dict[str, str] | None = None,
    now: float | None = None,
    last_toggle: dict[str, tuple[str, float]] | None = None,
) -> dict[str, Any]:
    """Dashboard AI block: thinking paragraph + decision list (no persisted hysteresis)."""
    settings_map = dict(DEFAULT_SETTINGS)
    if settings:
        settings_map.update({k: str(v) for k, v in settings.items()})
    tick = time.time() if now is None else now
    decisions, meta = decide_dump(
        states=states,
        settings=settings_map,
        now=tick,
        last_toggle=last_toggle if last_toggle is not None else {},
    )
    rows: list[dict[str, Any]] = []
    for entity_id, action, reason in decisions:
        current = "on" if _entity_is_on(states.get(entity_id)) else "off"
        rows.append(
            {
                "entity_id": entity_id,
                "current": current,
                "target": action,
                "action": action,
                "reason": reason,
            }
        )
    return {
        "thinking": _build_thinking(meta),
        "decisions": rows,
        "surplus_w": meta.get("surplus_w"),
        "combined_losses_w": meta.get("combined_losses_w"),
        "combined_losses_incomplete": meta.get("combined_losses_incomplete"),
        "combined_vdrop_v": meta.get("combined_vdrop_v"),
        "combined_vdrop_ac_v": meta.get("combined_vdrop_ac_v"),
        "combined_vdrop_loss_w": meta.get("combined_vdrop_loss_w"),
        "combined_path_losses_w": meta.get("combined_path_losses_w"),
        "surplus_after_path_losses_w": meta.get("surplus_after_path_losses_w"),
        "panel_in_w": meta.get("panel_in_w"),
        "watt_hops": meta.get("watt_hops") or [],
        "vent_fan_w": meta.get("vent_fan_w"),
        "trailer_outlet_w": meta.get("trailer_outlet_w"),
        "sungold_ac_in_w": meta.get("sungold_ac_in_w"),
        "ku_renogy_ac_est_w": meta.get("ku_renogy_ac_est_w"),
        "ku_unmetered_pv_est_w": meta.get("ku_unmetered_pv_est_w"),
        "ku_charger_equal_share_w": meta.get("ku_charger_equal_share_w"),
        "ku_charger_equal_share_a": meta.get("ku_charger_equal_share_a"),
        "solar_w": meta.get("solar_w"),
        "load_w": meta.get("load_w"),
        "sim_plug_w": meta.get("sim_plug_w"),
        "effective_load_w": meta.get("effective_load_w"),
        "soc": meta.get("soc"),
        "shunt_v": meta.get("shunt_v"),
        "shunt_a": meta.get("shunt_a"),
        "t2_shunt_v": meta.get("t2_shunt_v"),
        "t2_shunt_a": meta.get("t2_shunt_a"),
        "ku_shunt_v": meta.get("ku_shunt_v"),
        "ku_shunt_a": meta.get("ku_shunt_a"),
        "soc_unsynced": meta.get("soc_unsynced"),
        "soc_gate": meta.get("soc_gate"),
        "charge_state": meta.get("charge_state"),
        "skipped": meta.get("skipped"),
        "meta": meta,
        "last_toggle": {},
    }


def default_ha_token_paths() -> list[Path]:
    """Gitignored long-lived token locations (never log file contents)."""
    return [
        ROOT.parent / "alfa-ai" / "deploy" / "secrets" / "home-assistant" / "long-lived.token",
        ROOT / "deploy" / "secrets" / "home-assistant" / "long-lived.token",
    ]


def _read_token_file(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def resolve_ha_token() -> str | None:
    direct = (os.environ.get("HA_TOKEN") or "").strip()
    if direct:
        return direct
    for env_name in ("HA_TOKEN_FILE", "HA_LONG_LIVED_TOKEN_FILE"):
        path_raw = (os.environ.get(env_name) or "").strip()
        if not path_raw:
            continue
        text = _read_token_file(Path(path_raw))
        if text:
            return text
        logger.debug("Could not read %s", env_name)
    for candidate in default_ha_token_paths():
        text = _read_token_file(candidate)
        if text:
            logger.info("Using HA token file %s", candidate)
            return text
    return None


def ha_base_url() -> str:
    return (os.environ.get("HA_BASE_URL") or "http://192.168.0.105:8123").rstrip("/")


def redact_secrets(text: str, token: str | None = None) -> str:
    out = text or ""
    if token:
        out = out.replace(token, "[REDACTED]")
    out = re.sub(r"Bearer\s+\S+", "Bearer [REDACTED]", out, flags=re.IGNORECASE)
    out = re.sub(r"Authorization:\s*\S+", "Authorization: [REDACTED]", out, flags=re.IGNORECASE)
    return out


def wanted_entity_ids(
    entity_ids: frozenset[str] | set[str] | None = None,
) -> frozenset[str]:
    wanted = set(entity_ids if entity_ids is not None else REQUIRED_ENTITY_IDS)
    for canonical, aliases in ENTITY_ALIASES.items():
        if canonical in wanted:
            wanted.update(aliases)
    return frozenset(wanted)


def _skip_snapshot_entity(entity_id: str) -> bool:
    if entity_id.startswith("input_boolean.sim_ac_plug_") and entity_id.endswith(
        "_internal"
    ):
        return True
    return False


def _prefix_match(entity_id: str) -> bool:
    return any(entity_id.startswith(prefix) for prefix in SNAPSHOT_PREFIXES)


def apply_entity_aliases(entities: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Keep dump-load canonical ids and Lovelace live ids in sync.

    Live registry ids win when both exist so GX tiles match Lovelace
    (HA REST GET /api/states). If only the canonical exists, copy it onto
    the live id so the browser can read Lovelace names.
    """
    out = dict(entities)
    for canonical, aliases in ENTITY_ALIASES.items():
        live_id = None
        live_row = None
        for alias in aliases:
            src = out.get(alias)
            if src:
                live_id = alias
                live_row = src
                break
        if live_row is not None:
            copied = dict(live_row)
            copied["source_entity_id"] = live_id
            out[canonical] = copied
            continue
        canonical_row = out.get(canonical)
        if not canonical_row:
            continue
        for alias in aliases:
            if alias in out:
                continue
            copied = dict(canonical_row)
            copied["source_entity_id"] = canonical
            out[alias] = copied
    return out


def _entity_entry(row: dict[str, Any]) -> dict[str, Any]:
    attrs = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
    entry: dict[str, Any] = {
        "state": row.get("state"),
        "attributes": attrs,
    }
    # HA REST state object timestamps:
    # https://developers.home-assistant.io/docs/api/rest/
    # https://www.home-assistant.io/docs/configuration/state_object/
    for ts_key in ("last_updated", "last_changed", "last_reported"):
        if ts_key in row:
            entry[ts_key] = row[ts_key]
    return entry


def filter_entities(
    all_states: list[dict[str, Any]],
    entity_ids: frozenset[str] | set[str] | None = None,
) -> dict[str, dict[str, Any]]:
    wanted = wanted_entity_ids(entity_ids)
    out: dict[str, dict[str, Any]] = {}
    for row in all_states:
        eid = str(row.get("entity_id") or "")
        if not eid or _skip_snapshot_entity(eid):
            continue
        if eid not in wanted and not _prefix_match(eid):
            continue
        out[eid] = _entity_entry(row)
    return apply_entity_aliases(out)


def entities_to_dump_states(entities: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        eid: {"entity_id": eid, "state": row.get("state"), "attributes": row.get("attributes") or {}}
        for eid, row in entities.items()
    }


def fetch_ha_states(base_url: str, token: str, timeout: float = 10.0) -> list[dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/states"
    req = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode("utf-8")
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("HA /api/states did not return a JSON array")
    return data


def history_allowlist() -> frozenset[str]:
    """Plant entity ids permitted for GET /api/history (exact ids only)."""
    allowed = set(REQUIRED_ENTITY_IDS)
    for canonical, aliases in ENTITY_ALIASES.items():
        allowed.add(canonical)
        allowed.update(aliases)
    return frozenset(allowed)


def is_history_entity_allowed(entity_id: str) -> bool:
    if entity_id in history_allowlist():
        return True
    return _prefix_match(entity_id)


def clamp_history_hours(hours: int) -> int:
    """Proxy-only hours param; not forwarded to HA."""
    if hours < 1:
        return 1
    if hours > HISTORY_HOURS_MAX:
        return HISTORY_HOURS_MAX
    return hours


def build_ha_history_url(base_url: str, entity_id: str, hours: int) -> str:
    """Build HA recorder URL with quoted ISO start/end.

    Official: https://developers.home-assistant.io/docs/api/rest/
    GET /api/history/period/{start}?filter_entity_id=...&end_time={end}&minimal_response
    Bare flag minimal_response only; optional no_attributes.

    significant_changes_only is listed on the REST page as an optional query flag with
    no documented disable value or default. Proxy omits it.
    """
    window = clamp_history_hours(hours)
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=window)
    start_iso = quote(start.isoformat(timespec="seconds"), safe="")
    end_iso = quote(end.isoformat(timespec="seconds"), safe="")
    return (
        f"{base_url.rstrip('/')}/api/history/period/{start_iso}"
        f"?filter_entity_id={entity_id}&end_time={end_iso}&minimal_response&no_attributes"
    )


def parse_ha_history_response(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError("HA /api/history/period did not return a JSON array")
    if not data:
        return []
    first = data[0]
    if not isinstance(first, list):
        raise ValueError("HA history response shape unexpected")
    rows: list[dict[str, Any]] = []
    for row in first:
        if isinstance(row, dict):
            rows.append(row)
    return rows


def fetch_ha_history(
    base_url: str,
    token: str,
    entity_id: str,
    hours: int = 24,
    timeout: float = 15.0,
) -> list[dict[str, Any]]:
    url = build_ha_history_url(base_url, entity_id, hours)
    req = Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urlopen(req, timeout=timeout) as resp:
        payload = resp.read().decode("utf-8")
    return parse_ha_history_response(json.loads(payload))


def load_demo_entities() -> dict[str, dict[str, Any]]:
    raw = json.loads(DEMO_SNAPSHOT.read_text(encoding="utf-8"))
    entities = raw.get("entities")
    if not isinstance(entities, dict):
        raise ValueError("demo-snapshot.json missing entities object")
    return apply_entity_aliases(entities)


def is_sim_dump_entity(entity_id: str) -> bool:
    return any(entity_id.startswith(prefix) for prefix in _SIM_DUMP_ENTITY_PREFIXES)


def load_demo_sim_entities() -> dict[str, dict[str, Any]]:
    return {
        eid: dict(row)
        for eid, row in load_demo_entities().items()
        if is_sim_dump_entity(eid)
    }


def sim_dump_required_entity_ids() -> frozenset[str]:
    """Sim dump ids the live snapshot expects from HA or demo-file fallback."""
    return frozenset(eid for eid in REQUIRED_ENTITY_IDS if is_sim_dump_entity(eid))


def fill_missing_sim_dump_entities(
    entities: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], bool]:
    """Keep HA sim dump rows; overlay demo file only for missing sim dump ids.

    Returns (merged entities, sim_dump_demo) where sim_dump_demo is True when any
    required sim dump id was filled from demo-snapshot.json.
    """
    merged = dict(entities)
    demo_sim = load_demo_sim_entities()
    filled_from_demo = False
    for eid in sim_dump_required_entity_ids():
        if eid in merged:
            continue
        demo_row = demo_sim.get(eid)
        if demo_row is not None:
            merged[eid] = dict(demo_row)
            filled_from_demo = True
    return apply_entity_aliases(merged), filled_from_demo


def overlay_sim_dump_demo(entities: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Backward-compatible: fill all missing sim dump ids from demo file."""
    merged, _ = fill_missing_sim_dump_entities(entities)
    return merged


def _snapshot_ai(entities: dict[str, dict[str, Any]], now: float | None) -> dict[str, Any]:
    return decide_dump_view(states=entities_to_dump_states(entities), now=now)


_PRODUCTION_TOKEN_LABEL = (
    "Production requires a gitignored HA token on the proxy (HA_TOKEN_FILE)."
)


def public_missing_entity_ids(entity_ids: list[str]) -> list[str]:
    """Omit leftover HA unique_ids so the dashboard never prints soak."""
    return [eid for eid in entity_ids if "soak" not in eid.lower()]


def build_offline_snapshot(
    now: float | None = None,
    *,
    view: str = "production",
    label: str | None = None,
) -> dict[str, Any]:
    """No HA token: sim dump loads from demo file; plant tiles stay missing (no fake MPPT W)."""
    entities, sim_dump_demo = fill_missing_sim_dump_entities({})
    fetched_at = datetime.now(timezone.utc).isoformat()
    missing = sorted(eid for eid in REQUIRED_ENTITY_IDS if eid not in entities)
    resolved_label = label
    if resolved_label is None and view == "production":
        resolved_label = _PRODUCTION_TOKEN_LABEL
    payload: dict[str, Any] = {
        "mode": "demo",
        "view": view,
        "sim_dump_demo": sim_dump_demo,
        "fetched_at": fetched_at,
        "entities": entities,
        "missing_entity_ids": public_missing_entity_ids(missing),
        "ai": _snapshot_ai(entities, now),
    }
    if resolved_label:
        payload["label"] = resolved_label
    return payload


def build_demo_snapshot(now: float | None = None) -> dict[str, Any]:
    """Backward-compatible alias for offline snapshot (sim-only plant)."""
    return build_offline_snapshot(now=now)


def build_illustrative_demo_snapshot(now: float | None = None) -> dict[str, Any]:
    """Full illustrative demo-snapshot.json (operator Demo toggle)."""
    raw = json.loads(DEMO_SNAPSHOT.read_text(encoding="utf-8"))
    entities = load_demo_entities()
    fetched_at = datetime.now(timezone.utc).isoformat()
    label = raw.get("label") if isinstance(raw.get("label"), str) else None
    if not label:
        label = "DEMO illustrative numbers - not a live Home Assistant observation"
    return {
        "mode": "demo",
        "view": "demo",
        "sim_dump_demo": False,
        "label": label,
        "fetched_at": fetched_at,
        "entities": entities,
        "missing_entity_ids": [],
        "ai": _snapshot_ai(entities, now),
    }


def build_live_snapshot(token: str, now: float | None = None) -> dict[str, Any]:
    base = ha_base_url()
    rows = fetch_ha_states(base, token)
    entities, sim_dump_demo = fill_missing_sim_dump_entities(filter_entities(rows))
    fetched_at = datetime.now(timezone.utc).isoformat()
    missing = sorted(eid for eid in REQUIRED_ENTITY_IDS if eid not in entities)
    return {
        "mode": "live",
        "view": "production",
        "sim_dump_demo": sim_dump_demo,
        "fetched_at": fetched_at,
        "entities": entities,
        "missing_entity_ids": public_missing_entity_ids(missing),
        "ai": _snapshot_ai(entities, now),
    }


def parse_snapshot_view(query: str) -> str | None:
    """Return production, demo, or None (default). Raises ValueError for unknown view."""
    params = parse_qs(query)
    raw = (params.get("view") or [None])[0]
    if raw is None or not str(raw).strip():
        return None
    view = str(raw).strip().lower()
    if view in ("production", "demo"):
        return view
    raise ValueError(f"unknown view: {raw}")


def build_snapshot(
    token: str | None = None,
    now: float | None = None,
    *,
    view: str | None = None,
) -> dict[str, Any]:
    resolved = token if token is not None else resolve_ha_token()
    if view == "demo":
        return build_illustrative_demo_snapshot(now=now)
    if resolved:
        return build_live_snapshot(resolved, now=now)
    return build_offline_snapshot(now=now, view=view or "production")


class SolarFlowHandler(BaseHTTPRequestHandler):
    server_version = "SolarFlowServer/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        msg = redact_secrets(format % args)
        logger.info("%s - %s", self.address_string(), msg)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(
        self,
        body: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/snapshot":
            self._handle_snapshot(parsed.query)
            return
        if path == "/api/history":
            self._handle_history(parsed.query)
            return
        self._handle_static(path)

    def _handle_history(self, query: str) -> None:
        params = parse_qs(query)
        entity_id = (params.get("entity_id") or [""])[0].strip()
        hours_raw = (params.get("hours") or ["24"])[0].strip()
        try:
            hours = clamp_history_hours(int(hours_raw))
        except ValueError:
            hours = clamp_history_hours(24)

        if not entity_id:
            self._send_json({"error": "entity_id required"}, HTTPStatus.BAD_REQUEST)
            return
        if not is_history_entity_allowed(entity_id):
            self._send_json({"error": "entity_id not allowed"}, HTTPStatus.BAD_REQUEST)
            return

        token = resolve_ha_token()
        if not token:
            self._send_json(
                {"error": "history unavailable without HA token"},
                HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return

        try:
            rows = fetch_ha_history(ha_base_url(), token, entity_id, hours=hours)
            self._send_json(
                {
                    "entity_id": entity_id,
                    "hours": hours,
                    "points": rows,
                }
            )
        except HTTPError as exc:
            safe = redact_secrets(str(exc), token)
            if exc.code == HTTPStatus.NOT_FOUND:
                logger.warning(
                    "history endpoint 404 for %s (recorder/history not loaded): %s",
                    entity_id,
                    safe,
                )
                self._send_json(
                    {"error": HISTORY_RECORDER_DISABLED_MSG},
                    HTTPStatus.SERVICE_UNAVAILABLE,
                )
                return
            logger.warning("history HTTP failed for %s: %s", entity_id, safe)
            self._send_json({"error": "history fetch failed"}, HTTPStatus.BAD_GATEWAY)
        except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            safe = redact_secrets(str(exc), token)
            logger.warning("history fetch failed for %s: %s", entity_id, safe)
            self._send_json({"error": "history fetch failed"}, HTTPStatus.BAD_GATEWAY)

    def _handle_snapshot(self, query: str = "") -> None:
        token = resolve_ha_token()
        try:
            view = parse_snapshot_view(query)
        except ValueError as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        try:
            payload = build_snapshot(token=token, view=view)
            self._send_json(payload)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            safe = redact_secrets(str(exc), token)
            logger.warning("snapshot fetch failed: %s", safe)
            self._send_json({"mode": "live", "error": safe}, HTTPStatus.BAD_GATEWAY)

    def _handle_static(self, url_path: str) -> None:
        if url_path in ("", "/"):
            rel = "index.html"
        else:
            rel = url_path.lstrip("/")
        target = (WEB_ROOT / rel).resolve()
        try:
            target.relative_to(WEB_ROOT.resolve())
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        body = target.read_bytes()
        mime, _ = mimetypes.guess_type(str(target))
        self._send_bytes(body, mime or "application/octet-stream")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solar-flow dashboard HTTP server")
    parser.add_argument(
        "--host",
        default=os.environ.get("SOLAR_FLOW_HOST"),
        help="Bind address (default: SOLAR_FLOW_HOST or 127.0.0.1; 0.0.0.0 with --lan)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("SOLAR_FLOW_PORT", "8765")),
        help="Bind port (default: SOLAR_FLOW_PORT or 8765)",
    )
    parser.add_argument(
        "--lan",
        action="store_true",
        help="Bind 0.0.0.0 for LAN operator use (default is localhost only)",
    )
    return parser.parse_args(argv)


def resolve_bind_host(args: argparse.Namespace) -> str:
    if args.host:
        return args.host
    if args.lan:
        return "0.0.0.0"
    return "127.0.0.1"


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = parse_args(argv)
    host = resolve_bind_host(args)
    if not WEB_ROOT.is_dir():
        logger.error("Missing web root: %s", WEB_ROOT)
        return 1
    if not DEMO_SNAPSHOT.is_file():
        logger.error("Missing demo snapshot: %s", DEMO_SNAPSHOT)
        return 1

    httpd = ThreadingHTTPServer((host, args.port), SolarFlowHandler)
    display_host = host if host != "0.0.0.0" else "127.0.0.1"
    url = f"http://{display_host}:{args.port}/"
    print(f"Solar flow dashboard: {url}")
    logger.info("Serving %s on %s:%s (mode=%s)", WEB_ROOT, host, args.port, "live" if resolve_ha_token() else "demo")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
