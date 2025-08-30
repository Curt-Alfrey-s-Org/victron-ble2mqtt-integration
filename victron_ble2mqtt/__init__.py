"""Local victron_ble2mqtt shim: delegate to override implementation.

This package provides stable import paths while ensuring code is sourced from
override/victron_ble2mqtt. The actual version is read from the override package.
"""
from override.victron_ble2mqtt import *  # noqa: F401,F403
