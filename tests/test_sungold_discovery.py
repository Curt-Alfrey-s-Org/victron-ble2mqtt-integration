"""Unit tests for Sungold read-only MQTT discovery (no hardware)."""

from __future__ import annotations

import json

from sungold_modbus_ro.config import Settings
from sungold_modbus_ro.mqtt_ha import MqttHaPublisher
from sungold_modbus_ro.registers import (
    CHARGING_STATES,
    CURATED_ENTITIES,
    FAIL_CODES,
    MACHINE_STATES,
    RETIRED_DISCOVERY,
    decode_failcode,
    decode_fault_binary,
)


def _settings() -> Settings:
    return Settings(
        modbus_device="/dev/null",
        modbus_address=1,
        modbus_baudrate=9600,
        modbus_timeout=0.25,
        modbus_skip_threshold=5,
        modbus_skip_retry_interval=3600,
        mqtt_host="127.0.0.1",
        mqtt_port=1883,
        mqtt_user="test",
        mqtt_password="test",
        mqtt_topic="sungold_sph302480a",
        device_name="Sungold SPH302480A",
        poll_interval_sec=5,
        heartbeat_file="/tmp/sungold_test.heartbeat",
        skip_state_file="/tmp/sungold_test_skip.json",
    )


def test_curated_entities_are_read_only_sensors():
    allowed = {"sensor", "binary_sensor"}
    keys = [e.key for e in CURATED_ENTITIES]
    assert len(keys) == len(set(keys)), "duplicate entity keys"
    for entity in CURATED_ENTITIES:
        assert entity.topic_type in allowed
        assert entity.register > 0


def test_discovery_payload_has_unique_id_not_object_id():
    pub = MqttHaPublisher(_settings())
    entity = next(e for e in CURATED_ENTITIES if e.key == "battery/soc")
    payload = pub.build_discovery_payload(entity)
    wire = json.loads(json.dumps(payload))
    assert "unique_id" in wire
    assert wire["unique_id"] == "sungold_sph302480a-battery-soc"
    assert "object_id" not in wire
    assert wire["state_topic"] == "sungold_sph302480a/sensor/battery/soc/state"
    assert wire["device"]["model"] == "SPH302480A"
    assert wire["device"]["manufacturer"] == "SunGoldPower"
    assert wire["name"] == "Remaining battery"


def test_sph302480a_lcd_names():
    by_key = {e.key: e.name for e in CURATED_ENTITIES}
    expected = {
        "pv1/voltage": "PV input voltage",
        "pv1/current": "PV output current",
        "pv1/power": "PV output power",
        "battery/soc": "Remaining battery",
        "battery/voltage": "Battery input voltage",
        "battery/current": "Input battery current",
        "battery/temperature": "Battery temperature",
        "battery/charge_state": "Charge state",
        "inverter/charging_power": "Battery input power",
        "inverter/state": "Output mode",
        "inverter/error_flags": "Inverter error flags",
        "inverter/failcode": "Fault code",
        "grid/voltage": "AC input voltage",
        "grid/current": "AC input current",
        "grid/frequency": "AC input frequency",
        "inverter/voltage": "Output load voltage",
        "inverter/frequency": "AC output frequency",
        "load/current": "AC output load current",
        "load/power": "Load active power",
        "temperature/dc_dc": "PV charger heatsink temperature",
        "temperature/dc_ac": "Inverter heat sink temperature",
        "inverter/fault_active": "Fault state",
    }
    assert by_key == expected
    retired_keys = {key for _, key in RETIRED_DISCOVERY}
    assert retired_keys == {"pv/total_power", "grid/power", "temperature/transformer"}
    assert retired_keys.isdisjoint(by_key)


def test_charge_and_output_mode_wording():
    assert CHARGING_STATES[0] == "Not charging"
    assert CHARGING_STATES[1] == "Boost charge"
    assert CHARGING_STATES[2] == "Constant-voltage charge"
    assert CHARGING_STATES[4] == "Floating charge"
    assert CHARGING_STATES[8] == "Charging completed"
    assert MACHINE_STATES[2] == "Mains output"
    assert MACHINE_STATES[3] == "Inverter output"
    assert 4 not in MACHINE_STATES


def test_failcode_decoding():
    assert decode_failcode(0) == "No reported error"
    assert decode_failcode(1) == "Battery undervoltage alarm"
    assert decode_failcode(10) == "Buck overcurrent software protection"
    assert decode_failcode(12) == "Mains power down"
    assert decode_failcode(20) == "Inverter heat sink over temperature protection"
    assert decode_failcode(21) == "Fan failure"
    assert decode_failcode(26) == "Inverted AC output backfills to bypass AC input"
    assert decode_failcode(58) == "BMS communication error"
    assert decode_failcode(99) == "Unknown fault (99)"
    assert decode_fault_binary(0) == "OFF"
    assert decode_fault_binary(14) == "ON"
    for code in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 19, 20, 21, 22, 23, 26, 29, 30, 31, 32, 34, 58, 59, 60, 61, 62, 63, 64):
        assert code in FAIL_CODES


def test_retire_discovery_topic():
    pub = MqttHaPublisher(_settings())
    entity = next(e for e in CURATED_ENTITIES if e.key == "battery/soc")
    assert pub.discovery_topic(entity) == (
        "homeassistant/sensor/sungold_sph302480a-battery-soc/config"
    )
