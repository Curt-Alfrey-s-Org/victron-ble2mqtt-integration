"""Forward to override entrypoint and execute main() for runtime."""
from override.victron_ble2mqtt.__main__ import main as _override_main  # noqa: F401

# Execute the real main immediately when this module is launched with -m
_override_main()
