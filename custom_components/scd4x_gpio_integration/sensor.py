"""Sensor platform for scd4x_gpio_integration."""
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    TEMP_CELSIUS,
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DEFAULT_NAME,
    TEMP_ICON,
    DOMAIN,
    TEMP_KEY,
    CO2_KEY,
    HUMIDITY_KEY, CONF_SERIAL, HUMIDITY_ICON, CO2_ICON, CONF_DEVICE_NAME,
)
from .entity import SCD4XEntity

_LOGGER: logging.Logger = logging.getLogger(__package__)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities:
        AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [
        Scd4xSensor(
            hass,
            coordinator,
            entry,
            HUMIDITY_KEY,
            entry.data.get(CONF_DEVICE_NAME),
            SensorDeviceClass.HUMIDITY,
            PERCENTAGE,
            HUMIDITY_ICON
        ),
        Scd4xSensor(
            hass,
            coordinator,
            entry,
            TEMP_KEY,
            entry.data.get(CONF_DEVICE_NAME),
            SensorDeviceClass.TEMPERATURE,
            TEMP_CELSIUS,
            TEMP_ICON
        ),
        Scd4xSensor(
            hass,
            coordinator,
            entry,
            CO2_KEY,
            entry.data.get(CONF_DEVICE_NAME),
            SensorDeviceClass.CO2,
            CONCENTRATION_PARTS_PER_MILLION,
            CO2_ICON
        ),
    ]

    _LOGGER.debug(sensors[0].device_info)
    _LOGGER.debug(sensors[1].device_info)
    _LOGGER.debug(sensors[2].device_info)

    async_add_entities(sensors)


class Scd4xSensor(SCD4XEntity, SensorEntity):
    """scd4x_gpio_integration Sensor class."""

    def __init__(
            self,
            hass,
            coordinator,
            config_entry,
            key: str,
            name: str,
            device_class: SensorDeviceClass,
            unit_of_measurement: str,
            icon: str,
    ):
        super().__init__(coordinator, config_entry)
        self._key = key
        self._device_class = device_class
        self._unit_of_measurement = unit_of_measurement
        self._serial = self.config_entry.data[CONF_SERIAL]
        self._icon = icon
        self._name = name
        self.entity_id = generate_entity_id("sensor.{}", "{0}_{1}".format(name, key), hass=hass)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} {self._key}"

    @property
    def unique_id(self):
        """Return a unique ID to use for this entity."""
        return f"{self._serial}_{self._key}"

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self.coordinator.data[self._key]

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon

    @property
    def state_class(self) -> SensorStateClass | str | None:
        return SensorStateClass.MEASUREMENT

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self._unit_of_measurement

    @property
    def device_class(self):
        return self._device_class
