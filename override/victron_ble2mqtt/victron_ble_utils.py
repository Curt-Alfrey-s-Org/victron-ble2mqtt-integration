import inspect
import logging
from enum import Enum
from typing import Dict, List

from bleak import BLEDevice
from tomlkit.items import Table
from victron_ble.devices import (
	Device,
	DeviceData,
	BatteryMonitor,
	SolarCharger,
	detect_device_type,
)
from victron_ble.exceptions import AdvertisementKeyMismatchError

logger = logging.getLogger(__name__)


def values2dict(obj: DeviceData) -> dict:
	data = {}
	for name, method in inspect.getmembers(obj, predicate=inspect.ismethod):
		if name.startswith("get_"):
			value = method()
			if isinstance(value, Enum):
				# Some IntFlag/Flag combinations or patched values may have no .name
				enum_name = getattr(value, 'name', None)
				if enum_name:
					value = enum_name.lower()
				else:
					# Derive a readable string, e.g. "A|B" -> "a|b", or fallback to raw value
					text = str(value)
					if '.' in text:
						parts = text.split('|')
						parts = [p.split('.')[-1] for p in parts]
						text = '|'.join(parts)
					value = text.lower()
			if value is not None:
				data[name[4:]] = value
	return data

class GenericDevice:
	def __init__(self, victron_device: Device, ble_device: BLEDevice):
		self.victron_device = victron_device
		self.ble_device = ble_device

	def parse(self, *, raw_data) -> dict:
		device_data: DeviceData = self.victron_device.parse(raw_data)
		data_dict = values2dict(device_data)
		return data_dict

class DeviceHandler:
	def __init__(self, device_keys: List[Dict]):
		self.devices = {}
		self.device_type_map = {
			'SmartShunt': BatteryMonitor,
			'BlueSolar': SolarCharger,
			'BatteryMonitor': BatteryMonitor,
			'SolarCharger': SolarCharger
		}
		for device_info in device_keys:
			mac = (device_info.get('mac') or '').upper()
			device_type = device_info.get('type')
			name = device_info.get('name')
			advertisement_key = device_info.get('advertisement_key')
			# Normalize key to a clean string
			if isinstance(advertisement_key, Table):
				advertisement_key = str(advertisement_key.unwrap())
			elif not isinstance(advertisement_key, str):
				advertisement_key = str(advertisement_key or '')
			advertisement_key = advertisement_key.strip()
			# Validate hex key: exactly 32 hex chars (even length), no non-hex
			if not advertisement_key or len(advertisement_key) != 32 or not all(
				c in '0123456789abcdefABCDEF' for c in advertisement_key
			):
				logger.error('Invalid advertisement_key (must be 32 hex) %r for %s (%s)', advertisement_key, mac, name)
				continue
			DeviceClass = self.device_type_map.get(device_type)
			if not DeviceClass:
				logger.error('Unknown device type %s for %s', device_type, mac)
				continue
			try:
				victron_device = DeviceClass(advertisement_key)
				self.devices[mac] = GenericDevice(victron_device, ble_device=None)
				logger.info('Registered device %s (%s) as %s', name, mac, DeviceClass.__name__)
			except Exception as e:
				logger.error('Failed to register device %s: %s', mac, e)

	def get_generic_device(self, device: BLEDevice, raw_data: bytes) -> GenericDevice | None:
		address = device.address.upper()
		if address in self.devices:
			return self.devices[address]
		logger.info('Device %s not pre-registered, attempting detection', address)
		if DeviceClass := detect_device_type(raw_data):
			for device_info in self.devices.values():
				try:
					victron_device = DeviceClass(device_info.victron_device.advertisement_key)
					victron_device.parse(raw_data)
					generic_device = GenericDevice(victron_device, ble_device=device)
					self.devices[address] = generic_device
					logger.info('Registered new device: %s', device.name)
					return generic_device
				except (AdvertisementKeyMismatchError, ValueError) as err:
					logger.warning('Error parsing data: %s', err)
		logger.error('No valid device type for %s', address)
		return None


