import os

# Ensure the `override/victron_ble2mqtt` directory is searched first for submodules.
# This avoids moving files and keeps original override sources intact while
# making `import victron_ble2mqtt...` work from the repo root for tests and runtime.
pkg_override = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "override", "victron_ble2mqtt"))
if os.path.isdir(pkg_override):
    # Insert at start of package search path
    __path__.insert(0, pkg_override)

# Minimal package metadata
__all__ = []
"""Local victron_ble2mqtt package (consolidated copy).

This file intentionally small so imports work when running from the repo.
"""
__all__ = ["user_settings"]
__version__ = "0.0.0-local"
