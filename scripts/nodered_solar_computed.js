/**
 * Solar computed meters (KU est, jumper, etc.) for Node-RED function nodes.
 * Port of victron scripts/solar_watt_ledger.py helpers -- HA remains device-only.
 */

function stateMap(statesArr) {
    const m = {};
    if (!Array.isArray(statesArr)) return m;
    for (const row of statesArr) {
        if (row && row.entity_id) m[row.entity_id] = row.state;
    }
    return m;
}

function num(states, id) {
    const s = states[id];
    if (s === undefined || s === null || s === "unavailable" || s === "unknown") return null;
    const n = parseFloat(s);
    return Number.isFinite(n) ? n : null;
}

function em16A3Live(states) {
    const v = num(states, "sensor.em16_a3_voltage");
    const p = num(states, "sensor.em16_a3_power");
    const sgv = num(states, "sensor.sungold_sph302480a_grid_voltage");
    const sga = num(states, "sensor.sungold_sph302480a_grid_current");
    if (v === null || p === null || v < 80) return null;
    if (sgv !== null && sga !== null && sgv < 50 && sga < 0.5 && Math.abs(p) > 5) return null;
    return p;
}

function kuRenogyAcProxy(states) {
    const sgP = num(states, "sensor.sungold_sph302480a_charging_power");
    if (sgP !== null && sgP >= 15) return 0;
    const b3 = num(states, "sensor.em16_b3_power");
    if (b3 !== null && Math.abs(b3) >= 0.5) return Math.abs(b3);
    const a3 = em16A3Live(states);
    if (a3 !== null) return Math.abs(a3);
    return null;
}

function computeSolarDerived(statesArr) {
    const states = stateMap(statesArr);
    const mppt = num(states, "sensor.solar_controller_solar");
    const b1 = num(states, "sensor.battery_1_power");
    const b2 = num(states, "sensor.battery_2_power");
    const jumper = mppt !== null && b1 !== null ? mppt - b1 : null;
    const mppt23 = mppt !== null ? 2 * mppt : null;
    const kuAc = kuRenogyAcProxy(states);
    let kuCombined = null;
    if (b2 !== null && jumper !== null && kuAc !== null) {
        kuCombined = Math.round((b2 - jumper + kuAc) * 10) / 10;
    } else if (mppt23 !== null) {
        kuCombined = Math.round(mppt23 * 10) / 10;
    }
    const pwmEst =
        kuCombined !== null && mppt23 !== null
            ? Math.max(0, Math.round((kuCombined - mppt23) * 10) / 10)
            : null;
    const kuShare = kuCombined !== null ? Math.round((kuCombined / 3) * 10) / 10 : null;
    return {
        t2_mppt_w: mppt,
        t2_ku_jumper_w: jumper,
        ku_victron_mppt23_est_w: mppt23,
        ku_pwm_mppt_combined_est_w: kuCombined,
        ku_pwm_est_w: pwmEst,
        ku_charger_equal_share_w: kuShare,
        em16_a3_live_w: em16A3Live(states),
    };
}

module.exports = {
    stateMap,
    num,
    computeSolarDerived,
};
