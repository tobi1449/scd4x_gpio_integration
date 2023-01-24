"""
Custom integration to integrate scd4x_gpio_integration with Home Assistant.
"""
import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .scd4x_api import SCD4xAPI

from .const import (
    DOMAIN,
    PLATFORMS,
    STARTUP_MESSAGE, CONF_I2C, TEMP_SENSOR, CO2_SENSOR, HUMIDITY_SENSOR,
)

SCAN_INTERVAL = timedelta(seconds=5)

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: Config):
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})
        _LOGGER.info(STARTUP_MESSAGE)

    i2cpath = entry.data.get(CONF_I2C)

    coordinator = SCD4XDataUpdateCoordinator(hass, i2cpath)
    await coordinator.async_setup()
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = coordinator

    for platform in PLATFORMS:
        if entry.options.get(platform, True):
            coordinator.platforms.append(platform)
            await hass.async_add_job(hass.config_entries.async_forward_entry_setup(entry, platform))

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


class SCD4XDataUpdateCoordinator(DataUpdateCoordinator):

    def __init__(self, hass: HomeAssistant, i2cpath: str) -> None:
        self.platforms = []

        self._i2cpath = i2cpath
        self._api = SCD4xAPI(i2cpath)

        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)

    async def async_stop(self) -> None:
        try:
            await self._api.async_stop()
        except Exception as exception:
            raise ConfigEntryError from exception

    async def _async_update_data(self):
        try:
            sensor_data = await self._api.async_read_data()
            data = {
                CO2_SENSOR: sensor_data[0].co2,
                TEMP_SENSOR: sensor_data[1].degrees_celsius,
                HUMIDITY_SENSOR: sensor_data[2].percent_rh
            }
            return data
        except Exception as exception:
            raise UpdateFailed() from exception

    async def async_setup(self) -> None:
        try:
            await self._api.async_initialize()
        except Exception as exception:
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
