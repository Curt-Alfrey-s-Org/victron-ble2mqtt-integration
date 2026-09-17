# Away from home with Tailscale

Use this when Home Assistant already works **on your home Wi‑Fi** and you want the same numbers on a phone or laptop **off the LAN** — without opening Home Assistant to the public internet.

This repo’s installer does **not** install Tailscale. You add it on **`.105`** and on each device you travel with. You do **not** put Tailscale keys, machine names, or IPs in git.

## What you get

```
Phone / laptop (Tailscale on)
        │
        │  private VPN
        ▼
HA host (.105, Tailscale on)  →  Home Assistant :8123
                              →  Solar flow diagram (Tailscale Serve → :8765)
```

Home Assistant Container lives on **`.105`**, not the Pi. Pi4/Pi5 only collect
and publish MQTT. With Tailscale connected, open HA using **`.105`’s** Tailscale
name or Tailscale IP, port **8123**. The Pi’s Tailscale address is the wrong
host after the move. Same sensors as at home (Victron, optional Sungold, house BLE).

Do **not** port-forward `:8123` or `:8765` on your router. Tailscale is the path in.
Do **not** use Tailscale Funnel for these dashboards (Funnel is public internet).

## 1. Install Tailscale on the HA host

On **`.105`** (the machine that runs Home Assistant). The Pis do not need
Tailscale for the dashboard:

Follow [Tailscale’s Linux install](https://tailscale.com/download/linux) for Ubuntu, then:

```bash
sudo tailscale up
```

A login URL is printed. Open it on any device, sign in to **your** Tailscale account, and approve **`.105`**. Pick a machine name you will recognize (anything you like). That name is yours — do not commit it to this repo.

Check it is up:

```bash
sudo tailscale status
```

You should see **`.105`** listed as online. The console also shows a Tailscale IP (`100.x.x.x`) and, if MagicDNS is on, a name like `your-machine.tailnet-name.ts.net`.

## 2. Install Tailscale on the phone or laptop

Install the Tailscale app from [tailscale.com/download](https://tailscale.com/download) (or the App Store / Play Store). Sign in to the **same** Tailscale account. Turn the VPN **on** before you open Home Assistant.

## 3. Open Home Assistant while away

With Tailscale **connected** on the travel device:

```text
http://YOUR-TAILSCALE-NAME:8123
```

or

```text
http://100.x.x.x:8123
```

Use the name or `100.x` address from `sudo tailscale status` on **`.105`** (not the Pi) or from the Tailscale admin console. Replace the placeholders — do not copy anyone else’s. Live operator URLs: alfa-ai `docs/HOMEASSISTANT_105_OPERATOR.md`.

In the **Home Assistant Companion app**, add that URL as the server (or as the external URL). You still need your Home Assistant login. The phone must have Tailscale on; this is not a public website.

**Same data as the PC browser:** Companion and the desktop browser talk to the **same** Home Assistant. Open sidebar **Solar**, then the **Sungold** view (path `/sungold`) for the cart tiles without scrolling past every EM16 channel. If Sungold tiles are missing or say Entity not found, re-run `scripts/ha_label_sungold_solar.py` on `.105` with HA stopped ([SUNGOLD_SPH302480A.md](SUNGOLD_SPH302480A.md)).

**MagicDNS:** In the Tailscale admin console, enable MagicDNS if you want the name form instead of remembering the `100.x` address.

## 4. Animated solar-flow diagram on Tailscale

The GX-style diagram (`scripts/solar_flow_server.py`, port **8765**) defaults to localhost only. To open it on a phone the same way as HA:

On **`.105` / `web-sites`** (after Tailscale is up). Prefer linking an **existing**
site token so the diagram starts **LIVE** — do not invent a new HA UI token if one
already lives in `host105-ai.env` / alfa-ai secrets:

```bash
cd /path/to/victron-ble2mqtt-integration
sudo bash scripts/solar_flow_enable_tailscale.sh
# (calls scripts/solar_flow_link_ha_token.sh first; search order in SOLAR_FLOW_DASHBOARD.md)
```

Token-only (no Tailscale Serve change):

```bash
sudo bash scripts/solar_flow_link_ha_token.sh
sudo systemctl restart solar-flow.service
```

If auto-link finds nothing, only then paste a new long-lived token into
`/opt/homeassistant/secrets/ha_long_lived.token` (`chmod 600`).

That script:

1. Installs `systemd/solar-flow.service` (listens on `127.0.0.1:8765`)
2. Checks `GET /api/snapshot` — prints **LIVE** or **DEMO** (DEMO ≈ fake Battery 1 29.0 V)
3. Runs [`tailscale serve --bg 8765`](https://tailscale.com/docs/reference/tailscale-cli/serve) (HTTPS proxy for your tailnet only)
4. **Prints the exact Tailscale address** — typically:

```text
https://YOUR-105-NAME.YOUR-TAILNET.ts.net/
```

plus the direct forms `http://YOUR-105-NAME:8765/` and `http://100.x.x.x:8765/`.

Open the **Primary (Tailscale Serve HTTPS)** line on the phone with Tailscale connected. The page header also shows the discovered URL via `GET /api/access`.

Optional — put that URL on the HA Solar dashboard (HA container **stopped**):

```bash
sudo SOLAR_FLOW_PUBLIC_URL='https://YOUR-105-NAME.YOUR-TAILNET.ts.net/' \
  python3 scripts/ha_label_sungold_solar.py
```

Full diagram docs: [SOLAR_FLOW_DASHBOARD.md](SOLAR_FLOW_DASHBOARD.md).

## 5. Home Wi‑Fi vs away

| Where you are | How to open HA | How to open solar flow |
|---------------|----------------|------------------------|
| Home LAN | `http://YOUR-LAN-IP:8123` (`.105`) | `http://127.0.0.1:8765/` on the host, or LAN IP if started with `--lan` |
| Away, Tailscale on | `http://YOUR-TAILSCALE-NAME:8123` | Serve HTTPS URL from `solar_flow_enable_tailscale.sh`, or `http://100.x:8765/` |

Both talk to the **same** Home Assistant / same MQTT plant. You are not duplicating the stack.

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Page does not load away from home | Tailscale app **on** on the phone? `.105` still `tailscale status` online? Using `.105`’s address, not the Pi’s? |
| Works on Wi‑Fi, not on cellular | Phone is using LAN IP. Switch to the Tailscale name / `100.x` URL. |
| Login loop / old server in the app | Remove the server in the HA app and add the Tailscale URL again. |
| “Can’t connect” with Tailscale off | Expected. Turn Tailscale on, or wait until you are on home Wi‑Fi. |
| Sungold missing on phone, present on PC | Same HA URL? Open **Solar → Sungold**. Re-label with `ha_label_sungold_solar.py` if tiles are Entity not found. |
| Solar flow 404 / connection refused on Tailscale | Run `sudo bash scripts/solar_flow_enable_tailscale.sh`; confirm `systemctl status solar-flow` and `tailscale serve status`. |
| Diagram shows DEMO / Battery 1 stuck at ~29.0 V | Token missing at `/opt/homeassistant/secrets/ha_long_lived.token`. Run `sudo bash scripts/solar_flow_link_ha_token.sh` (copies from `host105-ai.env` / alfa-ai / known `*.token`), then `sudo systemctl restart solar-flow`. Confirm `curl …/api/snapshot` prints `live` and a real voltage. |

## Out of scope

- Putting Tailscale auth keys in `.env` or this git repo
- Exposing `:8123` or `:8765` on the public internet (including Tailscale Funnel)
- Replacing Home Assistant’s own user login — Tailscale only provides the network path
