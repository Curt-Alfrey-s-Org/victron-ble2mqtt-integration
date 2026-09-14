"""Unit tests for Sungold read-only MQTT discovery (no hardware)."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import paho.mqtt.client as mqtt

from sungold_modbus_ro import __main__ as sungold_main
from sungold_modbus_ro import modbus_io, mqtt_ha
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
    assert retired_keys == {
        "pv/total_power",
        "grid/power",
        "temperature/transformer",
        "pv/voltage",
        "pv/current",
        "pv/power",
    }
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


def test_poll_loop_does_not_hide_discovery():
    source = Path(__file__).resolve().parents[1] / "sungold" / "sungold_modbus_ro"
    main_src = (source / "__main__.py").read_text(encoding="utf-8")
    mqtt_src = (source / "mqtt_ha.py").read_text(encoding="utf-8")
    assert "hide_entity" not in main_src
    assert "hide_entity" not in mqtt_src
    assert not hasattr(mqtt_ha.MqttHaPublisher, "hide_entity")
    assert "is_register_available" in sungold_main.run_poll_cycle.__code__.co_names


def test_publish_state_returns_false_when_not_connected():
    pub = MqttHaPublisher(_settings())
    pub._client.is_connected = MagicMock(return_value=False)
    pub._client.publish = MagicMock()
    entity = next(e for e in CURATED_ENTITIES if e.key == "battery/soc")
    assert pub.publish_state(entity, "50") is False
    pub._client.publish.assert_not_called()


def test_publish_state_returns_false_when_publish_not_queued():
    pub = MqttHaPublisher(_settings())
    pub._client.is_connected = MagicMock(return_value=True)
    pub._client.publish = MagicMock(
        return_value=SimpleNamespace(rc=mqtt.MQTT_ERR_NO_CONN, wait_for_publish=MagicMock(), is_published=MagicMock(return_value=False))
    )
    entity = next(e for e in CURATED_ENTITIES if e.key == "battery/soc")
    assert pub.publish_state(entity, "50") is False


def test_publish_state_returns_true_when_published():
    pub = MqttHaPublisher(_settings())
    pub._client.is_connected = MagicMock(return_value=True)
    info = SimpleNamespace(
        rc=mqtt.MQTT_ERR_SUCCESS,
        wait_for_publish=MagicMock(),
        is_published=MagicMock(return_value=True),
    )
    pub._client.publish = MagicMock(return_value=info)
    entity = next(e for e in CURATED_ENTITIES if e.key == "battery/soc")
    assert pub.publish_state(entity, "50") is True
    info.wait_for_publish.assert_called_once()


def test_heartbeat_not_touched_when_mqtt_publish_fails(tmp_path):
    heartbeat = tmp_path / "heartbeat"

    modbus = MagicMock()
    modbus.is_register_available.return_value = True
    modbus.read_entity.return_value = "50"

    mqtt_pub = MagicMock()
    mqtt_pub.publish_state.return_value = False

    assert sungold_main.run_poll_cycle(modbus, mqtt_pub) is False
    assert not heartbeat.exists()
    assert mqtt_pub.publish_state.call_count == len(CURATED_ENTITIES)


def test_heartbeat_touched_after_successful_poll_cycle(tmp_path):
    heartbeat = tmp_path / "heartbeat"
    settings = replace(_settings(), heartbeat_file=str(heartbeat))

    modbus = MagicMock()
    modbus.is_register_available.return_value = True
    modbus.read_entity.return_value = "50"

    mqtt_pub = MagicMock()
    mqtt_pub.publish_state.return_value = True

    assert sungold_main.run_poll_cycle(modbus, mqtt_pub) is True
    sungold_main.touch_heartbeat(settings.heartbeat_file)
    assert heartbeat.exists()


def test_timeout_does_not_skip_register(monkeypatch, tmp_path):
    class FakeSerial:
        baudrate = 9600
        timeout = 1.0

        def close(self) -> None:
            return None

    class FakeInstr:
        serial = FakeSerial()

        def read_register(self, *args, **kwargs):
            raise OSError("No communication with the instrument (no answer)")

    monkeypatch.setattr(
        modbus_io.minimalmodbus, "Instrument", lambda *args, **kwargs: FakeInstr()
    )
    settings = replace(_settings(), skip_state_file=str(tmp_path / "skip.json"))
    client = modbus_io.ReadOnlyModbusClient(settings)
    entity = next(e for e in CURATED_ENTITIES if e.key == "battery/soc")
    for _ in range(10):
        assert client.read_entity(entity) is None
    assert entity.register not in client._register_skip_time
