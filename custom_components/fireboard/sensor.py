import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    _coordinator = hass.data[DOMAIN][entry.entry_id]
    devices = await _coordinator.get_fb_devices()
    sensors = []
    for device in devices:
        _LOGGER.debug("Starting channel discovery for %s", device["title"])
        for channel in device["channels"]:
            _LOGGER.debug(
                "Added channel %s for device %s", channel["channel"], device["title"]
            )
            fb_sensor = FireboardSensor(device, channel, _coordinator)
            key = f"{device['hardware_id']}_{channel['channel']}"
            _coordinator.data[key] = fb_sensor
            sensors.append(fb_sensor)

        if device["last_drivelog"] != None:
            key = f"{device['hardware_id']}_drive"
            drive_sensor = FireboardDriveSensor(device, _coordinator)
            _coordinator.data[key] = drive_sensor
            sensors.append(drive_sensor)
    async_add_entities(sensors, update_before_add=True)


class FireboardDriveSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, device, coordinator):
        super().__init__(coordinator)
        self._device = device
        self._key = f"{device['hardware_id']}_drive"
        self._attr_unique_id = self._key
        self.drive_value = None

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["hardware_id"])},
            name=self._device["title"],
            manufacturer="Fireboard",
            model=self._device["model"],
            model_id=self._device["hardware_id"],
        )

    def get_uuid(self):
        return self._device["uuid"]

    @property
    def name(self):
        return "Drive fan output"

    @property
    def unit_of_measurement(self):
        return "%"

    @property
    def unique_id(self) -> str:
        return f"{self._device['hardware_id']}_drive"

    @property
    def native_value(self):
        sensor = self.coordinator.data.get(self._key)
        return getattr(sensor, "drive_value", None)


class FireboardSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, device, channel, coordinator):
        super().__init__(coordinator)
        self._device = device
        self._channel = channel
        self._key = f"{device['hardware_id']}_{channel['channel']}"
        self._attr_unique_id = self._key
        self._degree_type = None
        if device["degreetype"] == 2:
            self._degree_type = UnitOfTemperature.FAHRENHEIT
        else:
            self._degree_type = UnitOfTemperature.CELSIUS

    def get_uuid(self):
        return self._device["uuid"]

    def get_channel_number(self):
        return self._channel["channel"]

    @property
    def native_value(self):
        sensor = self.coordinator.data.get(self._key)
        return getattr(sensor, "sensor_value", None)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def name(self):
        chan_name = f"Channel {self._channel['channel']}"
        if self._channel["channel_label"] != "":
            chan_name = self._channel["channel_label"]
        return f"{self._device['title']} {chan_name}"

    @property
    def unit_of_measurement(self):
        return self._degree_type

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device["hardware_id"])},
            name=self._device["title"],
            manufacturer="Fireboard",
            model=self._device["model"],
            model_id=self._device["hardware_id"],
        )

    @property
    def unique_id(self) -> str:
        return f"{self._device['hardware_id']}_{self._channel['channel']}"

    @property
    def should_report(self):
        return True
