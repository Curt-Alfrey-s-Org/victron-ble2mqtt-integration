retry() { while :; do "$@"; echo "mosquitto_sub ended; retry in 5s" >&2; sleep 5; done; }
#!/usr/bin/env sh
set -eu

HOST="${MQTT_HOST:-192.168.0.1}"
PORT="${MQTT_PORT:-1883}"
USER="${MQTT_USER:-victron}"
PASS="${MQTT_PASSWORD:-changeme}"
TOPIC_ROOT="${TOPIC_ROOT:-victron}"
DEVICE_NAME_PREFIX="${DEVICE_NAME_PREFIX:-Victron}"

# allowlist (case-insensitive)
ALLOW_RE="(^|/)(soc|state_of_charge|battery_pct|percent|temperature|temp|voltage|volt|current|amp|power|watt|energy|yield|kwh|frequency|hz|capacity|ah|a_h)($|/)"
touch /tmp/seen_keys

mosquitto_sub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -v -t "$TOPIC_ROOT/#" | \
while IFS= read -r line; do
  topic="${line%% *}"; payload="${line#* }"
  rel="${topic#$TOPIC_ROOT/}"
  dev="${rel%%/*}"
  rest="${rel#${dev}/}"
  [ -n "$dev" ] && [ "$rest" != "$rel" ] || continue

  # optional device limit: comma-separated names in LIMIT_DEVICES
  if [ -n "${LIMIT_DEVICES:-}" ]; then
    case ",$LIMIT_DEVICES," in *,"$dev",*) : ;; *) continue ;; esac
  fi

  printf "%s\n" "$rest" | grep -Eqi "$ALLOW_RE" || continue

  sdev="$(printf "%s" "$dev"  | tr -cd "[:alnum:]_-")"
  smetric="$(printf "%s" "$rest" | tr -cd "[:alnum:]_-/")"
  slug="$(printf "%s" "${sdev}_${smetric}" | tr "/ " "__")"
  key="${sdev}:${smetric}"
  grep -qxF "$key" /tmp/seen_keys && continue

  unit=""; dclass=""; sclass="measurement"
  case "$smetric" in
    *soc*|*state_of_charge*|*battery_pct*|*percent*) unit="%"; dclass="battery" ;;
    *temp*|*temperature*)                            unit="°C"; dclass="temperature" ;;
    *voltage*|*volt*|*/V|*pv*_v|*bat*_v)             unit="V"; dclass="voltage" ;;
    *current*|*amp*|*/A|*pv*_i|*bat*_i)              unit="A"; dclass="current" ;;
    *power*|*watt*|*/W|*pv*_p|*bat*_p)               unit="W"; dclass="power" ;;
    *energy*|*yield*|*kwh*)                          unit="kWh"; dclass="energy"; sclass="total_increasing" ;;
    *frequency*|*hz)                                 unit="Hz"; dclass="frequency" ;;
    *capacity*|*ah|*a_h)                             unit="Ah" ;;
  esac

  name_metric="$(printf "%s" "$rest" | tr "/_" "  " | sed -E "s/ +/ /g")"
  name="${DEVICE_NAME_PREFIX} ${dev} ${name_metric}"
  uniq="vic_${sdev}_${smetric}_$(hostname)"

  cfg="/tmp/ha_${slug}.json"
  {
    echo "{"
    echo "  \"name\": \"${name}\","
    echo "  \"unique_id\": \"${uniq}\","
    echo "  \"state_topic\": \"${topic}\","
    if [ -n "$dclass" ]; then echo "  \"device_class\": \"${dclass}\","; fi
    if [ -n "$unit" ]; then echo "  \"unit_of_measurement\": \"${unit}\","; fi
    echo "  \"state_class\": \"${sclass}\","
    echo "  \"device\": {"
    echo "    \"identifiers\": [\"victron_${sdev}\"],"
    echo "    \"name\": \"${DEVICE_NAME_PREFIX} ${dev}\","
    echo "    \"manufacturer\": \"Victron\","
    echo "    \"model\": \"BLE->MQTT\""
    echo "  }"
    echo "}"
  } > "$cfg"

  mosquitto_pub -h "$HOST" -p "$PORT" -u "$USER" -P "$PASS" -r \
    -t "homeassistant/sensor/${slug}/config" -f "$cfg"

  echo "$key" >> /tmp/seen_keys
done
