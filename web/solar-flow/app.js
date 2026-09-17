(function () {
  'use strict';

  var POLL_MS = 2000;
  var VIEW_STORAGE_KEY = 'solar-flow-view';
  var currentView = 'production';
  // Browser may request hours=24; proxy clamps to 10 (see solar_flow_server.py).
  var HISTORY_HOURS = 24;
  var HISTORY_TABLE_ROWS = 40;
  var lastSnapshot = null;
  var proxyOnline = false;
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var selectedHistoryEntity = null;

  var ENTITY_IDS = {
    solar: 'sensor.solar_controller_solar',
    battState: 'sensor.solar_controller_charge_state',
    mpptV: 'sensor.solar_controller_battery',
    mpptA: 'sensor.solar_controller_battery_charging',
    mpptChargeW: 'sensor.solar_controller_charging_power',
    mpptLoadA: 'sensor.solar_controller_load',
    mpptLoadW: 'sensor.solar_controller_load_power',
    mpptYield: 'sensor.solar_controller_yield_today',
    mpptRssi: 'sensor.solar_controller_rssi',
    batt1Soc: 'sensor.battery_1_state_of_charge',
    batt1V: 'sensor.battery_1_voltage',
    batt1A: 'sensor.battery_1_current',
    batt1W: 'sensor.battery_1_power',
    batt1Ah: 'sensor.battery_1_consumed_ah',
    batt1Rem: 'sensor.battery_1_remaining_minutes',
    batt1Rssi: 'sensor.battery_1_rssi',
    batt2Soc: 'sensor.battery_2_state_of_charge',
    batt2V: 'sensor.battery_2_voltage',
    batt2A: 'sensor.battery_2_current',
    batt2W: 'sensor.battery_2_power',
    batt2Ah: 'sensor.battery_2_consumed_ah',
    batt2Rem: 'sensor.battery_2_remaining_minutes',
    batt2Rssi: 'sensor.battery_2_rssi',
    panelA3W: 'sensor.em16_a3_power',
    panelA3V: 'sensor.em16_a3_voltage',
    panelA3A: 'sensor.em16_a3_current',
    b3W: 'sensor.em16_b3_power',
    b3V: 'sensor.em16_b3_voltage',
    b3A: 'sensor.em16_b3_current',
    dumpTotal: 'sensor.sim_dump_load_power',
    sgPvW: 'sensor.sungold_sph302480a_pv_power',
    sgPvV: 'sensor.sungold_sph302480a_pv_voltage',
    sgPvA: 'sensor.sungold_sph302480a_pv_current',
    sgSoc: 'sensor.sungold_sph302480a_battery_soc',
    sgBattV: 'sensor.sungold_sph302480a_battery_voltage',
    sgBattA: 'sensor.sungold_sph302480a_battery_current',
    sgBattW: 'sensor.sungold_sph302480a_charging_power',
    sgCharge: 'sensor.sungold_sph302480a_charge_state',
    sgGridV: 'sensor.sungold_sph302480a_grid_voltage',
    sgGridA: 'sensor.sungold_sph302480a_grid_current',
    sgGridHz: 'sensor.sungold_sph302480a_grid_frequency',
    sgLoadW: 'sensor.sungold_sph302480a_load_active_power',
    sgLoadA: 'sensor.sungold_sph302480a_load_current',
    sgOutV: 'sensor.sungold_sph302480a_ac_output_voltage',
    sgOutHz: 'sensor.sungold_sph302480a_ac_output_frequency',
    sgMode: 'sensor.sungold_sph302480a_inverter_state',
    sgFail: 'sensor.sungold_sph302480a_fail_code',
    sgFault: 'binary_sensor.sungold_sph302480a_fault_active'
  };

  var PLUG_COUNT = 6;
  var EM16_CHANNELS = ['a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'b1', 'b2', 'b3', 'b4', 'b5', 'b6', 'c1', 'c2', 'c3', 'c4', 'c5', 'c6'];

  function $(id) {
    return document.getElementById(id);
  }

  function formatNum(n, decimals) {
    if (n === null || n === undefined || isNaN(n)) return null;
    if (decimals === undefined) decimals = 0;
    return Number(n).toFixed(decimals);
  }

  function parseFloatSafe(val) {
    if (val === null || val === undefined || val === '' || val === 'unknown' || val === 'unavailable') {
      return null;
    }
    var n = parseFloat(val);
    return isNaN(n) ? null : n;
  }

  var ENTITY_ALIASES = {
    'sensor.solar_controller_solar': ['sensor.solar_controller_solar_power'],
    'sensor.solar_controller_charge_state': ['sensor.solar_controller_battery_state'],
    'sensor.battery_1_state_of_charge': ['sensor.battery_1_soc'],
    'sensor.battery_2_state_of_charge': ['sensor.battery_2_soc'],
    'sensor.battery_1_voltage': ['sensor.battery_1_battery_voltage'],
    'sensor.battery_2_voltage': ['sensor.battery_2_battery_voltage'],
    'sensor.battery_1_current': ['sensor.battery_1_battery_current'],
    'sensor.battery_2_current': ['sensor.battery_2_battery_current'],
    'sensor.sungold_sph302480a_load_active_power': ['sensor.sungold_sph302480a_load_power']
  };

  function getEntity(entities, id) {
    if (!entities) return null;
    if (entities[id]) return entities[id];
    var aliases = ENTITY_ALIASES[id];
    if (!aliases) return null;
    for (var a = 0; a < aliases.length; a++) {
      if (entities[aliases[a]]) return entities[aliases[a]];
    }
    return null;
  }

  function getState(entities, id) {
    var ent = getEntity(entities, id);
    return ent ? ent.state : null;
  }

  function getPowerW(entities, id) {
    var state = getState(entities, id);
    return parseFloatSafe(state);
  }

  function getBatteryPower(entities, prefix) {
    var w = getPowerW(entities, 'sensor.' + prefix + '_power');
    if (w !== null) return w;
    var v = parseFloatSafe(getState(entities, 'sensor.' + prefix + '_voltage'));
    var a = parseFloatSafe(getState(entities, 'sensor.' + prefix + '_current'));
    if (v !== null && a !== null) return v * a;
    return null;
  }

  function isSwitchOn(entities, n) {
    var state = getState(entities, 'switch.sim_ac_plug_' + n);
    return state === 'on';
  }

  function isPlantLive() {
    return !!(lastSnapshot && lastSnapshot.mode === 'live');
  }

  function showDemoWatermark(snapshot) {
    if (!snapshot) return false;
    return snapshot.mode === 'demo';
  }

  function updateDemoWatermark(snapshot) {
    document.body.classList.toggle('demo-mode', showDemoWatermark(snapshot));
  }

  function setText(id, text) {
    var el = $(id);
    if (el) el.textContent = text;
  }

  function setValue(id, text) {
    setText(id, text);
  }

  function wattSignClass(n) {
    if (n === null || n === undefined || isNaN(n) || n === 0) return 'watt-zero';
    return n > 0 ? 'watt-pos' : 'watt-neg';
  }

  function wattLossClass(n) {
    if (n === null || n === undefined || isNaN(n) || n === 0) return 'watt-zero';
    return 'watt-neg';
  }

  function applyWattSign(el, n) {
    if (!el) return;
    el.classList.remove('watt-pos', 'watt-neg', 'watt-zero');
    el.classList.add(wattSignClass(n));
  }

  function setWattValue(id, watts, signed) {
    var el = $(id);
    if (!el) return;
    el.textContent = signed ? formatSignedW(watts) : formatW(watts);
    applyWattSign(el, watts);
  }

  function setSignedCurrent(id, v, a) {
    var el = $(id);
    if (!el) return;
    el.textContent = formatVA(v, a);
    applyWattSign(el, a);
  }

  function wattSpan(text, n, loss) {
    var cls = loss ? wattLossClass(n) : wattSignClass(n);
    return '<span class="' + cls + '">' + escapeHtml(text) + '</span>';
  }

  function setPip(id, active) {
    var el = $(id);
    if (!el) return;
    if (active) {
      el.classList.add('active');
    } else {
      el.classList.remove('active');
    }
  }

  function setFlow(pathId, flowing, reverse) {
    var el = $(pathId);
    if (!el) return;
    el.classList.remove('flowing', 'reverse');
    if (flowing && !reducedMotion) {
      el.classList.add('flowing');
      if (reverse) el.classList.add('reverse');
    }
  }

  function setHopLabel(pathId, watts, unmetered, signed) {
    var el = $('hop-' + pathId);
    if (!el) return;
    if (unmetered) {
      el.classList.add('unmetered');
    } else {
      el.classList.remove('unmetered');
    }
    el.textContent = signed ? formatSignedW(watts) : formatW(watts);
    applyWattSign(el, unmetered ? 0 : watts);
  }

  function panelHopW(entities) {
    var a3W = getPowerW(entities, ENTITY_IDS.panelA3W);
    return a3W !== null ? Math.abs(a3W) : null;
  }

  function trailerOutletW(entities) {
    var b3W = getPowerW(entities, ENTITY_IDS.b3W);
    if (b3W !== null && Math.abs(b3W) >= 0.5) {
      return Math.abs(b3W);
    }
    var a3W = getPowerW(entities, ENTITY_IDS.panelA3W);
    return a3W !== null ? Math.abs(a3W) : null;
  }

  function sungoldAcInW(entities, sgGridV, sgGridA) {
    if (sgGridV !== null && sgGridA !== null) {
      return Math.abs(sgGridV * sgGridA);
    }
    return null;
  }

  function ventFanEstimateW(trailerW, sgAcInW) {
    if (trailerW === null || sgAcInW === null) return null;
    var residual = trailerW - sgAcInW;
    return residual > 0 ? residual : 0;
  }

  function b3HopW(entities, panelW) {
    var b3W = getPowerW(entities, ENTITY_IDS.b3W);
    if (b3W !== null && Math.abs(b3W) >= 0.5) {
      return Math.abs(b3W);
    }
    return panelW;
  }

  function utiHopW(entities, b3W, sgGridV, sgGridA) {
    var acIn = sungoldAcInW(entities, sgGridV, sgGridA);
    if (acIn !== null) return acIn;
    if (b3W !== null && Math.abs(b3W) >= 0.5) return Math.abs(b3W);
    return null;
  }

  function mpptToBattHopW(entities, solarW) {
    var chargeW = getPowerW(entities, ENTITY_IDS.mpptChargeW);
    if (chargeW !== null && chargeW > 0) {
      return chargeW;
    }
    var mpptV = parseFloatSafe(getState(entities, ENTITY_IDS.mpptV));
    var mpptA = parseFloatSafe(getState(entities, ENTITY_IDS.mpptA));
    if (mpptV !== null && mpptA !== null && mpptA > 0.01) {
      return Math.abs(mpptV * mpptA);
    }
    return solarW;
  }

  // T2-KU jumper has no clamp. Estimate from T2 bus balance:
  // solar_W + (-batt1_W when discharging) leaves via T2 Renogy and/or jumper.
  // SmartShunt power is signed ([operation] current into battery is +).
  function jumperEstimateW(solarW, batt1W, t2RenogyW) {
    if (batt1W === null) return null;
    var solar = solarW === null ? 0 : solarW;
    var inv = t2RenogyW === null ? 0 : t2RenogyW;
    return solar - inv - batt1W;
  }

  function updateHopLabels(opts) {
    setHopLabel('path-t2-panels-mppt', opts.solarW, false);
    setHopLabel('path-t2-mppt-batt1', opts.mpptBattHopW, false);
    setHopLabel('path-t2-batt1-renogy', null, true);
    setHopLabel('path-t2-ku-jumper', opts.jumperW, false, true);
    setHopLabel('path-ku-panels-chargers', null, true);
    setHopLabel('path-ku-chargers-batt2', null, true);
    setHopLabel('path-ku-pwm-panels', null, true);
    setHopLabel('path-ku-pwm-batt2', null, true);
    setHopLabel('path-ku-batt2-inverter', opts.batt2W, false, true);
    setHopLabel('path-ku-renogy-panel', opts.panelW, false);
    setHopLabel('path-panel-b3', opts.b3W, false);
    setHopLabel('path-b3-outlet-sg-uti', opts.utiW, false);
    setHopLabel('path-sg-uti-sph', opts.utiW, false);
    setHopLabel('path-outlet-vent-fan', opts.ventW, opts.ventW === null);
    setHopLabel('path-sg-acout-pi4', null, true);
    var simW = opts.simBusW;
    var simUnmetered = simW === null;
    setHopLabel('path-sim-acbus', simW, simUnmetered);
    setHopLabel('path-sim-riser', simW, simUnmetered);
    for (var p = 1; p <= PLUG_COUNT; p++) {
      setHopLabel('path-sim-plug-' + p, opts.plugWs[p], false);
    }
    setHopLabel('path-sg-pv-panels', opts.sgPvW, false);
    setHopLabel('path-sg-pv-batt', opts.sgPvW, false);
    setHopLabel('path-sg-batt-inv', opts.sgBattW, false, true);
    setHopLabel('path-sg-inv-acout', opts.sgLoadW, false);
  }

  function setPlugOn(n, on) {
    var node = $('node-plug-' + n);
    if (!node) return;
    if (on) {
      node.classList.add('on');
    } else {
      node.classList.remove('on');
    }
  }

  function updateClock() {
    var now = new Date();
    var el = $('clock');
    if (el) {
      el.textContent = now.toLocaleTimeString(undefined, { hour12: false });
    }
  }

  function updateModeBadge(mode) {
    var badge = $('mode-badge');
    if (!badge) return;
    badge.classList.remove('mode-live', 'mode-waiting');
    if (mode === 'live' || mode === 'demo') {
      badge.textContent = mode;
      badge.classList.add('mode-live');
    } else {
      badge.textContent = 'waiting';
      badge.classList.add('mode-waiting');
    }
  }

  function updateProxyBanner(online) {
    var banner = $('proxy-banner');
    if (!banner) return;
    banner.hidden = online;
  }

  function formatW(w) {
    if (w === null || w === undefined || isNaN(w)) return '0 W';
    return formatNum(Math.abs(w), 0) + ' W';
  }

  function formatSignedW(w) {
    if (w === null || w === undefined || isNaN(w)) return '0 W';
    var sign = w > 0 ? '+' : w < 0 ? '-' : '';
    return sign + formatNum(Math.abs(w), 0) + ' W';
  }

  function formatVA(v, a) {
    return (v !== null ? formatNum(v, 1) + ' V' : '-- V') + ' / ' +
      (a !== null ? formatNum(a, 1) + ' A' : '-- A');
  }

  function formatAh(n) {
    if (n === null) return '-- Ah';
    var sign = n > 0 ? '+' : n < 0 ? '-' : '';
    return sign + formatNum(Math.abs(n), 1) + ' Ah';
  }

  function formatRem(n) {
    if (n === null) return 'rem --';
    return 'rem ' + formatNum(n, 0) + ' min';
  }

  function formatSocUnsynced(pct) {
    if (pct === null) return 'SoC unsynced --';
    return 'SoC unsynced ' + formatNum(pct, 0) + '%';
  }

  function renderMetrics(ai) {
    var container = $('ai-metrics');
    if (!container) return;
    if (!ai) {
      container.innerHTML = '';
      return;
    }
    var unsynced = !!ai.soc_unsynced;
    var fields = [
      { label: 'Surplus', key: 'surplus_w', signed: true },
      { label: 'Conversion losses', key: 'combined_losses_w', loss: true },
      { label: 'Vdrop D/C', key: 'combined_vdrop_v', suffix: ' V' },
      { label: 'Vdrop A/C', key: 'combined_vdrop_ac_v', suffix: ' V' },
      { label: 'Vdrop loss', key: 'combined_vdrop_loss_w', loss: true },
      { label: 'Path losses', key: 'combined_path_losses_w', loss: true },
      { label: 'After losses', key: 'surplus_after_path_losses_w', signed: true },
      { label: 'Vent fan', key: 'vent_fan_w' },
      { label: 'Panel in', key: 'panel_in_w' },
      { label: 'Solar', key: 'solar_w' },
      { label: 'Load', key: 'load_w' },
      { label: 'Sim dump loads', key: 'sim_plug_w' },
      { label: 'Eff. load', key: 'effective_load_w' },
      { label: 'T2 shunt V', key: 't2_shunt_v', suffix: ' V', zeroOk: true },
      { label: 'T2 shunt A', key: 't2_shunt_a', signedA: true, zeroOk: true },
      { label: 'KU shunt V', key: 'ku_shunt_v', suffix: ' V', zeroOk: true },
      { label: 'KU shunt A', key: 'ku_shunt_a', signedA: true, zeroOk: true },
      {
        label: unsynced ? 'SoC unsynced' : 'SoC',
        key: 'soc',
        suffix: '%',
        dim: unsynced
      }
    ];
    var html = '';
    for (var i = 0; i < fields.length; i++) {
      var f = fields[i];
      var val = ai[f.key];
      var display;
      if (val === null || val === undefined) {
        if (f.zeroOk && f.signedA) {
          val = 0;
          display = formatNum(0, 1) + ' A';
        } else if (f.zeroOk && f.suffix) {
          val = 0;
          display = formatNum(0, 1) + f.suffix;
        } else {
          display = '--';
        }
      } else if (f.signedA) {
        display = (val > 0 ? '+' : '') + formatNum(val, 1) + ' A';
      } else if (f.suffix) {
        display = formatNum(val, 1) + f.suffix;
      } else if (f.signed) {
        display = formatSignedW(val);
      } else {
        display = formatW(val);
      }
      var signClass = '';
      if (val !== null && val !== undefined) {
        if (f.loss) {
          signClass = ' ' + wattLossClass(val);
        } else if (f.signed || f.signedA || !f.suffix) {
          signClass = ' ' + wattSignClass(val);
        }
      }
      html += '<div class="metric-item' + (f.dim ? ' unsynced' : '') +
        '"><span class="metric-label">' + f.label +
        '</span><span class="metric-value' + signClass + '">' +
        escapeHtml(display) + '</span></div>';
    }
    if (ai.charge_state) {
      html += '<div class="metric-item"><span class="metric-label">Charge</span>' +
        '<span class="metric-value">' + escapeHtml(String(ai.charge_state)) + '</span></div>';
    }
    if (ai.soc_gate) {
      html += '<div class="metric-item unsynced"><span class="metric-label">SoC gate</span>' +
        '<span class="metric-value">' + escapeHtml(String(ai.soc_gate)) + '</span></div>';
    }
    if (ai.skipped) {
      html += '<div class="metric-item"><span class="metric-label">Skipped</span>' +
        '<span class="metric-value">' + escapeHtml(String(ai.skipped)) + '</span></div>';
    }
    container.innerHTML = html;
  }

  function hopCellW(val, unmetered) {
    if (unmetered) return 'unmetered';
    if (val === null || val === undefined) return '0 W';
    return formatW(val);
  }

  function renderWattHops(ai) {
    var body = $('watt-hops-body');
    if (!body) return;
    var hops = (ai && ai.watt_hops) || [];
    if (!hops.length) {
      body.innerHTML = '<tr><td colspan="5">waiting for hops</td></tr>';
      return;
    }
    var html = '';
    for (var i = 0; i < hops.length; i++) {
      var hop = hops[i];
      var lossCell = hop.unmetered
        ? 'unmetered'
        : (hop.loss_w === null || hop.loss_w === undefined ? '0 W' : formatW(hop.loss_w));
      var storedCell = (hop.stored_w === null || hop.stored_w === undefined)
        ? '0 W'
        : formatSignedW(hop.stored_w);
      html += '<tr title="' + escapeHtml(hop.note || '') + '">' +
        '<td>' + escapeHtml(hop.label || hop.id || '') + '</td>' +
        '<td>' + wattSpan(hopCellW(hop.watts_in, hop.unmetered), hop.unmetered ? 0 : hop.watts_in) + '</td>' +
        '<td>' + wattSpan(hopCellW(hop.watts_out, hop.unmetered), hop.unmetered ? 0 : hop.watts_out) + '</td>' +
        '<td>' + wattSpan(lossCell, hop.unmetered ? 0 : hop.loss_w, true) + '</td>' +
        '<td>' + wattSpan(storedCell, hop.stored_w) + '</td></tr>';
    }
    body.innerHTML = html;
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderDecisions(decisions) {
    var list = $('ai-actions');
    if (!list) return;
    if (!decisions || decisions.length === 0) {
      list.innerHTML = '<li class="ai-action-placeholder">no decisions</li>';
      return;
    }
    var html = '';
    for (var i = 0; i < decisions.length; i++) {
      var d = decisions[i];
      var targetClass = 'target-' + (d.target || 'skip');
      html += '<li class="ai-decision ' + targetClass + '">' +
        '<span class="entity-id">' + escapeHtml(d.entity_id || '?') + '</span>' +
        '<span class="decision-arrow">' + escapeHtml(d.current || '?') +
        ' &rarr; ' + escapeHtml(d.target || '?') + '</span>';
      if (d.reason) {
        html += '<span class="reason">' + escapeHtml(d.reason) + '</span>';
      }
      html += '</li>';
    }
    list.innerHTML = html;
  }

  function channelNote(ch) {
    if (ch === 'a3') return 'panel hot leg';
    if (ch === 'b3') return 'Sungold outlet breaker';
    if (ch === 'b2') return 'return of A3; do not add';
    if (ch === 'a2' || ch === 'b4') return 'candidate T2 Renogy idle';
    if (ch.charAt(0) === 'c') return 'unused CT';
    return '';
  }

  function renderEm16Meters(entities) {
    var container = $('em16-meters');
    if (!container) return;
    var html = '';
    for (var i = 0; i < EM16_CHANNELS.length; i++) {
      var ch = EM16_CHANNELS[i];
      var prefix = 'sensor.em16_' + ch + '_';
      var w = parseFloatSafe(getState(entities, prefix + 'power'));
      var v = parseFloatSafe(getState(entities, prefix + 'voltage'));
      var a = parseFloatSafe(getState(entities, prefix + 'current'));
      var live = w !== null && Math.abs(w) >= 1;
      var cls = 'meter-card';
      if (ch === 'b2') cls += ' return';
      if (ch === 'a3' || ch === 'b3') cls += ' highlight';
      cls += live ? ' live' : ' idle';
      var note = channelNote(ch);
      html += '<div class="' + cls + '">' +
        '<div class="meter-ch">' + ch.toUpperCase() +
        (note ? ' <span class="meter-va">' + escapeHtml(note) + '</span>' : '') +
        '</div>' +
        '<div class="meter-w ' + wattSignClass(w) + '">' + escapeHtml(formatSignedW(w)) + '</div>' +
        '<div class="meter-va ' + wattSignClass(a) + '">' + escapeHtml(formatVA(v, a)) + '</div>' +
        '</div>';
    }
    container.innerHTML = html;
  }

  function formatRssi(n) {
    if (n === null) return 'rssi --';
    return 'rssi ' + formatNum(n, 0);
  }

  function applySnapshot(snapshot) {
    if (!snapshot) return;
    lastSnapshot = snapshot;
    var entities = snapshot.entities || {};

    updateDemoWatermark(snapshot);
    updateModeBadge(snapshot.mode);
    setFetchedAt(snapshot.fetched_at, snapshot.mode);

    var labelEl = $('snapshot-label');
    if (labelEl) {
      var label = snapshot.label || '';
      var missing = snapshot.missing_entity_ids;
      if (missing && missing.length) {
        var plantMissing = [];
        for (var mi = 0; mi < missing.length; mi++) {
          if (missing[mi].indexOf('sim_ac_plug') === -1 && missing[mi].indexOf('sim_dump') === -1) {
            plantMissing.push(missing[mi]);
          }
        }
        if (plantMissing.length) {
          var extra = 'Missing HA ids: ' + plantMissing.slice(0, 8).join(', ');
          if (plantMissing.length > 8) extra += ' (+' + (plantMissing.length - 8) + ')';
          label = label ? (label + ' -- ' + extra) : extra;
        }
      }
      labelEl.textContent = label;
      labelEl.hidden = !label;
    }

    var solarW = getPowerW(entities, ENTITY_IDS.solar);
    setWattValue('val-solar-w', solarW);
    setWattValue('val-t2-panels-w', solarW);
    // KU Victron+PWM residual is not HA W (needs KU Renogy DC). Do not print 2x T2.
    setWattValue('val-ku-victron-panels-w', 0);
    setWattValue('val-ku-pwm-panels-w', 0);
    setPip('pip-solar', solarW !== null && solarW > 0);

    var battState = getState(entities, ENTITY_IDS.battState);
    setValue('val-batt-state', battState || '--');
    var mpptV = parseFloatSafe(getState(entities, ENTITY_IDS.mpptV));
    var mpptA = parseFloatSafe(getState(entities, ENTITY_IDS.mpptA));
    var mpptChargeW = getPowerW(entities, ENTITY_IDS.mpptChargeW);
    var mpptLoadA = parseFloatSafe(getState(entities, ENTITY_IDS.mpptLoadA));
    var mpptLoadW = getPowerW(entities, ENTITY_IDS.mpptLoadW);
    var mpptYield = parseFloatSafe(getState(entities, ENTITY_IDS.mpptYield));
    var mpptRssi = parseFloatSafe(getState(entities, ENTITY_IDS.mpptRssi));
    setValue('val-mppt-va', formatVA(mpptV, mpptA));
    setValue('val-mppt-charge-w', 'chg ' + formatW(mpptChargeW));
    applyWattSign($('val-mppt-charge-w'), mpptChargeW);
    setValue(
      'val-mppt-load',
      'load ' + formatW(mpptLoadW) +
        (mpptLoadA !== null ? ' / ' + formatNum(mpptLoadA, 1) + ' A' : '')
    );
    applyWattSign($('val-mppt-load'), mpptLoadW);
    setValue(
      'val-mppt-yield',
      (mpptYield !== null ? 'yield ' + formatNum(mpptYield, 0) + ' Wh' : 'yield --') +
        ' ' + formatRssi(mpptRssi)
    );

    var batt1Soc = parseFloatSafe(getState(entities, ENTITY_IDS.batt1Soc));
    var batt1V = parseFloatSafe(getState(entities, ENTITY_IDS.batt1V));
    var batt1A = parseFloatSafe(getState(entities, ENTITY_IDS.batt1A));
    var batt1W = getBatteryPower(entities, 'battery_1');
    setValue('val-batt1-soc', formatSocUnsynced(batt1Soc));
    setSignedCurrent('val-batt1-va', batt1V, batt1A);
    setWattValue('val-batt1-w', batt1W, true);
    setValue('val-batt1-ah', formatAh(parseFloatSafe(getState(entities, ENTITY_IDS.batt1Ah))));
    setValue(
      'val-batt1-rem',
      formatRem(parseFloatSafe(getState(entities, ENTITY_IDS.batt1Rem))) +
        ' ' + formatRssi(parseFloatSafe(getState(entities, ENTITY_IDS.batt1Rssi)))
    );
    setPip('pip-batt1', batt1W !== null && Math.abs(batt1W) > 0);

    var batt2Soc = parseFloatSafe(getState(entities, ENTITY_IDS.batt2Soc));
    var batt2V = parseFloatSafe(getState(entities, ENTITY_IDS.batt2V));
    var batt2A = parseFloatSafe(getState(entities, ENTITY_IDS.batt2A));
    var batt2W = getBatteryPower(entities, 'battery_2');
    setValue('val-batt2-soc', formatSocUnsynced(batt2Soc));
    setSignedCurrent('val-batt2-va', batt2V, batt2A);
    setWattValue('val-batt2-w', batt2W, true);
    setValue('val-batt2-ah', formatAh(parseFloatSafe(getState(entities, ENTITY_IDS.batt2Ah))));
    setValue(
      'val-batt2-rem',
      formatRem(parseFloatSafe(getState(entities, ENTITY_IDS.batt2Rem))) +
        ' ' + formatRssi(parseFloatSafe(getState(entities, ENTITY_IDS.batt2Rssi)))
    );
    setPip('pip-batt2', batt2W !== null && Math.abs(batt2W) > 0);

    var panelA3W = getPowerW(entities, ENTITY_IDS.panelA3W);
    var panelA3V = parseFloatSafe(getState(entities, ENTITY_IDS.panelA3V));
    var panelA3A = parseFloatSafe(getState(entities, ENTITY_IDS.panelA3A));
    var panelW = panelHopW(entities);
    setWattValue('val-panel-a3-w', panelA3W);
    setValue('val-panel-a3-va', 'A3 ' + formatVA(panelA3V, panelA3A));
    setPip('pip-panel', panelW !== null && panelW > 0);

    var b3RawW = getPowerW(entities, ENTITY_IDS.b3W);
    var b3V = parseFloatSafe(getState(entities, ENTITY_IDS.b3V));
    var b3A = parseFloatSafe(getState(entities, ENTITY_IDS.b3A));
    var b3W = b3HopW(entities, panelW);
    setWattValue('val-b3-w', b3RawW !== null ? b3RawW : panelA3W);
    setValue('val-b3-va', formatVA(b3V, b3A));
    setPip('pip-b3', b3W !== null && b3W > 0);

    setWattValue('val-t2-renogy-w', 0);
    setPip('pip-t2-renogy', false);
    setWattValue('val-ku-renogy-w', 0);

    var totalDump = 0;
    var hasDump = false;
    var anyPlugOn = false;
    var plugWs = {};
    for (var p = 1; p <= PLUG_COUNT; p++) {
      var plugOn = isSwitchOn(entities, p);
      var plugW = getPowerW(entities, 'sensor.sim_ac_plug_' + p + '_power');
      plugWs[p] = plugW;
      setWattValue('val-plug-' + p + '-w', plugW);
      setPip('pip-plug-' + p, plugOn || (plugW !== null && plugW > 0));
      setPlugOn(p, plugOn);
      setFlow('path-sim-plug-' + p, plugOn || (plugW !== null && plugW > 0), false);
      if (plugOn) anyPlugOn = true;
      if (plugW !== null) {
        totalDump += plugW;
        hasDump = true;
      }
    }

    var dumpSensor = getPowerW(entities, ENTITY_IDS.dumpTotal);
    setWattValue('val-dump-w', dumpSensor !== null ? dumpSensor : (hasDump ? totalDump : null));

    var sgPvW = getPowerW(entities, ENTITY_IDS.sgPvW);
    var sgPvV = parseFloatSafe(getState(entities, ENTITY_IDS.sgPvV));
    var sgPvA = parseFloatSafe(getState(entities, ENTITY_IDS.sgPvA));
    setWattValue('val-sg-panels-w', sgPvW);
    setWattValue('val-sg-pv-w', sgPvW);
    setValue('val-sg-pv-va', formatVA(sgPvV, sgPvA));
    setPip('pip-sg-pv', sgPvW !== null && sgPvW > 0);

    var sgSoc = parseFloatSafe(getState(entities, ENTITY_IDS.sgSoc));
    var sgBattV = parseFloatSafe(getState(entities, ENTITY_IDS.sgBattV));
    var sgBattA = parseFloatSafe(getState(entities, ENTITY_IDS.sgBattA));
    var sgBattW = getPowerW(entities, ENTITY_IDS.sgBattW);
    var sgCharge = getState(entities, ENTITY_IDS.sgCharge);
    setValue('val-sg-soc', sgSoc !== null ? 'remain ' + formatNum(sgSoc, 0) + '%' : 'remain --');
    setSignedCurrent('val-sg-batt-va', sgBattV, sgBattA);
    setWattValue('val-sg-batt-w', sgBattW, true);
    setValue('val-sg-charge', sgCharge || '--');
    setPip('pip-sg-batt', sgBattW !== null && Math.abs(sgBattW) > 0);

    var sgGridV = parseFloatSafe(getState(entities, ENTITY_IDS.sgGridV));
    var sgGridA = parseFloatSafe(getState(entities, ENTITY_IDS.sgGridA));
    var sgGridHz = parseFloatSafe(getState(entities, ENTITY_IDS.sgGridHz));
    var trailerW = trailerOutletW(entities);
    var utiW = utiHopW(entities, b3W, sgGridV, sgGridA);
    var ventW = ventFanEstimateW(trailerW, utiW);
    setWattValue('val-sg-uti-w', utiW);
    setValue('val-sg-uti-va', formatVA(sgGridV, sgGridA));
    setValue('val-sg-uti-hz', sgGridHz !== null ? formatNum(sgGridHz, 0) + ' Hz' : '-- Hz');
    setPip('pip-sg-uti', utiW !== null && utiW > 0);
    if (ventW === null) {
      setValue('val-vent-fan-w', 'unmetered');
      applyWattSign($('val-vent-fan-w'), 0);
    } else {
      setWattValue('val-vent-fan-w', ventW);
    }
    setPip('pip-vent-fan', ventW !== null && ventW > 0.5);
    setValue('val-pi4-w', 'unmetered');
    applyWattSign($('val-pi4-w'), 0);
    setPip('pip-pi4', true);

    var sgLoadW = getPowerW(entities, ENTITY_IDS.sgLoadW);
    var sgLoadA = parseFloatSafe(getState(entities, ENTITY_IDS.sgLoadA));
    var sgOutV = parseFloatSafe(getState(entities, ENTITY_IDS.sgOutV));
    var sgOutHz = parseFloatSafe(getState(entities, ENTITY_IDS.sgOutHz));
    setWattValue('val-sg-load-w', sgLoadW);
    setValue('val-sg-load-va', formatVA(sgOutV, sgLoadA));
    setValue('val-sg-load-hz', sgOutHz !== null ? formatNum(sgOutHz, 0) + ' Hz' : '-- Hz');
    setPip('pip-sg-acout', sgLoadW !== null && Math.abs(sgLoadW) > 0);

    var sgMode = getState(entities, ENTITY_IDS.sgMode);
    var sgFail = getState(entities, ENTITY_IDS.sgFail);
    var sgFault = getState(entities, ENTITY_IDS.sgFault);
    setValue('val-sg-mode', sgMode ? 'mode ' + sgMode : 'mode --');
    var faultOn = sgFault === 'on' || sgFault === 'true';
    setValue('val-sg-fault', faultOn ? 'fault on' : (sgFail && sgFail !== '0' ? 'fail ' + sgFail : 'fault off'));
    setPip('pip-sg-inv', (sgBattW !== null && Math.abs(sgBattW) > 0) || (sgLoadW !== null && sgLoadW > 0) || faultOn);

    renderEm16Meters(entities);

    var ai = snapshot.ai || {};
    setText('ai-thinking', ai.thinking || (proxyOnline ? 'idle' : 'waiting for proxy'));
    renderMetrics(ai);
    renderWattHops(ai);
    renderDecisions(ai.decisions);

    var simBusW = hasDump && totalDump > 0 ? totalDump : null;
    var mpptBattHopW = mpptToBattHopW(entities, solarW);
    var jumperW = jumperEstimateW(solarW, batt1W, 0);
    var jumperDir = $('lbl-jumper-dir');
    if (jumperDir) {
      if (jumperW === null || Math.abs(jumperW) < 0.5) {
        jumperDir.textContent = 'T2-KU jumper est.';
      } else if (jumperW > 0) {
        jumperDir.textContent = 'T2 to KU jumper est.';
      } else {
        jumperDir.textContent = 'KU to T2 jumper est.';
      }
    }
    updateHopLabels({
      solarW: solarW,
      mpptBattHopW: mpptBattHopW,
      jumperW: jumperW,
      batt2W: batt2W,
      panelW: panelW,
      b3W: b3W,
      utiW: utiW,
      ventW: ventW,
      simBusW: simBusW,
      plugWs: plugWs,
      sgPvW: sgPvW,
      sgBattW: sgBattW,
      sgLoadW: sgLoadW
    });
    updateFlows({
      solarW: solarW,
      batt1W: batt1W,
      batt2W: batt2W,
      jumperW: jumperW,
      panelW: panelW,
      b3W: b3W,
      utiW: utiW,
      ventW: ventW,
      plugTotal: totalDump,
      anyPlugOn: anyPlugOn,
      sgPvW: sgPvW,
      sgBattW: sgBattW,
      sgLoadW: sgLoadW
    });
    setPip(
      'pip-inverter',
      (batt2W !== null && batt2W < 0) || (utiW !== null && utiW > 0)
    );
  }

  function setFetchedAt(iso, mode) {
    var el = $('fetched-at');
    if (!el) return;
    if (!iso) {
      el.textContent = 'no fetch';
      el.removeAttribute('datetime');
      return;
    }
    el.setAttribute('datetime', iso);
    var parsed = new Date(iso);
    if (isNaN(parsed.getTime())) {
      el.textContent = iso;
      return;
    }
    el.textContent = 'HA ' + parsed.toLocaleTimeString(undefined, { hour12: false });
  }

  function updateFlows(opts) {
    var solarFlow = opts.solarW !== null && opts.solarW > 0;
    var batt1Charge = opts.batt1W !== null && opts.batt1W > 0;
    var batt1Discharge = opts.batt1W !== null && opts.batt1W < 0;
    setFlow('path-t2-panels-mppt', solarFlow, false);
    setFlow('path-t2-mppt-batt1', solarFlow || batt1Charge || batt1Discharge, batt1Discharge);
    setFlow('path-t2-batt1-renogy', false, false);
    var jumperAbs = opts.jumperW !== null ? Math.abs(opts.jumperW) : 0;
    setFlow('path-t2-ku-jumper', jumperAbs >= 0.5, opts.jumperW !== null && opts.jumperW < 0);

    var batt2Discharge = opts.batt2W !== null && opts.batt2W < 0;
    var panelFlow = opts.panelW !== null && opts.panelW > 0;
    var b3Flow = opts.b3W !== null && opts.b3W > 0;
    var utiFlow = opts.utiW !== null && opts.utiW > 0;
    var plugLoad = (opts.plugTotal || 0) > 0 || opts.anyPlugOn;
    setFlow('path-ku-batt2-inverter', batt2Discharge || utiFlow, false);
    setFlow('path-ku-renogy-panel', panelFlow || b3Flow || utiFlow, false);
    setFlow('path-panel-b3', b3Flow || utiFlow, false);
    setFlow('path-b3-outlet-sg-uti', utiFlow, false);
    setFlow('path-sg-uti-sph', utiFlow, false);
    setFlow('path-outlet-vent-fan', opts.ventW !== null && opts.ventW > 0.5, false);
    setFlow('path-sg-acout-pi4', true, false);
    setFlow('path-sim-acbus', plugLoad, false);
    setFlow('path-sim-riser', plugLoad, false);
    setFlow('path-sg-pv-panels', opts.sgPvW !== null && opts.sgPvW > 0, false);
    setFlow('path-sg-pv-batt', opts.sgPvW !== null && opts.sgPvW > 0, false);
    setFlow('path-sg-batt-inv', opts.sgBattW !== null && Math.abs(opts.sgBattW) > 0, false);
    setFlow(
      'path-sg-inv-acout',
      (opts.sgLoadW !== null && opts.sgLoadW > 0) || plugLoad,
      false
    );
  }

  function formatHistoryTime(iso) {
    if (!iso) return '--';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return String(iso);
    return d.toLocaleString();
  }

  function renderSparkline(points) {
    var poly = $('history-spark-poly');
    if (!poly) return;
    if (!points || points.length < 2) {
      poly.setAttribute('points', '');
      return;
    }
    var nums = [];
    for (var i = 0; i < points.length; i++) {
      var n = parseFloatSafe(points[i].state);
      if (n !== null) nums.push(n);
    }
    if (nums.length < 2) {
      poly.setAttribute('points', '');
      return;
    }
    var min = nums[0];
    var max = nums[0];
    for (var j = 1; j < nums.length; j++) {
      if (nums[j] < min) min = nums[j];
      if (nums[j] > max) max = nums[j];
    }
    var span = max - min;
    if (span < 0.001) span = 1;
    var width = 240;
    var height = 48;
    var coords = [];
    for (var k = 0; k < nums.length; k++) {
      var x = (k / (nums.length - 1)) * width;
      var y = height - ((nums[k] - min) / span) * (height - 4) - 2;
      coords.push(x.toFixed(1) + ',' + y.toFixed(1));
    }
    poly.setAttribute('points', coords.join(' '));
  }

  function renderHistoryTable(points, currentRow) {
    var tbody = $('history-tbody');
    if (!tbody) return;
    var rows = [];
    if (currentRow) {
      rows.push(currentRow);
    }
    if (points && points.length) {
      var start = Math.max(0, points.length - HISTORY_TABLE_ROWS);
      for (var i = points.length - 1; i >= start; i--) {
        rows.push(points[i]);
      }
    }
    if (!rows.length && !currentRow) {
      tbody.innerHTML = '<tr><td colspan="2">no recorded history</td></tr>';
      return;
    }
    var html = '';
    var limit = Math.min(rows.length, HISTORY_TABLE_ROWS);
    for (var r = 0; r < limit; r++) {
      var row = rows[r];
      var timeLabel = row.is_current ?
        'current' :
        formatHistoryTime(row.last_changed || row.last_updated);
      var rowClass = row.is_current ? ' class="history-current"' : '';
      html += '<tr' + rowClass + '><td>' + escapeHtml(timeLabel) +
        '</td><td>' + escapeHtml(String(row.state)) + '</td></tr>';
    }
    tbody.innerHTML = html;
  }

  function showHistoryPanel(title, entityId) {
    var panel = $('history-panel');
    if (!panel) return;
    panel.hidden = false;
    setText('history-title', title || 'History');
    setText('history-entity-id', entityId || '');
    selectedHistoryEntity = entityId;
  }

  function hideHistoryPanel() {
    var panel = $('history-panel');
    if (panel) panel.hidden = true;
    selectedHistoryEntity = null;
  }

  function fetchHistory(entityId) {
    var status = $('history-status');
    if (status) status.textContent = 'loading...';
    return fetch(
      '/api/history?entity_id=' + encodeURIComponent(entityId) + '&hours=' + HISTORY_HOURS,
      { method: 'GET', headers: { Accept: 'application/json' }, cache: 'no-store' }
    ).then(function (res) {
      return res.json().then(function (body) {
        return { ok: res.ok, status: res.status, body: body };
      });
    });
  }

  function openHistoryForNode(node) {
    var entityId = node.getAttribute('data-history-entity');
    if (!entityId) return;
    var title = node.getAttribute('data-history-title') || entityId;
    showHistoryPanel(title, entityId);
    var entities = (lastSnapshot && lastSnapshot.entities) || {};
    var ent = getEntity(entities, entityId);
    var currentRow = null;
    if (ent) {
      currentRow = {
        state: ent.state,
        last_changed: ent.last_changed || ent.last_updated || lastSnapshot.fetched_at,
        is_current: true
      };
    }
    if (!isPlantLive()) {
      if ($('history-status')) {
        $('history-status').textContent = 'history unavailable without HA token';
      }
      renderSparkline([]);
      renderHistoryTable([], currentRow);
      return;
    }
    fetchHistory(entityId)
      .then(function (result) {
        var statusEl = $('history-status');
        if (!result.ok) {
          if (statusEl) {
            statusEl.textContent = (result.body && result.body.error) ?
              String(result.body.error) : 'history fetch failed';
          }
          renderSparkline([]);
          renderHistoryTable([], currentRow);
          return;
        }
        var points = (result.body && result.body.points) || [];
        if (statusEl) {
          statusEl.textContent = points.length ?
            ('last ' + result.body.hours + ' h, ' + points.length + ' points') :
            (currentRow ? 'current snapshot only (no recorded history)' : 'no recorded history');
        }
        renderSparkline(points);
        renderHistoryTable(points, currentRow);
      })
      .catch(function () {
        if ($('history-status')) $('history-status').textContent = 'history fetch failed';
        renderSparkline([]);
        renderHistoryTable([], currentRow);
      });
  }

  function initHistoryClicks() {
    var nodes = document.querySelectorAll('.node-clickable[data-history-entity]');
    for (var i = 0; i < nodes.length; i++) {
      nodes[i].addEventListener('click', function (ev) {
        openHistoryForNode(ev.currentTarget);
      });
      nodes[i].addEventListener('keydown', function (ev) {
        if (ev.key === 'Enter' || ev.key === ' ') {
          ev.preventDefault();
          openHistoryForNode(ev.currentTarget);
        }
      });
    }
    var closeBtn = $('history-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', hideHistoryPanel);
    }
  }

  function readStoredView() {
    try {
      var stored = localStorage.getItem(VIEW_STORAGE_KEY);
      if (stored === 'production' || stored === 'demo') {
        return stored;
      }
    } catch (err) {
      /* SecurityError or file: URL */
    }
    return 'production';
  }

  function storeView(view) {
    try {
      localStorage.setItem(VIEW_STORAGE_KEY, view);
    } catch (err) {
      /* SecurityError or file: URL */
    }
  }

  function setViewToggle(view) {
    var prodBtn = $('view-production');
    var demoBtn = $('view-demo');
    if (prodBtn) {
      prodBtn.setAttribute('aria-pressed', view === 'production' ? 'true' : 'false');
    }
    if (demoBtn) {
      demoBtn.setAttribute('aria-pressed', view === 'demo' ? 'true' : 'false');
    }
  }

  function switchView(view) {
    if (view !== 'production' && view !== 'demo') {
      return;
    }
    if (view === currentView) {
      return;
    }
    currentView = view;
    storeView(view);
    setViewToggle(view);
    poll();
  }

  function initViewToggle() {
    currentView = readStoredView();
    setViewToggle(currentView);
    var prodBtn = $('view-production');
    var demoBtn = $('view-demo');
    if (prodBtn) {
      prodBtn.addEventListener('click', function () {
        switchView('production');
      });
    }
    if (demoBtn) {
      demoBtn.addEventListener('click', function () {
        switchView('demo');
      });
    }
  }

  function fetchSnapshot() {
    return fetch('/api/snapshot?view=' + encodeURIComponent(currentView), {
      method: 'GET',
      headers: { Accept: 'application/json' },
      cache: 'no-store'
    }).then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    });
  }

  function poll() {
    fetchSnapshot()
      .then(function (data) {
        proxyOnline = true;
        updateProxyBanner(true);
        lastSnapshot = data;
        applySnapshot(data);
      })
      .catch(function () {
        proxyOnline = false;
        updateProxyBanner(false);
        if (!lastSnapshot) {
          updateModeBadge(null);
          setText('ai-thinking', 'waiting for proxy');
        } else {
          applySnapshot(lastSnapshot);
        }
      });
  }

  function init() {
    updateClock();
    setInterval(updateClock, 1000);
    initViewToggle();
    initHistoryClicks();
    poll();
    setInterval(poll, POLL_MS);

    if (window.matchMedia) {
      var mq = window.matchMedia('(prefers-reduced-motion: reduce)');
      mq.addEventListener('change', function (e) {
        reducedMotion = e.matches;
        if (lastSnapshot) applySnapshot(lastSnapshot);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
