"""Unit tests for BMS supervisor VE.Direct Text parser and MQTT discovery."""

from __future__ import annotations

import inspect
import json

from types import SimpleNamespace
from unittest.mock import MagicMock

import paho.mqtt.client as mqtt
from bms_supervisor.config import Settings, VALID_ADAPTERS, load_settings
from bms_supervisor.entities import CURATED_ENTITIES
from bms_supervisor.mqtt_ha import MqttHaPublisher
from bms_supervisor.vedirect_text import (
    VeDirectTextParser,
    checksum_valid,
    fields_to_metrics,
    parse_fields,
)

# FAQ Q8 sample block (VE.Direct protocol FAQ).
# https://www.victronenergy.com/live/vedirect_protocol:faq
FAQ_SAMPLE_BLOCK = bytes.fromhex(
    "0d0a5049440930783230330d0a560932363230310d0a4909300d0a5009300d0a"
    "434509300d0a534f4309313030300d0a545447092d310d0a416c61726d094f4646"
    "0d0a52656c6179094f46460d0a415209300d0a424d56093730300d0a465709"
    "303330370d0a436865636b73756d09d8"
)


def _settings(adapter: str = "generic_shunt") -> Settings:
    return Settings(
        serial_device="/dev/null",
        adapter=adapter,
        bank_id="bench",
        mqtt_host="127.0.0.1",
        mqtt_port=1883,
        mqtt_user="test",
        mqtt_password="test",
        mqtt_topic="bms_supervisor",
        device_name="Test BMS",
        heartbeat_file="/tmp/bms_supervisor_test.heartbeat",
        manufacturer="Victron Energy",
        model="SmartShunt (generic)",
    )


def test_faq_checksum_block_valid():
    assert checksum_valid(FAQ_SAMPLE_BLOCK)
    assert sum(FAQ_SAMPLE_BLOCK) % 256 == 0


def test_faq_block_parses_conversions():
    fields = parse_fields(FAQ_SAMPLE_BLOCK)
    assert fields["PID"] == "0x203"
    assert fields["V"] == "26201"
    assert fields["I"] == "0"
    assert fields["SOC"] == "1000"
    assert fields["ALARM"] == "OFF"

    metrics = fields_to_metrics(fields)
    assert metrics.voltage_v == 26.201
    assert metrics.current_a == 0.0
    assert metrics.soc_pct == 100.0
    assert metrics.consumed_ah == 0.0
    assert metrics.alarm == "OFF"


def test_invalid_checksum_discarded():
    bad = bytearray(FAQ_SAMPLE_BLOCK)
    bad[-1] = (bad[-1] + 1) % 256
    assert not checksum_valid(bytes(bad))

    parser = VeDirectTextParser()
    results = list(parser.feed(bytes(bad)))
    assert results == []


def test_hex_frames_ignored():
    hex_line = b":D83A01...\r\n"
    parser = VeDirectTextParser()
    results = list(parser.feed(hex_line + FAQ_SAMPLE_BLOCK))
    assert len(results) == 1
    assert results[0]["V"] == "26201"


def test_no_serial_write_in_codebase():
    """Ensure no code path transmits HEX (:) frames to serial."""
    import bms_supervisor.__main__ as main_mod

    source = inspect.getsource(main_mod)
    assert "serial.write" not in source
    assert ".write(" not in source


def test_curated_entities_read_only():
    allowed = {"sensor", "binary_sensor"}
    keys = [e.key for e in CURATED_ENTITIES]
    assert len(keys) == len(set(keys))
    for entity in CURATED_ENTITIES:
        assert entity.topic_type in allowed


def test_discovery_unique_id_not_object_id():
    pub = MqttHaPublisher(_settings())
    entity = next(e for e in CURATED_ENTITIES if e.key == "voltage")
    payload = pub.build_discovery_payload(entity)
    wire = json.loads(json.dumps(payload))
    assert "unique_id" in wire
    assert wire["unique_id"] == "bms_supervisor-generic_shunt-bench-voltage"
    assert "object_id" not in wire
    assert wire["state_topic"] == "bms_supervisor/generic_shunt/voltage/state"
    assert wire["device"]["identifiers"] == ["bms_supervisor", "generic_shunt", "bench"]


def test_alarm_is_binary_sensor_discovery():
    pub = MqttHaPublisher(_settings())
    entity = next(e for e in CURATED_ENTITIES if e.key == "alarm")
    topic = pub.discovery_topic(entity)
    assert topic.startswith("homeassistant/binary_sensor/")
    payload = pub.build_discovery_payload(entity)
    assert payload["payload_on"] == "ON"
    assert payload["payload_off"] == "OFF"


def test_unknown_adapter_rejected(monkeypatch):
    monkeypatch.setenv("MQTT_USER", "u")
    monkeypatch.setenv("MQTT_PASSWORD", "p")
    monkeypatch.setenv("BMS_ADAPTER", "invalid_adapter")
    try:
        load_settings()
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_valid_adapters():
    assert "aes_lynk_observe" in VALID_ADAPTERS
    assert "aes_observe" not in VALID_ADAPTERS


def _block_with_checksum(pairs: list[tuple[str, str]]) -> bytes:
    """Build a VE.Direct Text block with a valid modulo-256 checksum."""
    body = b"".join(f"\r\n{k}\t{v}".encode("ascii") for k, v in pairs)
    prefix = body + b"\r\nChecksum\t"
    checksum_byte = (256 - (sum(prefix) % 256)) % 256
    return prefix + bytes([checksum_byte])


def test_temperature_placeholder_omitted_voltage_preserved():
    """Protocol 3.34 fn 8: T sends --- when no temp sensor; other fields still convert."""
    fields = {"V": "26201", "T": "---", "I": "0"}
    metrics = fields_to_metrics(fields)
    assert metrics.voltage_v == 26.201
    assert metrics.current_a == 0.0
    assert metrics.temperature_c is None

    block = _block_with_checksum([("PID", "0x203"), ("V", "26201"), ("T", "---"), ("I", "0")])
    assert checksum_valid(block)
    parser = VeDirectTextParser()
    results = list(parser.feed(block))
    assert len(results) == 1
    metrics2 = fields_to_metrics(results[0])
    assert metrics2.voltage_v == 26.201
    assert metrics2.temperature_c is None


def test_unsynced_soc_ce_placeholders_omitted():
    """Protocol 3.34 fn 10/11: unsynced BMV sends --- for SOC and CE."""
    fields = {"V": "26201", "SOC": "---", "CE": "---", "I": "-500", "ALARM": "OFF"}
    metrics = fields_to_metrics(fields)
    assert metrics.voltage_v == 26.201
    assert metrics.current_a == -0.5
    assert metrics.soc_pct is None
    assert metrics.consumed_ah is None
    assert metrics.alarm == "OFF"


def test_empty_field_values_treated_as_missing():
    fields = {"V": "26201", "SOC": "", "P": "   "}
    metrics = fields_to_metrics(fields)
    assert metrics.voltage_v == 26.201
    assert metrics.soc_pct is None
    assert metrics.power_w is None


def test_publish_state_returns_false_when_not_connected():
    pub = MqttHaPublisher(_settings())
    pub._client.is_connected = MagicMock(return_value=False)
    pub._client.publish = MagicMock()
    entity = next(e for e in CURATED_ENTITIES if e.key == "voltage")
    assert pub.publish_state(entity, "26.5") is False
    pub._client.publish.assert_not_called()


def test_publish_state_returns_false_when_publish_not_queued():
    pub = MqttHaPublisher(_settings())
    pub._client.is_connected = MagicMock(return_value=True)
    pub._client.publish = MagicMock(
        return_value=SimpleNamespace(
            rc=mqtt.MQTT_ERR_NO_CONN,
            wait_for_publish=MagicMock(),
            is_published=MagicMock(return_value=False),
        )
    )
    entity = next(e for e in CURATED_ENTITIES if e.key == "voltage")
    assert pub.publish_state(entity, "26.5") is False


def test_publish_state_returns_true_when_published():
    pub = MqttHaPublisher(_settings())
    pub._client.is_connected = MagicMock(return_value=True)
    info = SimpleNamespace(
        rc=mqtt.MQTT_ERR_SUCCESS,
        wait_for_publish=MagicMock(),
        is_published=MagicMock(return_value=True),
    )
    pub._client.publish = MagicMock(return_value=info)
    entity = next(e for e in CURATED_ENTITIES if e.key == "voltage")
    assert pub.publish_state(entity, "26.5") is True
    info.wait_for_publish.assert_called_once()


def test_publish_metrics_false_when_mqtt_fails():
    pub = MqttHaPublisher(_settings())
    pub.publish_state = MagicMock(return_value=False)
    metrics = fields_to_metrics({"V": "26201", "I": "0"})
    assert pub.publish_metrics(metrics) is False
    assert pub.publish_state.call_count >= 1


def test_publish_metrics_true_when_mqtt_succeeds():
    pub = MqttHaPublisher(_settings())
    pub.publish_state = MagicMock(return_value=True)
    metrics = fields_to_metrics({"V": "26201", "I": "0"})
    assert pub.publish_metrics(metrics) is True


def test_bms_compose_healthcheck_uses_exec_cmd():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "docker-compose.bms-supervisor.yml").read_text(
        encoding="utf-8"
    )
    assert "- CMD" in src
    assert "CMD-SHELL" not in src
    assert "autoheal: \"true\"" in src


def test_pi5_adguard_has_autoheal_label():
    from pathlib import Path

    src = (
        Path(__file__).resolve().parents[1] / "hosts/pi5/docker-compose.adguard.yml"
    ).read_text(encoding="utf-8")
    assert 'autoheal: "true"' in src


def test_deploy_pi5_starts_autoheal():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "scripts/deploy_pi5.sh").read_text(
        encoding="utf-8"
    )
    assert "docker-compose.autoheal.yml" in src
    assert "--remove-orphans" not in src
