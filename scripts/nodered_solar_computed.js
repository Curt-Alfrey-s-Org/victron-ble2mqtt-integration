/**
 * Solar computed meters + 8 panel boxes for Node-RED (HA device-only).
 * Mirrors victron scripts/solar_watt_ledger.py helpers.
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

const H5082_SOCKETS = [
    ["2F9D", "left"],
    ["2F9D", "right"],
    ["3013", "left"],
    ["3013", "right"],
    ["3EC9", "left"],
    ["3EC9", "right"],
    ["82FB", "left"],
    ["82FB", "right"],
    ["9607", "left"],
    ["9607", "right"],
    ["C061", "left"],
    ["C061", "right"],
    ["C38D", "left"],
    ["C38D", "right"],
    ["CF79", "left"],
    ["CF79", "right"],
];

function h5082Id(plug, side) {
    return plug.toLowerCase() + "_" + side;
}

function textState(states, id) {
    const s = states[id];
    if (s === undefined || s === null || s === "unavailable" || s === "unknown") return "";
    return String(s).replace(/\s+/g, " ").trim();
}

/** On/off plus the operator's Where, Load, and Use text. Not a watt calculation. */
function socketSamples(states) {
    return H5082_SOCKETS.map(function (pair) {
        const plug = pair[0];
        const side = pair[1];
        const id = h5082Id(plug, side);
        const sw = states["switch.ihoment_h5082_" + id];
        const on = sw === "on" ? 1 : sw === "off" ? 0 : null;
        const use = textState(states, "input_select.h5082_" + id + "_use") === "dump" ? "dump" : "normal";
        return {
            plug: plug,
            side: side,
            location: textState(states, "input_text.h5082_" + plug.toLowerCase() + "_location"),
            load: textState(states, "input_text.h5082_" + id + "_load"),
            use: use,
            on: on,
        };
    });
}

function round1(x) {
    if (x === null || x === undefined || !Number.isFinite(x)) return null;
    return Math.round(x * 10) / 10;
}

function halfString(w) {
    return w === null ? null : round1(w / 2);
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

function em16B3Live(states) {
    const v = num(states, "sensor.em16_b3_voltage");
    const p = num(states, "sensor.em16_b3_power");
    if (v === null || p === null || v < 80) return null;
    return Math.abs(p);
}

function kuRenogyAcProxy(states) {
    const sgP = num(states, "sensor.sungold_sph302480a_charging_power");
    if (sgP !== null && sgP >= 15) return 0;
    const b3 = em16B3Live(states);
    if (b3 !== null && b3 >= 0.5) return b3;
    const a3 = em16A3Live(states);
    if (a3 !== null) return Math.abs(a3);
    return null;
}

/** 8 physical panels: 4x 2s strings -> MPPT1 T2, MPPT2 KU, MPPT3 KU, PWM KU */
function panelBoxes(mppt, mppt23, pwmEst) {
    const kuMpptEach = mppt23 === null ? null : mppt23 / 2;
    return [
        {
            id: 1,
            label: "P1",
            string: "T2 series A",
            connects: "Panel 1+2 -> Victron MPPT #1 (T2) -> HQ2239CQYT2 24V",
            est_w: halfString(mppt),
        },
        {
            id: 2,
            label: "P2",
            string: "T2 series B",
            connects: "Panel 1+2 -> Victron MPPT #1 (T2) -> HQ2239CQYT2 24V",
            est_w: halfString(mppt),
        },
        {
            id: 3,
            label: "P3",
            string: "KU MPPT2 A",
            connects: "Panel 3+4 -> Victron MPPT #2 (KU) -> HQ2239JTRKU 24V",
            est_w: halfString(kuMpptEach),
        },
        {
            id: 4,
            label: "P4",
            string: "KU MPPT2 B",
            connects: "Panel 3+4 -> Victron MPPT #2 (KU) -> HQ2239JTRKU 24V",
            est_w: halfString(kuMpptEach),
        },
        {
            id: 5,
            label: "P5",
            string: "KU MPPT3 A",
            connects: "Panel 5+6 -> Victron MPPT #3 (KU) -> HQ2239JTRKU 24V",
            est_w: halfString(kuMpptEach),
        },
        {
            id: 6,
            label: "P6",
            string: "KU MPPT3 B",
            connects: "Panel 5+6 -> Victron MPPT #3 (KU) -> HQ2239JTRKU 24V",
            est_w: halfString(kuMpptEach),
        },
        {
            id: 7,
            label: "P7",
            string: "KU PWM A",
            connects: "Panel 7+8 -> Renogy PWM 12/24 -> HQ2239JTRKU 24V",
            est_w: halfString(pwmEst),
        },
        {
            id: 8,
            label: "P8",
            string: "KU PWM B",
            connects: "Panel 7+8 -> Renogy PWM 12/24 -> HQ2239JTRKU 24V",
            est_w: halfString(pwmEst),
        },
    ];
}

function computeSolarDerived(statesArr) {
    const states = stateMap(statesArr);
    const mppt = num(states, "sensor.solar_controller_solar");
    const mpptCharge = num(states, "sensor.solar_controller_charging_power");
    const b1 = num(states, "sensor.battery_1_power");
    const b2 = num(states, "sensor.battery_2_power");
    const sgPv = num(states, "sensor.sungold_sph302480a_pv_power");
    const sgLoad = num(states, "sensor.sungold_sph302480a_load_power");
    const sgBatt = num(states, "sensor.sungold_sph302480a_charging_power");
    const sgGridV = num(states, "sensor.sungold_sph302480a_grid_voltage");
    const sgGridA = num(states, "sensor.sungold_sph302480a_grid_current");
    const sgAcIn =
        sgGridV !== null && sgGridA !== null ? round1(Math.abs(sgGridV * sgGridA)) : null;

    const jumper = mppt !== null && b1 !== null ? round1(mppt - b1) : null;
    const mppt23 = mppt !== null ? round1(2 * mppt) : null;
    const kuAc = kuRenogyAcProxy(states);
    let kuCombined = null;
    if (b2 !== null && jumper !== null && kuAc !== null) {
        kuCombined = round1(b2 - jumper + kuAc);
    } else if (mppt23 !== null) {
        kuCombined = mppt23;
    }
    const pwmEst =
        kuCombined !== null && mppt23 !== null ? round1(Math.max(0, kuCombined - mppt23)) : null;
    const kuShare = kuCombined !== null ? round1(kuCombined / 3) : null;

    const siteSolar =
        mppt !== null && kuCombined !== null ? round1(mppt + kuCombined) : null;
    const batt1Charge = b1 !== null && b1 > 0 ? round1(b1) : 0;
    const siteSource = round1(batt1Charge + (sgAcIn || 0) + (sgPv || 0));
    const siteLoad = sgLoad !== null ? round1(sgLoad) : null;
    const loadUnaccounted =
        siteSolar !== null && siteLoad !== null ? round1(siteSolar - siteLoad) : null;
    const sungoldCartToLoad =
        sgLoad !== null && kuAc !== null ? round1(Math.max(0, sgLoad - kuAc)) : null;

    const panels = panelBoxes(mppt, mppt23, pwmEst);

    return {
        t2_mppt_w: mppt,
        t2_mppt_charge_w: mpptCharge,
        t2_ku_jumper_w: jumper,
        ku_victron_mppt23_est_w: mppt23,
        ku_pwm_mppt_combined_est_w: kuCombined,
        ku_pwm_est_w: pwmEst,
        ku_charger_equal_share_w: kuShare,
        em16_a3_live_w: em16A3Live(states),
        em16_b3_live_w: em16B3Live(states),
        trailer_outlet_w: kuAc,
        sungold_pv_w: sgPv,
        sungold_ac_in_w: sgAcIn,
        sungold_batt_in_w: sgBatt,
        sungold_ac_out_w: sgLoad,
        sungold_cart_to_load_w: sungoldCartToLoad,
        site_solar_w: siteSolar,
        site_source_w: siteSource,
        site_total_load_w: siteLoad,
        load_unaccounted_w: loadUnaccounted,
        battery_1_w: b1,
        battery_2_w: b2,
        panels,
        sockets: socketSamples(states),
    };
}

module.exports = {
    stateMap,
    num,
    round1,
    panelBoxes,
    socketSamples,
    computeSolarDerived,
};
