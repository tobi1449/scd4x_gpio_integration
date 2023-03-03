"""
Custom integration to integrate scd4x_gpio_integration with Home Assistant.
"""
import asyncio
import logging
import statistics
from datetime import timedelta
from queue import Queue
from typing import Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE, CONF_I2C, TEMP_SENSOR, CO2_SENSOR, HUMIDITY_SENSOR, CONF_ALTITUDE, CONF_AVERAGE_WINDOW,
)
from .scd4x_api import SCD4xAPI

SCAN_INTERVAL = timedelta(seconds=5)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    _LOGGER.info("Setting up SCD4x GPIO Integration")
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    i2cpath = entry.data.get(CONF_I2C)
    altitude = None
    if CONF_ALTITUDE in entry.data:
        altitude = entry.data.get(CONF_ALTITUDE)

    moving_average_window = None
    if CONF_AVERAGE_WINDOW in entry.data:
        moving_average_window = entry.data.get(CONF_AVERAGE_WINDOW)

    _LOGGER.info(f"Configured I2C Path is {i2cpath}")
    _LOGGER.info(f"Configured Altitude is {altitude}")
    _LOGGER.info(f"Configured Moving Average Time Window is {moving_average_window}")

    coordinator = SCD4XDataUpdateCoordinator(hass, i2cpath, altitude, moving_average_window)
    await coordinator.async_setup()
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        _LOGGER.info("Coordinator Last Update Success is false")
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            coordinator.platforms.append(platform)
            await hass.async_add_job(hass.config_entries.async_forward_entry_setup(entry, platform))

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


def recalculate_value(queue: Queue, new_value: float) -> float:
    if queue.full():
        queue.get()

    queue.put(new_value)
    return statistics.mean(queue)


class SCD4XDataUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, i2cpath: str, altitude: Optional[int],
                 moving_average_window: Optional[int]) -> None:
        _LOGGER.info("Initializing coordinator for SCD4x GPIO Integration")
        self.platforms = []

        self._api = SCD4xAPI(i2cpath, altitude)
        self._moving_average_window = moving_average_window
        if self._moving_average_window is None or self._moving_average_window < 1:
            self._moving_average_window = 1

        self._co2_queue = Queue(self._moving_average_window)
        self._temp_queue = Queue(self._moving_average_window)
        self._hum_queue = Queue(self._moving_average_window)

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def async_stop(self) -> None:
        try:
            _LOGGER.info("Stopping SCD4x API")
            await self._api.async_stop()
        except Exception as exception:
            raise ConfigEntryError from exception

    async def _async_update_data(self):
        try:
            _LOGGER.info("Try to get new data from SCD4x API")
            sensor_data = await self._api.async_read_data()

            if not sensor_data:
                raise UpdateFailed()

            data = {
                CO2_SENSOR: round(recalculate_value(self._co2_queue, sensor_data[0]), 2),
                TEMP_SENSOR: round(recalculate_value(self._temp_queue, sensor_data[1]), 2),
                HUMIDITY_SENSOR: round(recalculate_value(self._hum_queue, sensor_data[2]), 2)
            }
            return data
        except Exception as exception:
            raise UpdateFailed() from exception

    async def async_setup(self) -> None:
        try:
            _LOGGER.info("Setting up SCD4x coordinator")
            await self._api.async_initialize()
        except Exception as exception:
            await self._api.async_stop()
            raise ConfigEntryError from exception


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    unloaded = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
                if platform in coordinator.platforms
            ]
        )
    )
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop()

    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
