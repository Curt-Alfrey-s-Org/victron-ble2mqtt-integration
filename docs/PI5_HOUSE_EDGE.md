# Pi 5 house edge — DNS + BLE into `.105` Home Assistant

Mosquitto and Home Assistant run on **`.105` (`192.168.0.105`)**. The **Pi 4**
(`HOST_ROLE=pi4`) is the Victron BLE / Sungold USB radio in another building.
The **Pi 5** (`HOST_ROLE=pi5`) is the house radio and LAN DNS box. It does not
run a second Home Assistant.

```
House BLE  ──► Theengs on Pi 5 ──► Mosquitto on .105 :1883 ──► HA Container
Solar-site BLE (Govee, …) ──► Theengs on Pi 4 ──► same broker
LAN DNS    ──► AdGuard on Pi 5 (:53 / :8080)
Victron    ──► victron_ble2mqtt on Pi 4 ──► same broker
Optional house VE.Direct USB ──► bms_supervisor on Pi 5 ──► same broker (ENABLE_BMS_SUPERVISOR=1)
```

**Autoheal on Pi5:** `scripts/deploy_pi5.sh` starts repo-root `docker-compose.autoheal.yml` when `ENABLE_AUTOHEAL=1` (default). AdGuard has an HTTP [healthcheck](https://docs.docker.com/reference/compose-file/services/#healthcheck) and `autoheal: "true"`. Official `theengs/gateway` has **no** image HEALTHCHECK ([gateway-docker Dockerfile](https://github.com/theengs/gateway-docker/blob/main/Dockerfile)); do not invent a Docker probe for Pi5 Theengs. MQTT LWT stays broker availability ([Theengs use](https://gateway.theengs.io/use/use.html)). A retained LWT `online` can linger after an MQTT [keep-alive timeout](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html) while logs show `Failed to send message` / `Disconnected from MQTT broker`. Recreate **only** `theengs-gateway` with [`docker compose up --force-recreate`](https://docs.docker.com/reference/cli/docker/compose/up/) (no `--remove-orphans`). `restart: unless-stopped` covers process **exit** only ([restart policy](https://docs.docker.com/engine/containers/start-containers-automatically/)). Do not pass `--remove-orphans` (would drop AdGuard/Theengs from a single-file compose project).

Pi4 also runs **Theengs** (`hosts/pi4/docker-compose.theengs.yml`) so BLE next to
the Victron gear can be heard there. **This site (2026-09-14):** the H5075 at
`A4:C1:38:CA:AF:6F` has dead cells — HA tiles stay Unknown until the cells are
replaced ([MQTT sensor](https://www.home-assistant.io/integrations/sensor.mqtt/)).
Do **not** run `scripts/deploy.sh` on Pi4 to add Theengs — that installer still starts HA
and Mosquitto. Load `theengs/gateway:v1.7.5.1` from the hub tarball
`theengs-gateway-v1.7.5.1.tar.gz`, write `hosts/pi4/mqtt.env` with
`scripts/write_theengs_mqtt_env.py`, then:

```bash
cd ~/victron-ble2mqtt-integration/hosts/pi4
sudo docker compose -f docker-compose.theengs.yml up -d
```

Installer: `sudo bash scripts/deploy.sh` on each Pi (role from `.env` or LAN IP).
Compose files: [hosts/pi5/](../hosts/pi5/). Operator notes: [hosts/pi5/README.md](../hosts/pi5/README.md).

Prometheus scrape config for `:9100` / `:9617` stays in the **monitoring** repo
on `192.168.0.107`.
