module.exports = {
    flowFile: "flows.json",
    flowFilePretty: true,
    adminRoot: "/",
    adminAuth: (function () {
        var user = process.env.NR_ADMIN_USER;
        var hash = process.env.NR_ADMIN_PASSWORD_HASH;
        if (!user || !hash) {
            return undefined;
        }
        return {
            type: "credentials",
            users: [{
                username: user,
                password: hash,
                permissions: "*"
            }]
        };
    })(),
    functionGlobalContext: {
        solarComputed: (function () {
            try {
                return require("/data/nodered_solar_computed.js");
            } catch (e) {
                return {};
            }
        })(),
        haToken: process.env.HA_LONG_LIVED_TOKEN || "",
        haBaseUrl: process.env.HA_BASE_URL || "http://127.0.0.1:8123"
    },
    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false
        }
    }
};
