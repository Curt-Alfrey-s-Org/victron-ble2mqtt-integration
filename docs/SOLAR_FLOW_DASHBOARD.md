# Solar flow dashboard -- retired

**Retired 17 Sep 2026.** The custom GX-style SVG proxy (`solar-flow.service`,
`:8765`, `web/solar-flow/`, `scripts/solar_flow_server.py`) is removed.

**Canonical operator view:** Home Assistant Lovelace **Solar plant**
([SOLAR_HA_DASHBOARD.md](SOLAR_HA_DASHBOARD.md)) at
`http://192.168.0.105:8123/solar-plant`.

Dump ON/OFF stays in alfa-ai `solar_dump.py` (HA REST, not this page).
Site physics: [SOLAR_POWER_BALANCE.md](SOLAR_POWER_BALANCE.md).

On `.105`, after `git pull`:

```bash
bash scripts/uninstall_solar_flow.sh
```

That stops and disables the unit ([systemctl](https://www.freedesktop.org/software/systemd/man/systemctl.html)
`disable --now`), removes `/etc/systemd/system/solar-flow.service`,
`daemon-reload`, turns off a Tailscale Serve proxy to `:8765` if present
([`tailscale serve ... off`](https://tailscale.com/kb/1242/tailscale-serve/#disable-tailscale-serve)),
and deletes the ufw 8765 rules
([ufw(8)](https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html)).
Do **not** run `tailscale serve reset` unless you intend to clear **all** Serve
handlers on that host.
