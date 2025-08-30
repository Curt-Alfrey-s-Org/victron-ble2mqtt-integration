import logging
try:
    from victron_ble.devices.battery_monitor import AlarmReason
    _MASK = 0x1FFF  # allow known bits; mask unknown ones

    def _missing_(cls, value):
        masked = int(value) & _MASK
        if masked != value:
            logging.getLogger("victron_ble.patch").warning(
                "BatteryMonitor AlarmReason had unknown bits: 0x%04X -> 0x%04X (masked)",
                value, masked,
            )
        # Avoid recursion: try to create a pseudo member (Flags),
        # else build a raw enum instance without invoking Enum.__new__ again.
        for member in cls:
            if member.value == masked:
                return member
        try:
            # For Flag / IntFlag types this creates a composite without recursion
            return cls._create_pseudo_member_(masked)  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            inst = int.__new__(cls, masked)
        except Exception:
            inst = object.__new__(cls)
        inst._value_ = masked
        # leave _name_ unset (None) to indicate synthesized value
        inst._name_ = None
        return inst

    AlarmReason._missing_ = classmethod(_missing_)
except Exception as e:
    logging.getLogger("victron_ble.patch").exception("AlarmReason patch failed: %s", e)
