import logging
try:
    from victron_ble.devices.battery_monitor import AlarmReason
    _MASK = 0x1FFF  # bits 0..12 allowed in victron-ble 0.9.2

    def _missing_(cls, value):
        masked = int(value) & _MASK
        if masked != value:
            logging.getLogger("victron_ble.patch").warning(
                "BatteryMonitor AlarmReason had unknown bits: 0x%04X -> 0x%04X (masked)",
                value, masked
            )
        return cls(masked)

    AlarmReason._missing_ = classmethod(_missing_)
except Exception as e:
    logging.getLogger("victron_ble.patch").exception("AlarmReason patch failed: %s", e)
