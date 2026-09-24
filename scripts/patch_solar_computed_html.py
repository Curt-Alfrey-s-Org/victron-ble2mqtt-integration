#!/usr/bin/env python3
"""Expand computed-html in flows/solar_computed_meters.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "flows" / "solar_computed_meters.json"

HTML_FUNC = r"""const d = flow.get('solarComputedLast') || {};
function cell(label, val, unit) {
    const v = val == null ? 'Unavailable' : String(val) + (unit || '');
    return '<tr><td>' + label + '</td><td><strong>' + v + '</strong></td></tr>';
}
const rows = [
    cell('Site solar W', d.site_solar_w, ' W'),
    cell('Site source W', d.site_source_w, ' W'),
    cell('Site total load W', d.site_total_load_w, ' W'),
    cell('Load unaccounted W', d.load_unaccounted_w, ' W'),
    cell('T2 MPPT W', d.t2_mppt_w, ' W'),
    cell('T2-KU jumper W', d.t2_ku_jumper_w, ' W'),
    cell('KU Victron MPPT 2+3 est W', d.ku_victron_mppt23_est_w, ' W'),
    cell('KU PWM+MPPT combined est W', d.ku_pwm_mppt_combined_est_w, ' W'),
    cell('KU PWM est W', d.ku_pwm_est_w, ' W'),
    cell('KU equal share (1/3) W', d.ku_charger_equal_share_w, ' W'),
    cell('Trailer / KU AC proxy W', d.trailer_outlet_w, ' W'),
    cell('EM16 A3 live W', d.em16_a3_live_w, ' W'),
    cell('EM16 B3 live W', d.em16_b3_live_w, ' W'),
    cell('Sungold PV W', d.sungold_pv_w, ' W'),
    cell('Sungold AC in W', d.sungold_ac_in_w, ' W'),
    cell('Sungold AC out W', d.sungold_ac_out_w, ' W'),
];
const panels = d.panels || [];
let panelRows = '';
for (let i = 0; i < 8; i++) {
    const p = panels[i] || {};
    const w = p.est_w == null ? 'Unavailable' : String(p.est_w) + ' W';
    const conn = p.connects || '';
    const short = conn.indexOf('->') >= 0 ? conn.split('->').pop().trim() : conn;
    panelRows += '<tr><td>' + (p.label || ('P' + (i+1))) + '</td><td>' + (p.string || '') + '</td><td><strong>' + w + '</strong></td><td style="font-size:0.85rem;color:#aaa">' + short + '</td></tr>';
}
msg.payload = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Solar computed</title>' +
'<meta http-equiv="refresh" content="5">' +
'<style>body{font-family:sans-serif;background:#111;color:#eee;padding:1rem}' +
'table{border-collapse:collapse;width:100%;max-width:48rem;margin-bottom:1.5rem}td,th{padding:0.5rem;border-bottom:1px solid #333;text-align:left}' +
'h1{font-size:1.1rem}h2{font-size:1rem;margin-top:1.5rem}p{color:#888;font-size:0.85rem}' +
'.panels td:nth-child(1){font-weight:bold;width:3rem}</style></head><body>' +
'<h1>Solar computed meters</h1><p>From HA device states only. Site solar in HA stays device tiles.</p>' +
'<table>' + rows.join('') + '</table>' +
'<h2>Solar panels (8 boxes)</h2><p>Est W per panel = half of its 2s string. Matches Node-RED diagram group.</p>' +
'<table class="panels"><tr><th>Panel</th><th>String</th><th>Est W</th><th>Connects to</th></tr>' + panelRows + '</table></body></html>';
msg.headers = { 'Content-Type': 'text/html; charset=utf-8' };
return msg;"""


def main() -> int:
    flow = json.loads(FLOW.read_text(encoding="utf-8"))
    for node in flow:
        if node.get("id") == "computed-html":
            node["func"] = HTML_FUNC
            break
    else:
        raise SystemExit("computed-html node not found")
    FLOW.write_text(json.dumps(flow, indent=2), encoding="utf-8")
    print("updated computed-html in", FLOW)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
