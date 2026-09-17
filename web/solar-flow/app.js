(function () {
  'use strict';

  var POLL_MS = 2000;
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
    em16: 'sensor.em16_a3_power',
    em16V: 'sensor.em16_a3_voltage',
    em16A: 'sensor.em16_a3_current',
    soakTotal: 'sensor.sim_soak_load_power',
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

  function isDemo() {
    return !!(lastSnapshot && lastSnapshot.mode === 'demo');
  }

  function demoText(text) {
    if (!isDemo()) return text;
    if (String(text).indexOf('DEMO ') === 0) return text;
    return 'DEMO ' + text;
  }

  function setText(id, text) {
    var el = $(id);
    if (el) el.textContent = text;
  }

  function setValue(id, text) {
    setText(id, demoText(text));
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

  function setHopLabel(pathId, watts, unmetered) {
    var el = $('hop-' + pathId);
    if (!el) return;
    if (unmetered || watts === null || watts === undefined) {
      el.textContent = '-- W';
      el.classList.add('unmetered');
      return;
    }
    el.classList.remove('unmetered');
    el.textContent = demoText(formatW(watts));
  }

  function outletHopW(entities, em16W, sgGridV, sgGridA) {
    if (em16W !== null) {
      return Math.abs(em16W);
    }
    if (sgGridV !== null && sgGridA !== null && Math.abs(sgGridA) > 0.01) {
      return Math.abs(sgGridV * sgGridA);
    }
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

  function updateHopLabels(opts) {
    setHopLabel('path-t2-panels-mppt', opts.solarW, false);
    setHopLabel('path-t2-mppt-batt1', opts.mpptBattHopW, false);
    setHopLabel('path-t2-batt1-renogy', null, true);
    setHopLabel('path-ku-panels-chargers', null, true);
    setHopLabel('path-ku-chargers-batt2', null, true);
    setHopLabel('path-ku-pwm-panels', null, true);
    setHopLabel('path-ku-pwm-batt2', null, true);
    setHopLabel('path-ku-batt2-inverter', opts.batt2W !== null ? Math.abs(opts.batt2W) : null, false);
    var acW = opts.acBusW;
    var acBusUnmetered = acW === null;
    setHopLabel('path-inverter-acbus', acW, acBusUnmetered);
    setHopLabel('path-ac-riser', acW, acBusUnmetered);
    setHopLabel('path-ac-em16', opts.em16W !== null ? Math.abs(opts.em16W) : null, false);
    for (var p = 1; p <= PLUG_COUNT; p++) {
      setHopLabel('path-ac-plug-' + p, opts.plugWs[p], false);
    }
    setHopLabel('path-ku-outlet-sg-acin', opts.outletW, false);
    setHopLabel('path-sg-pv-panels', opts.sgPvW, false);
    setHopLabel('path-sg-pv-batt', opts.sgPvW, false);
    setHopLabel('path-sg-batt-inv', opts.sgBattW !== null ? Math.abs(opts.sgBattW) : null, false);
    setHopLabel('path-sg-acin-inv', opts.outletW, false);
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
    badge.classList.remove('mode-live', 'mode-demo', 'mode-waiting');
    if (mode === 'live') {
      badge.textContent = 'live';
      badge.classList.add('mode-live');
    } else if (mode === 'demo') {
      badge.textContent = 'DEMO not live';
      badge.classList.add('mode-demo');
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
    if (w === null) return '-- W';
    return formatNum(Math.abs(w), 0) + ' W';
  }

  function formatSignedW(w) {
    if (w === null) return '-- W';
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
      { label: 'Solar', key: 'solar_w' },
      { label: 'Load', key: 'load_w' },
      { label: 'Sim plugs', key: 'sim_plug_w' },
      { label: 'Eff. load', key: 'effective_load_w' },
      { label: 'Shunt V', key: 'shunt_v', suffix: ' V' },
      { label: 'Shunt A', key: 'shunt_a', signedA: true },
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
        display = '--';
      } else if (f.signedA) {
        display = (val > 0 ? '+' : '') + formatNum(val, 1) + ' A';
      } else if (f.suffix) {
        display = formatNum(val, 1) + f.suffix;
      } else if (f.signed) {
        display = formatSignedW(val);
      } else {
        display = formatW(val);
      }
      html += '<div class="metric-item' + (f.dim ? ' unsynced' : '') +
        '"><span class="metric-label">' + f.label +
        '</span><span class="metric-value">' + escapeHtml(demoText(display)) + '</span></div>';
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
    if (ch === 'a3') return 'Sungold AC-in clamp';
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
      cls += live ? ' live' : ' idle';
      var note = channelNote(ch);
      html += '<div class="' + cls + '">' +
        '<div class="meter-ch">' + ch.toUpperCase() +
        (note ? ' <span class="meter-va">' + escapeHtml(note) + '</span>' : '') +
        '</div>' +
        '<div class="meter-w">' + escapeHtml(demoText(formatSignedW(w))) + '</div>' +
        '<div class="meter-va">' + escapeHtml(demoText(formatVA(v, a))) + '</div>' +
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
    var demo = snapshot.mode === 'demo';
    document.body.classList.toggle('demo-mode', demo);
    var watermark = $('demo-watermark');
    if (watermark) watermark.hidden = !demo;
    var demoBanner = $('demo-banner');
    if (demoBanner) demoBanner.hidden = !demo;

    updateModeBadge(snapshot.mode);
    setFetchedAt(snapshot.fetched_at, snapshot.mode);

    var labelEl = $('snapshot-label');
    if (labelEl) {
      var label = snapshot.label || '';
      var missing = snapshot.missing_entity_ids;
      if (snapshot.mode === 'live' && missing && missing.length) {
        var extra = 'Missing HA ids: ' + missing.slice(0, 8).join(', ');
        if (missing.length > 8) extra += ' (+' + (missing.length - 8) + ')';
        label = label ? (label + ' -- ' + extra) : extra;
      }
      labelEl.textContent = label;
      labelEl.hidden = !label;
    }

    var solarW = getPowerW(entities, ENTITY_IDS.solar);
    setValue('val-solar-w', formatW(solarW));
    setValue('val-t2-panels-w', formatW(solarW));
    setValue('val-ku-victron-panels-w', '-- W');
    setValue('val-ku-pwm-panels-w', '-- W');
    setPip('pip-solar', !demo && solarW !== null && solarW > 0);

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
    setValue(
      'val-mppt-load',
      'load ' + (mpptLoadW !== null ? formatW(mpptLoadW) : '-- W') +
        (mpptLoadA !== null ? ' / ' + formatNum(mpptLoadA, 1) + ' A' : '')
    );
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
    setValue('val-batt1-va', formatVA(batt1V, batt1A));
    setValue('val-batt1-w', formatSignedW(batt1W));
    setValue('val-batt1-ah', formatAh(parseFloatSafe(getState(entities, ENTITY_IDS.batt1Ah))));
    setValue(
      'val-batt1-rem',
      formatRem(parseFloatSafe(getState(entities, ENTITY_IDS.batt1Rem))) +
        ' ' + formatRssi(parseFloatSafe(getState(entities, ENTITY_IDS.batt1Rssi)))
    );
    setPip('pip-batt1', !demo && batt1W !== null && Math.abs(batt1W) > 0);

    var batt2Soc = parseFloatSafe(getState(entities, ENTITY_IDS.batt2Soc));
    var batt2V = parseFloatSafe(getState(entities, ENTITY_IDS.batt2V));
    var batt2A = parseFloatSafe(getState(entities, ENTITY_IDS.batt2A));
    var batt2W = getBatteryPower(entities, 'battery_2');
    setValue('val-batt2-soc', formatSocUnsynced(batt2Soc));
    setValue('val-batt2-va', formatVA(batt2V, batt2A));
    setValue('val-batt2-w', formatSignedW(batt2W));
    setValue('val-batt2-ah', formatAh(parseFloatSafe(getState(entities, ENTITY_IDS.batt2Ah))));
    setValue(
      'val-batt2-rem',
      formatRem(parseFloatSafe(getState(entities, ENTITY_IDS.batt2Rem))) +
        ' ' + formatRssi(parseFloatSafe(getState(entities, ENTITY_IDS.batt2Rssi)))
    );
    setPip('pip-batt2', !demo && batt2W !== null && Math.abs(batt2W) > 0);

    var em16W = getPowerW(entities, ENTITY_IDS.em16);
    var em16V = parseFloatSafe(getState(entities, ENTITY_IDS.em16V));
    var em16A = parseFloatSafe(getState(entities, ENTITY_IDS.em16A));
    setValue('val-em16-w', formatW(em16W));
    setValue('val-em16-va', formatVA(em16V, em16A));
    setPip('pip-em16', !demo && em16W !== null && Math.abs(em16W) > 0);

    setValue('val-t2-renogy-w', '-- W');
    setPip('pip-t2-renogy', false);
    setValue('val-ku-renogy-w', '-- W');

    var totalSoak = 0;
    var hasSoak = false;
    var anyPlugOn = false;
    var plugWs = {};
    for (var p = 1; p <= PLUG_COUNT; p++) {
      var plugOn = isSwitchOn(entities, p);
      var plugW = getPowerW(entities, 'sensor.sim_ac_plug_' + p + '_power');
      plugWs[p] = plugW;
      setValue('val-plug-' + p + '-w', formatW(plugW));
      setPip('pip-plug-' + p, !demo && (plugOn || (plugW !== null && plugW > 0)));
      setPlugOn(p, plugOn);
      setFlow('path-ac-plug-' + p, !demo && (plugOn || (plugW !== null && plugW > 0)), false);
      if (plugOn) anyPlugOn = true;
      if (plugW !== null) {
        totalSoak += plugW;
        hasSoak = true;
      }
    }

    var soakSensor = getPowerW(entities, ENTITY_IDS.soakTotal);
    setValue('val-soak-w', formatW(soakSensor !== null ? soakSensor : (hasSoak ? totalSoak : null)));

    var sgPvW = getPowerW(entities, ENTITY_IDS.sgPvW);
    var sgPvV = parseFloatSafe(getState(entities, ENTITY_IDS.sgPvV));
    var sgPvA = parseFloatSafe(getState(entities, ENTITY_IDS.sgPvA));
    setValue('val-sg-panels-w', formatW(sgPvW));
    setValue('val-sg-pv-w', formatW(sgPvW));
    setValue('val-sg-pv-va', formatVA(sgPvV, sgPvA));
    setPip('pip-sg-pv', !demo && sgPvW !== null && sgPvW > 0);

    var sgSoc = parseFloatSafe(getState(entities, ENTITY_IDS.sgSoc));
    var sgBattV = parseFloatSafe(getState(entities, ENTITY_IDS.sgBattV));
    var sgBattA = parseFloatSafe(getState(entities, ENTITY_IDS.sgBattA));
    var sgBattW = getPowerW(entities, ENTITY_IDS.sgBattW);
    var sgCharge = getState(entities, ENTITY_IDS.sgCharge);
    setValue('val-sg-soc', sgSoc !== null ? 'remain ' + formatNum(sgSoc, 0) + '%' : 'remain --');
    setValue('val-sg-batt-va', formatVA(sgBattV, sgBattA));
    setValue('val-sg-batt-w', formatSignedW(sgBattW));
    setValue('val-sg-charge', sgCharge || '--');
    setPip('pip-sg-batt', !demo && sgBattW !== null && Math.abs(sgBattW) > 0);

    var sgGridV = parseFloatSafe(getState(entities, ENTITY_IDS.sgGridV));
    var sgGridA = parseFloatSafe(getState(entities, ENTITY_IDS.sgGridA));
    var sgGridHz = parseFloatSafe(getState(entities, ENTITY_IDS.sgGridHz));
    var outletW = outletHopW(entities, em16W, sgGridV, sgGridA);
    setValue('val-sg-acin-w', formatW(outletW));
    setValue('val-sg-acin-va', formatVA(sgGridV, sgGridA));
    setValue('val-sg-acin-hz', sgGridHz !== null ? formatNum(sgGridHz, 0) + ' Hz' : '-- Hz');
    setPip('pip-sg-acin', !demo && outletW !== null && outletW > 0);

    var sgLoadW = getPowerW(entities, ENTITY_IDS.sgLoadW);
    var sgLoadA = parseFloatSafe(getState(entities, ENTITY_IDS.sgLoadA));
    var sgOutV = parseFloatSafe(getState(entities, ENTITY_IDS.sgOutV));
    var sgOutHz = parseFloatSafe(getState(entities, ENTITY_IDS.sgOutHz));
    setValue('val-sg-load-w', formatW(sgLoadW));
    setValue('val-sg-load-va', formatVA(sgOutV, sgLoadA));
    setValue('val-sg-load-hz', sgOutHz !== null ? formatNum(sgOutHz, 0) + ' Hz' : '-- Hz');
    setPip('pip-sg-acout', !demo && sgLoadW !== null && Math.abs(sgLoadW) > 0);

    var sgMode = getState(entities, ENTITY_IDS.sgMode);
    var sgFail = getState(entities, ENTITY_IDS.sgFail);
    var sgFault = getState(entities, ENTITY_IDS.sgFault);
    setValue('val-sg-mode', sgMode ? 'mode ' + sgMode : 'mode --');
    var faultOn = sgFault === 'on' || sgFault === 'true';
    setValue('val-sg-fault', faultOn ? 'fault on' : (sgFail && sgFail !== '0' ? 'fail ' + sgFail : 'fault off'));
    setPip('pip-sg-inv', !demo && ((sgBattW !== null && Math.abs(sgBattW) > 0) || (sgLoadW !== null && sgLoadW > 0) || faultOn));

    renderEm16Meters(entities);

    var ai = snapshot.ai || {};
    var thinking = ai.thinking;
    if (demo && thinking) thinking = 'DEMO snapshot: ' + thinking;
    setText('ai-thinking', thinking || (proxyOnline ? 'idle' : 'waiting for proxy'));
    renderMetrics(ai);
    renderDecisions(ai.decisions);

    var acBusW = hasSoak && totalSoak > 0 ? totalSoak : null;
    var mpptBattHopW = mpptToBattHopW(entities, solarW);
    updateHopLabels({
      solarW: solarW,
      mpptBattHopW: mpptBattHopW,
      batt2W: batt2W,
      em16W: em16W,
      acBusW: acBusW,
      plugWs: plugWs,
      outletW: outletW,
      sgPvW: sgPvW,
      sgBattW: sgBattW,
      sgLoadW: sgLoadW
    });
    updateFlows({
      solarW: solarW,
      batt1W: batt1W,
      batt2W: batt2W,
      em16W: em16W,
      plugTotal: totalSoak,
      anyPlugOn: anyPlugOn,
      sgPvW: sgPvW,
      sgBattW: sgBattW,
      sgGridA: sgGridA,
      sgGridV: sgGridV,
      outletW: outletW,
      sgLoadW: sgLoadW
    });
    setPip(
      'pip-inverter',
      !demo && (totalSoak > 0 || anyPlugOn || (batt2W !== null && batt2W < 0) || (outletW !== null && outletW > 0))
    );
  }

  function setFetchedAt(iso, mode) {
    var el = $('fetched-at');
    if (!el) return;
    if (mode === 'demo') {
      el.textContent = 'DEMO not HA';
      if (iso) el.setAttribute('datetime', iso);
      else el.removeAttribute('datetime');
      return;
    }
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
    if (isDemo()) {
      setFlow('path-t2-panels-mppt', false, false);
      setFlow('path-t2-mppt-batt1', false, false);
      setFlow('path-t2-batt1-renogy', false, false);
      setFlow('path-ku-panels-chargers', false, false);
      setFlow('path-ku-chargers-batt2', false, false);
      setFlow('path-ku-pwm-panels', false, false);
      setFlow('path-ku-pwm-batt2', false, false);
      setFlow('path-ku-batt2-inverter', false, false);
      setFlow('path-inverter-acbus', false, false);
      setFlow('path-ac-riser', false, false);
      setFlow('path-ac-em16', false, false);
      for (var dp = 1; dp <= PLUG_COUNT; dp++) {
        setFlow('path-ac-plug-' + dp, false, false);
      }
      setFlow('path-ku-outlet-sg-acin', false, false);
      setFlow('path-sg-pv-panels', false, false);
      setFlow('path-sg-pv-batt', false, false);
      setFlow('path-sg-batt-inv', false, false);
      setFlow('path-sg-acin-inv', false, false);
      setFlow('path-sg-inv-acout', false, false);
      return;
    }
    var solarFlow = opts.solarW !== null && opts.solarW > 0;
    var batt1Charge = opts.batt1W !== null && opts.batt1W > 0;
    var batt1Discharge = opts.batt1W !== null && opts.batt1W < 0;
    setFlow('path-t2-panels-mppt', solarFlow, false);
    setFlow('path-t2-mppt-batt1', solarFlow || batt1Charge || batt1Discharge, batt1Discharge);
    setFlow('path-t2-batt1-renogy', false, false);

    var batt2Discharge = opts.batt2W !== null && opts.batt2W < 0;
    var em16Flow = opts.em16W !== null && Math.abs(opts.em16W) > 0;
    var plugLoad = (opts.plugTotal || 0) > 0 || opts.anyPlugOn;
    var outletFlow = opts.outletW !== null && opts.outletW > 0;
    setFlow('path-ku-batt2-inverter', batt2Discharge || plugLoad || outletFlow, false);
    setFlow('path-inverter-acbus', plugLoad, false);
    setFlow('path-ac-riser', plugLoad, false);
    setFlow('path-ac-em16', em16Flow, false);
    setFlow('path-ku-outlet-sg-acin', outletFlow, false);
    setFlow('path-sg-pv-panels', opts.sgPvW !== null && opts.sgPvW > 0, false);
    setFlow('path-sg-pv-batt', opts.sgPvW !== null && opts.sgPvW > 0, false);
    setFlow('path-sg-batt-inv', opts.sgBattW !== null && Math.abs(opts.sgBattW) > 0, false);
    setFlow('path-sg-acin-inv', outletFlow, false);
    setFlow('path-sg-inv-acout', opts.sgLoadW !== null && opts.sgLoadW > 0, false);
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
    if (isDemo()) {
      if ($('history-status')) {
        $('history-status').textContent = 'history unavailable in demo mode';
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

  function fetchSnapshot() {
    return fetch('/api/snapshot', {
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
