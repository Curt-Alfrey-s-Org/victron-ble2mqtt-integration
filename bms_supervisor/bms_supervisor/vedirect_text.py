"""VE.Direct Text-mode parser (protocol 3.34) -- read-only, no HEX transmit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

# Official: VE.Direct Protocol 3.34, FAQ Q8 checksum (modulo-256 sum == 0).
# https://www.victronenergy.com/upload/documents/VE.Direct-Protocol-3.34.pdf
# https://www.victronenergy.com/live/vedirect_protocol:faq

_CHECKSUM_PREFIX = b"\r\nChecksum\t"

# Protocol 3.34 footnotes 8, 10, 11: "---" when no temp sensor, BMV unsynced, or DC monitor.
# https://www.victronenergy.com/upload/documents/VE.Direct-Protocol-3.34.pdf
_VEDIRECT_NA = "---"


def _value_present(value: str) -> bool:
    """Return False for empty or not-available VE.Direct placeholders."""
    stripped = value.strip()
    return stripped != "" and stripped != _VEDIRECT_NA


@dataclass(frozen=True)
class ParsedMetrics:
    """SI-unit values extracted from one valid Text block."""

    voltage_v: float | None = None
    current_a: float | None = None
    power_w: float | None = None
    soc_pct: float | None = None
    consumed_ah: float | None = None
    temperature_c: float | None = None
    alarm: str | None = None  # ON or OFF


def checksum_valid(block: bytes) -> bool:
    """Return True when sum of all bytes in block (incl. checksum byte) % 256 == 0."""
    if len(block) < len(_CHECKSUM_PREFIX) + 1:
        return False
    return sum(block) % 256 == 0


def parse_fields(block: bytes) -> dict[str, str]:
    """Parse label/value pairs; names normalized to uppercase."""
    fields: dict[str, str] = {}
    for line in block.split(b"\r\n"):
        if not line or b"\t" not in line:
            continue
        name_b, value_b = line.split(b"\t", 1)
        name = name_b.decode("ascii", errors="replace").upper()
        if name == "CHECKSUM":
            continue
        fields[name] = value_b.decode("ascii", errors="replace")
    return fields


def fields_to_metrics(fields: dict[str, str]) -> ParsedMetrics:
    """Convert raw VE.Direct fields to SI units per protocol 3.34."""
    voltage_v = None
    current_a = None
    power_w = None
    soc_pct = None
    consumed_ah = None
    temperature_c = None
    alarm = None

    if "V" in fields and _value_present(fields["V"]):
        voltage_v = int(fields["V"]) / 1000.0
    if "I" in fields and _value_present(fields["I"]):
        current_a = int(fields["I"]) / 1000.0
    if "P" in fields and _value_present(fields["P"]):
        power_w = float(fields["P"])
    if "SOC" in fields and _value_present(fields["SOC"]):
        soc_pct = int(fields["SOC"]) / 10.0
    if "CE" in fields and _value_present(fields["CE"]):
        consumed_ah = int(fields["CE"]) / 1000.0
    if "T" in fields and _value_present(fields["T"]):
        temperature_c = float(fields["T"])
    if "ALARM" in fields and _value_present(fields["ALARM"]):
        alarm = fields["ALARM"].upper()

    return ParsedMetrics(
        voltage_v=voltage_v,
        current_a=current_a,
        power_w=power_w,
        soc_pct=soc_pct,
        consumed_ah=consumed_ah,
        temperature_c=temperature_c,
        alarm=alarm,
    )


class VeDirectTextParser:
    """Incremental Text-mode frame handler; skips HEX (:) frames."""

    def __init__(self) -> None:
        self._buf = bytearray()
        self._hex_skip = False

    def feed(self, data: bytes) -> Iterator[dict[str, str]]:
        """Consume bytes; yield field dicts for each valid Text block."""
        for byte in data:
            if self._hex_skip:
                if byte == ord("\n"):
                    self._hex_skip = False
                continue

            at_line_start = not self._buf or self._buf[-1] in (ord("\n"), ord("\r"))
            if byte == ord(":") and at_line_start:
                self._hex_skip = True
                self._buf.clear()
                continue

            self._buf.append(byte)

            while True:
                block = self._extract_complete_block()
                if block is None:
                    break
                if checksum_valid(block):
                    yield parse_fields(block)
                # invalid checksum blocks are discarded silently

    def _extract_complete_block(self) -> bytes | None:
        idx = self._buf.find(_CHECKSUM_PREFIX)
        if idx < 0:
            return None
        checksum_byte_pos = idx + len(_CHECKSUM_PREFIX)
        if len(self._buf) <= checksum_byte_pos:
            return None
        block = bytes(self._buf[: checksum_byte_pos + 1])
        del self._buf[: checksum_byte_pos + 1]
        return block
