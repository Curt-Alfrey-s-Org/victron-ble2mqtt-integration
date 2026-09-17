(function () {
  'use strict';

  var POLL_MS = 2000;
  var VIEW_STORAGE_KEY = 'solar-flow-view';
  var currentView = 'production';
  // Browser may request hours=24; proxy clamps to 10 (see solar_flow_server.py).
  var HISTORY_HOURS = 24;
  var HISTORY_TABLE_ROWS = 40;
  var lastSnapshot = null;
  var lastInboundMetrics = { t2TotalA: null, kuTotalA: null };
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

  function applyLoadSign(el, n) {
    if (!el) return;
    el.classList.remove('watt-pos', 'watt-neg', 'watt-zero');
    el.classList.add(wattLossClass(n));
  }

  function signOpts(arg) {
    if (arg && typeof arg === 'object') return arg;
    return { signed: !!arg };
  }

  function setWattValue(id, watts, signedOrOpts) {
    var el = $(id);
    if (!el) return;
    var opts = signOpts(signedOrOpts);
    el.textContent = formatW(watts);
    if (opts.load) applyLoadSign(el, watts);
    else applyWattSign(el, watts);
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

  function setHopLabel(pathId, watts, unmetered, signedOrOpts) {
    var el = $('hop-' + pathId);
    if (!el) return;
    var opts = signOpts(signedOrOpts);
    if (unmetered) {
      el.classList.add('unmetered');
    } else {
      el.classList.remove('unmetered');
    }
    el.textContent = formatW(watts);
    if (opts.load) applyLoadSign(el, watts);
    else applyWattSign(el, watts);
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

  var HOP_EPS_W = 0.5;

  // Sungold UTI lives in the cart lane (AC-in of SPH), not the KU A/C breaker row.
  // Matches solar_watt_ledger: vent = max(0, trailer_outlet_W - utiHopW).
  function ventFanEstimateW(trailerW, utiW) {
    if (trailerW === null || utiW === null) return null;
    var residual = trailerW - utiW;
    return residual > 0 ? residual : 0;
  }

  function b3MeteredW(entities) {
    var b3W = getPowerW(entities, ENTITY_IDS.b3W);
    if (b3W !== null && Math.abs(b3W) >= HOP_EPS_W) {
      return Math.abs(b3W);
    }
    return null;
  }

  function b3OutletHopW(entities, panelW) {
    var b3 = b3MeteredW(entities);
    if (b3 !== null) return b3;
    return panelW;
  }

  function a3DownstreamHopW(panelW) {
    if (panelW === null || panelW < HOP_EPS_W) return null;
    return panelW;
  }

  function utiPassthroughFromAcOut(sgGridV, sgGridA, sgLoadW) {
    var acIn = sungoldAcInW(null, sgGridV, sgGridA);
    var acOut = sgLoadW !== null ? Math.abs(sgLoadW) : null;
    if (acOut === null || acOut < HOP_EPS_W) return false;
    if (acIn === null || acIn < HOP_EPS_W) return true;
    return false;
  }

  // P = V*I (HA REST state); prefer SPH grid V x A, else AC-out lower bound in UTI mode.
  function utiHopW(sgGridV, sgGridA, sgLoadW) {
    var acIn = sungoldAcInW(null, sgGridV, sgGridA);
    var acOut = sgLoadW !== null ? Math.abs(sgLoadW) : null;
    if (acIn !== null && acIn >= HOP_EPS_W) return acIn;
    if (acOut !== null && acOut >= HOP_EPS_W) return acOut;
    if (acIn !== null && acIn > 0) return acIn;
    return null;
  }

  function isSgUtiMode(sgMode, sgGridV) {
    if (sgGridV !== null && sgGridV > 50) return true;
    if (sgMode === '2' || sgMode === 'Mains output') return true;
    return false;
  }

  function isSgCartBattTare(sgMode, sgGridV, sgBattA, sgBattW) {
    if (!isSgUtiMode(sgMode, sgGridV)) return false;
    if (sgBattA === null || Math.abs(sgBattA) >= 0.5) return false;
    if (sgBattW !== null && Math.abs(sgBattW) >= 5) return false;
    return sgBattA !== null && Math.abs(sgBattA) > 0.01;
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
  // KU_PV ≈ batt2_W − jumper_into_KU + KU_Renogy_load.
  // jumper_W is T2→KU positive (T2_solar − batt1_W). Do not use (batt2+load)/3.
  function kuUnmeteredPvEstW(batt2W, jumperW, kuRenogyAcW) {
    if (batt2W === null || jumperW === null || kuRenogyAcW === null) return null;
    return batt2W - jumperW + kuRenogyAcW;
  }

  function kuEqualShareW(combinedW) {
    if (combinedW === null) return null;
    return combinedW / 3;
  }

  function paintKuChargerEst(shareW, batt2V) {
    var wattIds = [
      'val-ku-panel-mppt1-w',
      'val-ku-panel-mppt2-w',
      'val-ku-panel-pwm-w',
      'val-ku-mppt-1-w',
      'val-ku-mppt-2-w',
      'val-ku-pwm-w',
      'val-ku-pwm-panels-w'
    ];
    var ampIds = ['val-ku-mppt-1-a', 'val-ku-mppt-2-a', 'val-ku-pwm-a'];
    var i;
    for (i = 0; i < wattIds.length; i++) {
      setWattValue(wattIds[i], shareW);
    }
    for (i = 0; i < ampIds.length; i++) {
      var aEl = $(ampIds[i]);
      if (!aEl) continue;
      if (shareW === null || batt2V === null || batt2V === 0) {
        aEl.textContent = '-- A';
      } else {
        aEl.textContent = formatNum(Math.abs(shareW / batt2V), 1) + ' A';
      }
    }
  }

  function jumperEstimateW(solarW, batt1W, t2RenogyW) {
    if (batt1W === null) return null;
    var solar = solarW === null ? 0 : solarW;
    var inv = t2RenogyW === null ? 0 : t2RenogyW;
    return solar - inv - batt1W;
  }

  // Inbound branch A from hop W and pack V (P = V*I; display magnitude only).
  function inboundAFromW(watts, packV) {
    if (watts === null || watts === undefined || watts <= 0.01) return null;
    if (packV === null || packV === undefined || Math.abs(packV) < 0.01) return null;
    return Math.abs(watts) / Math.abs(packV);
  }

  function computeBattery1Inbound(mpptBattW, jumperW, batt1V) {
    var sources = [];
    var total = 0;
    var mpptA = inboundAFromW(mpptBattW, batt1V);
    if (mpptA !== null) {
      sources.push({ label: 'MPPT', a: mpptA, est: false });
      total += mpptA;
    }
    if (jumperW !== null && jumperW < -0.5) {
      var jumperA = inboundAFromW(Math.abs(jumperW), batt1V);
      if (jumperA !== null) {
        sources.push({ label: 'Jumper', a: jumperA, est: true });
        total += jumperA;
      }
    }
    return { sources: sources, totalA: sources.length ? total : 0 };
  }

  function computeBattery2Inbound(kuShareW, jumperW, batt2V) {
    var sources = [];
    var total = 0;
    var shareA = inboundAFromW(kuShareW, batt2V);
    if (shareA !== null) {
      sources.push({ label: 'MPPT1', a: shareA, est: true });
      sources.push({ label: 'MPPT2', a: shareA, est: true });
      sources.push({ label: 'PWM', a: shareA, est: true });
      total += shareA * 3;
    }
    if (jumperW !== null && jumperW > 0.5) {
      var jumperA = inboundAFromW(jumperW, batt2V);
      if (jumperA !== null) {
        sources.push({ label: 'Jumper', a: jumperA, est: true });
        total += jumperA;
      }
    }
    return { sources: sources, totalA: sources.length ? total : 0 };
  }

  function formatInboundBranchA(source) {
    return source.label + ' ' + formatNum(source.a, 1) + ' A' + (source.est ? ' est.' : '');
  }

  function paintBatteryInbound(prefix, inbound) {
    var linesEl = $('val-' + prefix + '-inbound-lines');
    var totalEl = $('val-' + prefix + '-inbound-total');
    if (!linesEl || !totalEl) return;
    if (!inbound.sources.length) {
      linesEl.textContent = 'none';
      totalEl.textContent = 'Total in 0 A';
      applyWattSign(totalEl, 0);
      return;
    }
    var parts = [];
    for (var i = 0; i < inbound.sources.length; i++) {
      parts.push(formatInboundBranchA(inbound.sources[i]));
    }
    linesEl.textContent = parts.join(' · ');
    totalEl.textContent = 'Total in ' + formatNum(inbound.totalA, 1) + ' A';
    applyWattSign(totalEl, inbound.totalA);
  }

  function formatShuntNetVA(v, a) {
    return formatVA(v, a) + ' shunt net';
  }

  function updateHopLabels(opts) {
    setHopLabel('path-t2-panels-mppt', opts.solarW, false);
    setHopLabel('path-t2-mppt-batt1', opts.mpptBattHopW, false);
    setHopLabel('path-t2-batt1-renogy', null, true, { load: true });
    setHopLabel('path-t2-ku-jumper', opts.jumperW, false);
    setHopLabel('path-ku-mppt1-panels', opts.kuShareW, true);
    setHopLabel('path-ku-mppt1-batt2', opts.kuShareW, true);
    setHopLabel('path-ku-mppt2-panels', opts.kuShareW, true);
    setHopLabel('path-ku-mppt2-batt2', opts.kuShareW, true);
    setHopLabel('path-ku-pwm-panels', opts.kuShareW, true);
    setHopLabel('path-ku-pwm-batt2', opts.kuShareW, true);
    setHopLabel('path-ku-batt2-inverter', opts.kuRenogyAcW, false, { load: true });
    setHopLabel('path-ku-renogy-panel', opts.a3DownstreamW, false, { load: true });
    setHopLabel('path-panel-b3', opts.a3DownstreamW, false, { load: true });
    setHopLabel('path-b3-outlet', opts.outletHopW, false, { load: true });
    setHopLabel('path-outlet-uti', opts.utiW, false, { load: true });
    setHopLabel('path-sg-uti-sph', opts.utiW, false, { load: true });
    setHopLabel('path-outlet-vent-fan', opts.ventW, opts.ventW === null, { load: true });
    setHopLabel('path-sg-acout-pi4', null, true, { load: true });
    var simW = opts.simBusW;
    var simUnmetered = simW === null;
    setHopLabel('path-sim-acbus', simW, simUnmetered, { load: true });
    setHopLabel('path-sim-riser', simW, simUnmetered, { load: true });
    for (var p = 1; p <= PLUG_COUNT; p++) {
      setHopLabel('path-sim-plug-' + p, opts.plugWs[p], false, { load: true });
    }
    setHopLabel('path-sg-pv-panels', opts.sgPvW, false);
    setHopLabel('path-sg-pv-batt', opts.sgPvW, false);
    setHopLabel('path-sg-batt-inv', opts.sgBattTare ? null : opts.sgBattW, false);
    setHopLabel('path-sg-inv-acout', opts.sgLoadW, false, { load: true });
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
    return formatW(w);
  }

  function formatVA(v, a) {
    return (v !== null ? formatNum(Math.abs(v), 1) + ' V' : '-- V') + ' / ' +
      (a !== null ? formatNum(Math.abs(a), 1) + ' A' : '-- A');
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

  function renderMetricItem(f, ai) {
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
      display = formatNum(Math.abs(val), 1) + ' A';
    } else if (f.suffix) {
      display = formatNum(val, 1) + f.suffix;
    } else if (f.signed) {
      display = formatW(val);
    } else {
      display = formatW(val);
    }
    var signClass = '';
    if (val !== null && val !== undefined) {
      if (f.loss || f.load) {
        signClass = ' ' + wattLossClass(val);
      } else if (f.signed || f.signedA || !f.suffix) {
        signClass = ' ' + wattSignClass(val);
      }
    }
    var extraClass = (f.dim ? ' unsynced' : '') + (f.total ? ' metric-total' : '') +
      (f.nested ? ' metric-nested' : '');
    return '<div class="metric-item' + extraClass +
      '"><span class="metric-label">' + f.label +
      '</span><span class="metric-value' + signClass + '">' +
      escapeHtml(display) + '</span></div>';
  }

  function renderMetricFields(fields, ai) {
    var html = '';
    for (var i = 0; i < fields.length; i++) {
      html += renderMetricItem(fields[i], ai);
    }
    return html;
  }

  function renderMetrics(ai) {
    var container = $('ai-metrics');
    if (!container) return;
    if (!ai) {
      container.innerHTML = '';
      return;
    }
    ai = Object.assign({}, ai, {
      t2_inbound_total_a: lastInboundMetrics.t2TotalA,
      ku_inbound_total_a: lastInboundMetrics.kuTotalA
    });
    var unsynced = !!ai.soc_unsynced;
    var html = '';

    html += '<section class="metrics-section" aria-label="Surplus">';
    html += '<div class="metrics-grid">';
    html += renderMetricFields([
      { label: 'Surplus', key: 'surplus_w', signed: true },
      { label: 'After path losses', key: 'surplus_after_path_losses_w', signed: true }
    ], ai);
    html += '</div></section>';

    html += '<section class="metrics-section" aria-label="Losses">';
    html += '<h4 class="metrics-heading">Losses</h4>';
    html += '<div class="metrics-grid">';
    html += renderMetricFields([
      { label: 'Conversion losses', key: 'combined_losses_w', loss: true },
      { label: 'Vdrop loss', key: 'combined_vdrop_loss_w', loss: true }
    ], ai);
    html += '<div class="metric-subgroup" aria-label="Vdrop voltage readings">';
    html += renderMetricFields([
      { label: 'Vdrop D/C', key: 'combined_vdrop_v', suffix: ' V', zeroOk: true, nested: true },
      { label: 'Vdrop A/C', key: 'combined_vdrop_ac_v', suffix: ' V', zeroOk: true, nested: true }
    ], ai);
    html += '</div>';
    html += renderMetricItem(
      { label: 'Total path losses', key: 'combined_path_losses_w', loss: true, total: true },
      ai
    );
    html += '</div></section>';

    html += '<section class="metrics-section" aria-label="Loads">';
    html += '<h4 class="metrics-heading">Loads</h4>';
    html += '<div class="metrics-grid">';
    html += renderMetricFields([
      { label: 'Vent fan', key: 'vent_fan_w', load: true },
      { label: 'KU Renogy A/C', key: 'ku_renogy_ac_est_w', load: true },
      { label: 'Load', key: 'load_w', load: true },
      { label: 'Sim dump loads', key: 'sim_plug_w', load: true },
      { label: 'Eff. load', key: 'effective_load_w', load: true }
    ], ai);
    html += '</div></section>';

    html += '<section class="metrics-section" aria-label="Energy">';
    html += '<h4 class="metrics-heading">Energy</h4>';
    html += '<div class="metrics-grid">';
    html += renderMetricFields([
      { label: 'Panel in', key: 'panel_in_w' },
      { label: 'Solar', key: 'solar_w' },
      { label: 'KU PV est', key: 'ku_unmetered_pv_est_w', signed: true },
      { label: 'KU charger est', key: 'ku_charger_equal_share_w', signed: true },
      { label: 'T2 in from sources', key: 't2_inbound_total_a', signedA: true, zeroOk: true },
      { label: 'KU in from sources', key: 'ku_inbound_total_a', signedA: true, zeroOk: true },
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
    ], ai);
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
    html += '</div></section>';

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
        : formatW(hop.stored_w);
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
        '<div class="meter-w ' + wattSignClass(w) + '">' + escapeHtml(formatW(w)) + '</div>' +
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
    applyLoadSign($('val-mppt-load'), mpptLoadW);
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
    setValue('val-batt1-va', formatShuntNetVA(batt1V, batt1A));
    applyWattSign($('val-batt1-va'), batt1A);
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
    setValue('val-batt2-va', formatShuntNetVA(batt2V, batt2A));
    applyWattSign($('val-batt2-va'), batt2A);
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
    setWattValue('val-panel-a3-w', panelA3W, { load: true });
    setValue('val-panel-a3-va', 'A3 ' + formatVA(panelA3V, panelA3A));
    setPip('pip-panel', panelW !== null && panelW > 0);

    var b3RawW = getPowerW(entities, ENTITY_IDS.b3W);
    var b3V = parseFloatSafe(getState(entities, ENTITY_IDS.b3V));
    var b3A = parseFloatSafe(getState(entities, ENTITY_IDS.b3A));
    var b3MeterW = b3MeteredW(entities);
    var outletHopW = b3OutletHopW(entities, panelW);
    var a3DownstreamW = a3DownstreamHopW(panelW);
    setWattValue('val-b3-w', b3RawW !== null ? b3RawW : 0, { load: true });
    setValue('val-b3-va', formatVA(b3V, b3A));
    setPip('pip-b3', b3MeterW !== null && b3MeterW > 0);

    setWattValue('val-t2-renogy-w', 0);
    setPip('pip-t2-renogy', false);

    var totalDump = 0;
    var hasDump = false;
    var anyPlugOn = false;
    var plugWs = {};
    for (var p = 1; p <= PLUG_COUNT; p++) {
      var plugOn = isSwitchOn(entities, p);
      var plugW = getPowerW(entities, 'sensor.sim_ac_plug_' + p + '_power');
      plugWs[p] = plugW;
      setWattValue('val-plug-' + p + '-w', plugW, { load: true });
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
    setWattValue('val-dump-w', dumpSensor !== null ? dumpSensor : (hasDump ? totalDump : null), { load: true });

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
    var sgModeEarly = getState(entities, ENTITY_IDS.sgMode);
    var sgGridVEarly = parseFloatSafe(getState(entities, ENTITY_IDS.sgGridV));
    var sgBattTare = isSgCartBattTare(sgModeEarly, sgGridVEarly, sgBattA, sgBattW);
    setSignedCurrent('val-sg-batt-va', sgBattV, sgBattA);
    if (sgBattTare) {
      setWattValue('val-sg-batt-w', sgBattW !== null ? sgBattW : 0, true);
      setValue('val-sg-charge', 'standby (UTI tare)');
      setPip('pip-sg-batt', false);
    } else {
      setWattValue('val-sg-batt-w', sgBattW, true);
      setValue('val-sg-charge', sgCharge || '--');
      setPip('pip-sg-batt', sgBattW !== null && Math.abs(sgBattW) > 0);
    }

    var sgGridV = sgGridVEarly;
    var sgGridA = parseFloatSafe(getState(entities, ENTITY_IDS.sgGridA));
    var sgGridHz = parseFloatSafe(getState(entities, ENTITY_IDS.sgGridHz));
    var sgLoadW = getPowerW(entities, ENTITY_IDS.sgLoadW);
    var trailerW = trailerOutletW(entities);
    var utiW = utiHopW(sgGridV, sgGridA, sgLoadW);
    var ventW = ventFanEstimateW(trailerW, utiW);
    var kuRenogyAcW = trailerW;
    setWattValue('val-ku-renogy-w', kuRenogyAcW, { load: true });
    setValue(
      'val-ku-renogy-note',
      kuRenogyAcW !== null ? 'est. from A3 A/C' : 'no HA inverter'
    );
    if (kuRenogyAcW === null) {
      setValue('val-batt2-load', 'load 0 W');
      applyLoadSign($('val-batt2-load'), 0);
    } else {
      setValue('val-batt2-load', 'load ' + formatW(kuRenogyAcW));
      applyLoadSign($('val-batt2-load'), kuRenogyAcW);
    }
    setWattValue('val-sg-uti-w', utiW, { load: true });
    setValue('val-sg-uti-va', formatVA(sgGridV, sgGridA));
    setValue('val-sg-uti-hz', sgGridHz !== null ? formatNum(sgGridHz, 0) + ' Hz' : '-- Hz');
    setPip('pip-sg-uti', utiW !== null && utiW > 0);
    if (ventW === null) {
      setValue('val-vent-fan-w', 'unmetered');
      applyWattSign($('val-vent-fan-w'), 0);
    } else {
      setWattValue('val-vent-fan-w', ventW, { load: true });
    }
    setPip('pip-vent-fan', ventW !== null && ventW > 0.5);
    setFanSpeedClass(ventW !== null && ventW > 0.5, resolveVentFanSpeed(snapshot));
    paintWeatherSky(snapshot);
    setValue('val-pi4-w', 'unmetered');
    applyWattSign($('val-pi4-w'), 0);
    setPip('pip-pi4', true);

    var sgLoadA = parseFloatSafe(getState(entities, ENTITY_IDS.sgLoadA));
    var sgOutV = parseFloatSafe(getState(entities, ENTITY_IDS.sgOutV));
    var sgOutHz = parseFloatSafe(getState(entities, ENTITY_IDS.sgOutHz));
    setWattValue('val-sg-load-w', sgLoadW, { load: true });
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
    renderWattHops(ai);
    renderDecisions(ai.decisions);

    var simBusW = hasDump && totalDump > 0 ? totalDump : null;
    var mpptBattHopW = mpptToBattHopW(entities, solarW);
    var jumperW = jumperEstimateW(solarW, batt1W, 0);
    var kuPvEstW = kuUnmeteredPvEstW(batt2W, jumperW, kuRenogyAcW);
    var kuShareW = kuEqualShareW(kuPvEstW);
    paintKuChargerEst(kuShareW, batt2V);
    setWattValue('val-ku-victron-panels-w', kuPvEstW);
    var b1Inbound = computeBattery1Inbound(mpptBattHopW, jumperW, batt1V);
    var b2Inbound = computeBattery2Inbound(kuShareW, jumperW, batt2V);
    paintBatteryInbound('batt1', b1Inbound);
    paintBatteryInbound('batt2', b2Inbound);
    lastInboundMetrics = {
      t2TotalA: b1Inbound.totalA,
      kuTotalA: b2Inbound.totalA
    };
    renderMetrics(ai);
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
      kuRenogyAcW: kuRenogyAcW,
      kuShareW: kuShareW,
      panelW: panelW,
      a3DownstreamW: a3DownstreamW,
      outletHopW: outletHopW,
      b3MeterW: b3MeterW,
      utiW: utiW,
      ventW: ventW,
      simBusW: simBusW,
      plugWs: plugWs,
      sgPvW: sgPvW,
      sgBattW: sgBattW,
      sgBattTare: sgBattTare,
      sgLoadW: sgLoadW
    });
    updateFlows({
      solarW: solarW,
      batt1W: batt1W,
      batt2W: batt2W,
      jumperW: jumperW,
      panelW: panelW,
      kuRenogyAcW: kuRenogyAcW,
      a3DownstreamW: a3DownstreamW,
      outletHopW: outletHopW,
      utiW: utiW,
      ventW: ventW,
      plugTotal: totalDump,
      anyPlugOn: anyPlugOn,
      sgPvW: sgPvW,
      sgBattW: sgBattW,
      sgBattTare: sgBattTare,
      sgLoadW: sgLoadW
    });
    setPip(
      'pip-inverter',
      kuRenogyAcW !== null && kuRenogyAcW > 0.5
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

    var downstreamFlow = opts.a3DownstreamW !== null && opts.a3DownstreamW > 0;
    var outletFlow = opts.outletHopW !== null && opts.outletHopW > 0;
    var utiFlow = opts.utiW !== null && opts.utiW > 0;
    var kuRenogyFlow = opts.kuRenogyAcW !== null && opts.kuRenogyAcW > 0.5;
    var plugLoad = (opts.plugTotal || 0) > 0 || opts.anyPlugOn;
    setFlow('path-ku-batt2-inverter', kuRenogyFlow, false);
    setFlow('path-ku-renogy-panel', downstreamFlow || kuRenogyFlow, false);
    setFlow('path-panel-b3', downstreamFlow, false);
    setFlow('path-b3-outlet', outletFlow, false);
    setFlow('path-outlet-uti', utiFlow, false);
    setFlow('path-sg-uti-sph', utiFlow, false);
    setFlow('path-outlet-vent-fan', opts.ventW !== null && opts.ventW > 0.5, false);
    setFlow('path-sg-acout-pi4', true, false);
    setFlow('path-sim-acbus', plugLoad, false);
    setFlow('path-sim-riser', plugLoad, false);
    setFlow('path-sg-pv-panels', opts.sgPvW !== null && opts.sgPvW > 0, false);
    setFlow('path-sg-pv-batt', opts.sgPvW !== null && opts.sgPvW > 0, false);
    setFlow(
      'path-sg-batt-inv',
      !opts.sgBattTare && opts.sgBattW !== null && Math.abs(opts.sgBattW) > 0,
      false
    );
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

  /* Weather + vent fan visual hooks (CSS classes only; no watt math). */
  function mapWeatherClass(condition) {
    if (!condition) return 'wx-clear';
    var c = String(condition).toLowerCase().replace(/[\s_]+/g, '');
    if (/lightning|thunder|exceptional|storm/.test(c)) return 'wx-storm';
    if (/rain|pour|drizzle|shower|snow|hail|sleet|wintry|snowyrainy/.test(c)) return 'wx-rain';
    if (c === 'cloudy' || c === 'fog' || c === 'windy' || c === 'windyvariant' || /overcast/.test(c)) {
      return 'wx-cloudy';
    }
    if (c === 'partlycloudy' || /partly|mostlycloud|scattered/.test(c)) return 'wx-partly';
    if (c === 'sunny' || c === 'clearnight' || c === 'clear' || /fair/.test(c)) return 'wx-clear';
    return 'wx-partly';
  }

  function setWeatherClass(condition, label, temp) {
    var sky = $('node-weather-sky');
    if (!sky) return;
    sky.className = 'weather-sky ' + mapWeatherClass(condition);
    var lbl = $('val-weather-condition');
    if (lbl) lbl.textContent = label || condition || '--';
    var tempEl = $('val-weather-temp');
    if (tempEl) tempEl.textContent = temp != null && temp !== '' ? String(temp) : '';
    setPip('pip-weather-sky', condition != null && condition !== '' && condition !== '--');
  }

  function resolveWeatherFromSnapshot(snapshot) {
    var block = snapshot.weather || snapshot.ecobee_weather || null;
    if (block) {
      return {
        condition: block.condition || block.state,
        label: block.label || block.condition || block.state,
        temp: block.temperature != null
          ? formatNum(block.temperature, 0) + (block.temperature_unit ? ' ' + block.temperature_unit : '')
          : null
      };
    }
    var entities = snapshot.entities || {};
    var keys = Object.keys(entities);
    var i;
    for (i = 0; i < keys.length; i++) {
      if (keys[i].indexOf('weather.') === 0) {
        var ent = entities[keys[i]];
        var attrs = ent.attributes || {};
        return {
          condition: attrs.condition || ent.state,
          label: attrs.condition || ent.state,
          temp: attrs.temperature != null
            ? formatNum(attrs.temperature, 0) + (attrs.temperature_unit ? ' ' + attrs.temperature_unit : '')
            : null
        };
      }
    }
    for (i = 0; i < keys.length; i++) {
      if (keys[i].indexOf('climate.') === 0) {
        var clim = entities[keys[i]];
        var cattrs = clim.attributes || {};
        return {
          condition: cattrs.condition || clim.state,
          label: cattrs.condition || clim.state,
          temp: cattrs.current_temperature != null
            ? formatNum(cattrs.current_temperature, 0) + (cattrs.temperature_unit ? ' ' + cattrs.temperature_unit : '')
            : null
        };
      }
    }
    return null;
  }

  function paintWeatherSky(snapshot) {
    var info = resolveWeatherFromSnapshot(snapshot);
    if (info) {
      setWeatherClass(info.condition, info.label, info.temp);
    } else {
      setWeatherClass(null, '--', null);
    }
  }

  function fanSpeedFromPercentage(pct) {
    if (pct == null || isNaN(pct)) return null;
    if (pct <= 25) return 1;
    if (pct <= 50) return 2;
    if (pct <= 75) return 3;
    return 4;
  }

  function resolveVentFanSpeed(snapshot) {
    var meta = snapshot.meta || {};
    if (meta.vent_fan_speed != null) return meta.vent_fan_speed;
    if (snapshot.vent_fan_speed != null) return snapshot.vent_fan_speed;
    var entities = snapshot.entities || {};
    var keys = Object.keys(entities);
    var i;
    for (i = 0; i < keys.length; i++) {
      if (keys[i].indexOf('fan.') !== 0) continue;
      var ent = entities[keys[i]];
      var attrs = ent.attributes || {};
      if (attrs.percentage != null) return fanSpeedFromPercentage(parseFloatSafe(attrs.percentage));
      if (ent.state && /^\d+$/.test(ent.state)) {
        var level = parseInt(ent.state, 10);
        if (level >= 1 && level <= 4) return level;
      }
    }
    return null;
  }

  function setFanSpeedClass(running, speed) {
    var node = $('node-vent-fan');
    if (!node) return;
    node.classList.remove('vent-running', 'fan-speed-1', 'fan-speed-2', 'fan-speed-3', 'fan-speed-4');
    if (!running || reducedMotion) return;
    var s = parseInt(speed, 10);
    if (isNaN(s) || s < 1) s = 1;
    if (s > 4) s = 4;
    node.classList.add('vent-running', 'fan-speed-' + s);
  }
})();
