#!/usr/bin/env python3
"""Solar-flow LAN dashboard: static files + GET /api/snapshot from Home Assistant REST.

Official:
  HA REST: https://developers.home-assistant.io/docs/api/rest/
  http.server: https://docs.python.org/3/library/http.server.html
  urllib.request: https://docs.python.org/3/library/urllib.request.html

Token stays server-side (HA_TOKEN, HA_TOKEN_FILE, or HA_LONG_LIVED_TOKEN_FILE).
Default bind 127.0.0.1:8765; use --lan / --tailscale for 0.0.0.0 (operator LAN + Tailscale).
"""
from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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

DEFAULT_SETTINGS: dict[str, str] = {
    "ha_solar_soak_enabled": "true",
    "ha_switch_allowlist": _SIM_PLUG_ALLOWLIST,
    "ha_switch_watts": _SIM_PLUG_WATTS,
    "ha_never_auto": "",
    "ha_solar_entity": "sensor.solar_controller_solar_power",
    "ha_load_entity": "sensor.em16_a3_power",
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

# Lovelace / MQTT names that differ from soak canonical ids.
# Live Solar dashboard uses sensor.solar_controller_solar (tests/test_ha_label_victron_refoss.py).
# MQTT discovery names: Solar power, Battery state, State of charge
# (override/victron_ble2mqtt/mqtt.py SolarChargerHandler / BatteryMonitorHandler).
# Sungold live ids: scripts/ha_label_sungold_solar.py + .105 entity registry 16 Sep 2026.
# Fresh MQTT discovery for unique_id ...-pv1-* yields entity_id ..._pv1_*; older installs
# reuse ..._pv_voltage. Alias both so PC and mobile Tailscale see the same numbers.
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
    "sensor.sungold_sph302480a_pv_voltage": ("sensor.sungold_sph302480a_pv1_voltage",),
    "sensor.sungold_sph302480a_pv_current": ("sensor.sungold_sph302480a_pv1_current",),
    "sensor.sungold_sph302480a_pv_power": ("sensor.sungold_sph302480a_pv1_power",),
    "sensor.sungold_sph302480a_charging_power": (
        "sensor.sungold_sph302480a_inverter_charging_power",
    ),
    "sensor.sungold_sph302480a_charge_state": (
        "sensor.sungold_sph302480a_battery_charge_state",
    ),
    "sensor.sungold_sph302480a_ac_output_voltage": (
        "sensor.sungold_sph302480a_inverter_voltage",
    ),
    "sensor.sungold_sph302480a_ac_output_frequency": (
        "sensor.sungold_sph302480a_inverter_frequency",
    ),
    "sensor.sungold_sph302480a_fail_code": (
        "sensor.sungold_sph302480a_inverter_failcode",
    ),
    "binary_sensor.sungold_sph302480a_fault_active": (
        "binary_sensor.sungold_sph302480a_inverter_fault_active",
    ),
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
    "sensor.sim_soak_",
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
        "sensor.sim_soak_load_power",
    ]
)

SoakDecision = tuple[str, Literal["on", "off", "skip"], str]

logger = logging.getLogger("solar_flow_server")


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
) -> float | None:
    sim_w = _sim_on_watts(states, watts_map)
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


def decide_soak(
    *,
    states: dict[str, dict[str, Any]],
    settings: dict[str, str],
    now: float,
    last_toggle: dict[str, tuple[str, float]] | None = None,
) -> tuple[list[SoakDecision], dict[str, Any]]:
    """Pure soak decision (mirrors alfa-ai src/ops/solar_soak.decide_soak)."""
    toggles = last_toggle if last_toggle is not None else {}
    enabled = _setting_on(settings.get("ha_solar_soak_enabled", "false"))
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
    charge_row = _state_row(states, charge_e)
    watts_map = _parse_switch_watts(settings.get("ha_switch_watts", ""))
    sim_plug_w = _sim_on_watts(states, watts_map)
    effective_load_w = _effective_load_watts(load_w, states, watts_map)

    meta: dict[str, Any] = {
        "enabled": enabled,
        "solar_w": solar_w,
        "load_w": load_w,
        "sim_plug_w": sim_plug_w,
        "effective_load_w": effective_load_w,
        "soc": soc,
        "shunt_v": shunt_v,
        "shunt_a": shunt_a,
        "soc_unsynced": soc_unsynced,
        "charge_state": str(charge_row.get("state") if charge_row else ""),
        "allowlist_count": len(allowlist),
    }

    if not enabled:
        return [], {**meta, "skipped": "ha_solar_soak_enabled=false"}

    if not allowlist:
        return [], {**meta, "skipped": "empty ha_switch_allowlist"}

    if solar_w is None:
        return [], {**meta, "skipped": "solar sensor unavailable"}

    if effective_load_w is None:
        return [], {**meta, "skipped": "load sensor unavailable and no ha_switch_watts map"}

    surplus = solar_w - effective_load_w
    meta["surplus_w"] = surplus

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

    decisions: list[SoakDecision] = []
    for entity_id in eligible:
        current_on = _entity_is_on(states.get(entity_id))
        target: Literal["on", "off", "skip"] = "skip"
        reason = "hysteresis hold"

        if surplus > min_surplus:
            target = "on"
            reason = f"surplus {surplus:.0f}W > {min_surplus}W"
        elif surplus <= off_surplus:
            target = "off"
            reason = f"surplus {surplus:.0f}W <= {off_surplus}W"

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


def _build_thinking(meta: dict[str, Any]) -> str:
    skipped = meta.get("skipped")
    charge = meta.get("charge_state") or "unknown"
    shunt_bits: list[str] = []
    shunt_v = meta.get("shunt_v")
    shunt_a = meta.get("shunt_a")
    if shunt_v is not None:
        shunt_bits.append(
            f"Shunt {shunt_v:.1f}V (LiTime absorb 28.4-29.2 V nameplate, not a Victron SoC)."
        )
    if shunt_a is not None:
        if shunt_a > 0:
            flow = "charging"
        elif shunt_a < 0:
            flow = "discharging"
        else:
            flow = "idle"
        shunt_bits.append(f"Shunt {shunt_a:.1f}A ({flow}; +charge/-discharge).")

    if skipped:
        solar_w = meta.get("solar_w")
        soc = meta.get("soc")
        surplus = meta.get("surplus_w")
        bits = [f"Soak skipped: {skipped}."]
        if surplus is not None:
            bits.append(f"Surplus would be {surplus:.0f}W.")
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
        return "Insufficient sensor data for soak evaluation."
    bits = [f"Surplus {surplus:.0f}W with charge state {charge}."]
    if meta.get("soc_unsynced"):
        bits.append("SoC gate skipped: unsynced; using V/A + charge state only.")
        soc = meta.get("soc")
        if soc is not None:
            bits.append(f"SoC tile {soc:.0f}% not used for control.")
    elif meta.get("soc") is not None:
        bits.append(f"SoC {meta['soc']:.0f}%.")
    bits.extend(shunt_bits)
    bits.append(
        "Decisions follow soak thresholds (min surplus 200W, off at 50W)."
    )
    return " ".join(bits)


def decide_soak_view(
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
    decisions, meta = decide_soak(
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
        "solar_w": meta.get("solar_w"),
        "load_w": meta.get("load_w"),
        "sim_plug_w": meta.get("sim_plug_w"),
        "effective_load_w": meta.get("effective_load_w"),
        "soc": meta.get("soc"),
        "shunt_v": meta.get("shunt_v"),
        "shunt_a": meta.get("shunt_a"),
        "soc_unsynced": meta.get("soc_unsynced"),
        "soc_gate": meta.get("soc_gate"),
        "charge_state": meta.get("charge_state"),
        "skipped": meta.get("skipped"),
        "meta": meta,
        "last_toggle": {},
    }


def resolve_ha_token() -> str | None:
    direct = (os.environ.get("HA_TOKEN") or "").strip()
    if direct:
        return direct
    for env_name in ("HA_TOKEN_FILE", "HA_LONG_LIVED_TOKEN_FILE"):
        path_raw = (os.environ.get(env_name) or "").strip()
        if not path_raw:
            continue
        try:
            text = Path(path_raw).read_text(encoding="utf-8").strip()
        except OSError:
            logger.debug("Could not read %s", env_name)
            continue
        if text:
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
    """Copy Lovelace/MQTT alias rows onto soak canonical ids when the canonical is absent."""
    out = dict(entities)
    for canonical, aliases in ENTITY_ALIASES.items():
        if canonical in out:
            continue
        for alias in aliases:
            src = out.get(alias)
            if not src:
                continue
            copied = dict(src)
            copied["source_entity_id"] = alias
            out[canonical] = copied
            break
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


def entities_to_soak_states(entities: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
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


def load_demo_entities() -> dict[str, dict[str, Any]]:
    raw = json.loads(DEMO_SNAPSHOT.read_text(encoding="utf-8"))
    entities = raw.get("entities")
    if not isinstance(entities, dict):
        raise ValueError("demo-snapshot.json missing entities object")
    return entities


def build_demo_snapshot(now: float | None = None) -> dict[str, Any]:
    entities = load_demo_entities()
    soak_states = entities_to_soak_states(entities)
    fetched_at = datetime.now(timezone.utc).isoformat()
    return {
        "mode": "demo",
        "label": "DEMO illustrative numbers - not a live Home Assistant observation",
        "fetched_at": fetched_at,
        "entities": entities,
        "ai": decide_soak_view(states=soak_states, now=now),
    }


def build_live_snapshot(token: str, now: float | None = None) -> dict[str, Any]:
    base = ha_base_url()
    rows = fetch_ha_states(base, token)
    entities = filter_entities(rows)
    soak_states = entities_to_soak_states(entities)
    fetched_at = datetime.now(timezone.utc).isoformat()
    missing = sorted(eid for eid in REQUIRED_ENTITY_IDS if eid not in entities)
    return {
        "mode": "live",
        "fetched_at": fetched_at,
        "entities": entities,
        "missing_entity_ids": missing,
        "ai": decide_soak_view(states=soak_states, now=now),
    }


def build_snapshot(token: str | None = None, now: float | None = None) -> dict[str, Any]:
    resolved = token if token is not None else resolve_ha_token()
    if resolved:
        return build_live_snapshot(resolved, now=now)
    return build_demo_snapshot(now=now)


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
        path = self.path.split("?", 1)[0]
        if path == "/api/snapshot":
            self._handle_snapshot()
            return
        if path == "/api/access":
            self._handle_access()
            return
        self._handle_static(path)

    def _handle_snapshot(self) -> None:
        token = resolve_ha_token()
        try:
            if token:
                payload = build_live_snapshot(token)
            else:
                payload = build_demo_snapshot()
            self._send_json(payload)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            safe = redact_secrets(str(exc), token)
            logger.warning("snapshot fetch failed: %s", safe)
            self._send_json({"mode": "live", "error": safe}, HTTPStatus.BAD_GATEWAY)

    def _handle_access(self) -> None:
        host, port = self.server.server_address[:2]
        identity = discover_tailscale_identity()
        payload = {
            "bind_host": host,
            "port": port,
            "urls": access_urls(str(host), int(port)),
            "tailscale": identity,
            "serve_https": discover_serve_https_url(),
        }
        self._send_json(payload)

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
        help="Bind address (default: SOLAR_FLOW_HOST or 127.0.0.1; 0.0.0.0 with --lan/--tailscale)",
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
    parser.add_argument(
        "--tailscale",
        action="store_true",
        help="Bind 0.0.0.0 and print Tailscale MagicDNS / 100.x URLs (same as --lan plus discovery)",
    )
    return parser.parse_args(argv)


def resolve_bind_host(args: argparse.Namespace) -> str:
    if args.host:
        return args.host
    if args.lan or args.tailscale or _env_truthy("SOLAR_FLOW_TAILSCALE"):
        return "0.0.0.0"
    return "127.0.0.1"


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def _tailscale_bin() -> str | None:
    return shutil.which("tailscale")


def discover_tailscale_identity() -> dict[str, str]:
    """Return Tailscale IP / DNS name for this host when the CLI is available.

    Does not invent names. Empty dict when Tailscale is missing or offline.
    Official: https://tailscale.com/docs/reference/tailscale-cli
    """
    binary = _tailscale_bin()
    if not binary:
        return {}
    out: dict[str, str] = {}
    try:
        ip_proc = subprocess.run(
            [binary, "ip", "-4"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if ip_proc.returncode == 0:
        ip = (ip_proc.stdout or "").strip().split()[0] if ip_proc.stdout.strip() else ""
        if ip.startswith("100."):
            out["tailscale_ip"] = ip
    try:
        status_proc = subprocess.run(
            [binary, "status", "--json"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return out
    if status_proc.returncode != 0 or not (status_proc.stdout or "").strip():
        return out
    try:
        status = json.loads(status_proc.stdout)
    except json.JSONDecodeError:
        return out
    self_node = status.get("Self") or {}
    dns = (self_node.get("DNSName") or "").rstrip(".")
    if dns:
        out["magicdns"] = dns
    hostname = (self_node.get("HostName") or "").strip()
    if hostname:
        out["hostname"] = hostname
    return out


def discover_serve_https_url() -> str | None:
    """Parse `tailscale serve status` for an HTTPS MagicDNS URL when Serve is configured."""
    binary = _tailscale_bin()
    if not binary:
        return None
    try:
        proc = subprocess.run(
            [binary, "serve", "status"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    match = re.search(r"https://[a-zA-Z0-9._-]+\.ts\.net(?:/\S*)?", text)
    if match:
        return match.group(0).rstrip("/")
    return None


def access_urls(bind_host: str, port: int) -> list[str]:
    """Operator URLs for this process (localhost, Tailscale IP, MagicDNS, Serve)."""
    urls: list[str] = [f"http://127.0.0.1:{port}/"]
    if bind_host in ("0.0.0.0", "::", ""):
        identity = discover_tailscale_identity()
        ts_ip = identity.get("tailscale_ip")
        if ts_ip:
            urls.append(f"http://{ts_ip}:{port}/")
        magic = identity.get("magicdns")
        if magic:
            urls.append(f"http://{magic}:{port}/")
        serve = discover_serve_https_url()
        if serve:
            if not serve.endswith("/"):
                serve = serve + "/"
            if serve not in urls:
                urls.append(serve)
    # Dedupe while preserving order
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def print_access_urls(bind_host: str, port: int) -> None:
    urls = access_urls(bind_host, port)
    print("Solar flow dashboard access URLs:")
    for url in urls:
        print(f"  {url}")
    if bind_host in ("0.0.0.0", "::") and len(urls) <= 1:
        print(
            "  (Tailscale offline or not installed — run scripts/solar_flow_enable_tailscale.sh on .105)"
        )


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
    print_access_urls(host, args.port)
    logger.info(
        "Serving %s on %s:%s (mode=%s)",
        WEB_ROOT,
        host,
        args.port,
        "live" if resolve_ha_token() else "demo",
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down")
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
