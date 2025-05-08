from collections import defaultdict
from datetime import timedelta
import logging

import async_timeout
from fireboard_cloud_api_client import FireboardAPI

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .sensor import FireboardSensor

_LOGGER = logging.getLogger(__name__)


class FireboardCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry):
        """Initialize the coordinator."""
        self._entry_id = entry.entry_id
        self._api = FireboardAPI(entry.data["email"], entry.data["password"])
        self.data = {}

        super().__init__(
            hass,
            _LOGGER,
            name="Fireboard Coordinator",
            update_interval=timedelta(minutes=1),
            always_update=True,
        )

    async def _async_update_data(self):
        try:
            async with async_timeout.timeout(60):
                _LOGGER.debug("Polling Fireboard API")
                if not self.data:
                    _LOGGER.warning("No sensors registered yet; skipping update")
                    return {}

                updated = {}
                uuid_to_sensors = defaultdict(list)
                drive_sensors = []

                # Group sensors by UUID
                for key, sensor in self.data.items():
                    if isinstance(sensor, FireboardSensor):
                        uuid_to_sensors[sensor.get_uuid()].append((key, sensor))
                    else:
                        drive_sensors.append(sensor)

                for drive in drive_sensors:
                    data = await self._api.get_realtime_drivelog(drive.get_uuid())
                    if data:
                        drive.drive_value = data["driveper"] * 100
                    else:
                        drive.drive_value = None
                    updated[drive.unique_id] = drive

                # Fetch data once per unique UUID
                for uuid, sensor_list in uuid_to_sensors.items():
                    try:
                        data = await self._api.get_realtime_temperature(uuid)
                        for key, sensor in sensor_list:
                            channel_data = next(
                                (
                                    ch
                                    for ch in data
                                    if ch["channel"] == sensor.get_channel_number()
                                ),
                                None,
                            )
                            if channel_data:
                                sensor.sensor_value = channel_data["temp"]
                            else:
                                sensor.sensor_value = None
                            updated[key] = sensor
                    except Exception as e:
                        _LOGGER.error("Failed to fetch data for UUID %s: %s", uuid, e)

                return updated
        except Exception as e:
            _LOGGER.error("Error fetching data: %s", e)
            raise UpdateFailed(f"Error communicating with Fireboard API: {e}") from e

    async def get_fb_devices(self):
        """Asynchronously retrieve the list of Fireboard devices from the API.

        Returns:
            list: A list of devices as returned by the Fireboard API.

        Raises:
            Any exception raised by the underlying API call.

        """
        return await self._api.list_devices()
