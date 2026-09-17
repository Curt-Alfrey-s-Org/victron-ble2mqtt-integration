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
```

Home Assistant Container lives on **`.105`**, not the Pi. Pi4/Pi5 only collect
and publish MQTT. With Tailscale connected, open HA using **`.105`’s** Tailscale
name or Tailscale IP, port **8123**. The Pi’s Tailscale address is the wrong
host after the move. Same sensors as at home (Victron, optional Sungold, house BLE).

Do **not** port-forward `:8123` on your router. Tailscale is the path in.

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

**MagicDNS:** In the Tailscale admin console, enable MagicDNS if you want the name form instead of remembering the `100.x` address.

## 4. Home Wi-Fi vs away

| Where you are | How to open HA | How to open solar flow |
|---------------|----------------|------------------------|
| Home LAN | `http://YOUR-LAN-IP:8123` (`.105`, e.g. `hostname -I` on that VM) | `http://YOUR-LAN-IP:8765` |
| Away, Tailscale on | `http://YOUR-TAILSCALE-NAME:8123` or the Tailscale `100.x` address of **`.105`** | `http://YOUR-TAILSCALE-NAME:8765` (same name, port **8765**) |

Both HA URLs talk to the **same** Home Assistant. Both solar-flow URLs talk to the **same**
`solar-flow.service` on `.105` ([SOLAR_FLOW_DASHBOARD.md](SOLAR_FLOW_DASHBOARD.md)). You are
not duplicating either stack. `127.0.0.1` is not a Tailscale address.

Optional: [Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve) may proxy
HTTPS `/` on `.105` to `http://127.0.0.1:8765`. That is the same solar-flow process. Do not
enable Funnel. Do not commit the Serve FQDN.

## Troubleshooting

| Symptom | What to check |
|---------|----------------|
| Page does not load away from home | Tailscale app **on** on the phone? `.105` still `tailscale status` online? Using `.105`’s address, not the Pi’s? |
| Works on Wi‑Fi, not on cellular | Phone is using LAN IP. Switch to the Tailscale name / `100.x` URL. |
| Login loop / old server in the app | Remove the server in the HA app and add the Tailscale URL again. |
| “Can’t connect” with Tailscale off | Expected. Turn Tailscale on, or wait until you are on home Wi‑Fi. |

## Out of scope

- Putting Tailscale auth keys in `.env` or this git repo
- Exposing `:8123` or `:5006` on the public internet
- Replacing Home Assistant’s own user login — Tailscale only provides the network path
