"""Adds config flow for Blueprint."""
import logging
from typing import Optional

import voluptuous as vol
from homeassistant import config_entries

from . import SCD4xAPI
from .const import (DOMAIN, CONF_I2C, CONF_SERIAL, CONF_ALTITUDE, CONF_AVERAGE_WINDOW, CONF_TEMPERATURE_OFFSET,
                    CONF_DEVICE_NAME)

_LOGGER: logging.Logger = logging.getLogger(__package__)


class Scd4xConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        self._errors = {}

        if user_input is not None:
            i2c_path = user_input[CONF_I2C]
            _LOGGER.debug(f"User gave {i2c_path} as path. Testing.")

            altitude = None
            if CONF_ALTITUDE in user_input:
                altitude = user_input[CONF_ALTITUDE]

            temperature_offset = None
            if CONF_TEMPERATURE_OFFSET in user_input:
                temperature_offset = user_input[CONF_TEMPERATURE_OFFSET]

            valid, serial = await self._test_i2cpath(i2c_path, altitude, temperature_offset)

            if valid:
                _LOGGER.debug(f"Device Serial Number: {serial}")
                user_input[CONF_SERIAL] = serial

                return self.async_create_entry(title="SCD4x Sensor", data=user_input)
            else:
                self._errors["base"] = "unable_to_connect"

            return await self._show_config_form(user_input)

        user_input = {CONF_DEVICE_NAME: "", CONF_I2C: "", CONF_ALTITUDE: None, CONF_AVERAGE_WINDOW: 60,
                      CONF_TEMPERATURE_OFFSET: 4}
        # Provide defaults for form

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argumentS
        return self.async_show_form(step_id="user", data_schema=vol.Schema(
            {vol.Required(CONF_DEVICE_NAME): vol.Coerce(str),
                vol.Required(CONF_I2C, default=user_input[CONF_I2C]): vol.Coerce(str),
                vol.Optional(CONF_ALTITUDE): vol.All(vol.Coerce(int), vol.Range(min=-100, max=10000)),
                vol.Optional(CONF_AVERAGE_WINDOW): vol.All(vol.Coerce(int), vol.Range(min=1)),
                vol.Optional(CONF_TEMPERATURE_OFFSET, default=4): vol.All(vol.Coerce(float),
                                                                          vol.Range(min=0, max=10)), }),
            errors=self._errors, )

    async def _test_i2cpath(self, i2cpath: str, altitude: Optional[int], temperature_offset: Optional[float]):
        serial = None
        api = None
        try:
            _LOGGER.debug(f"Testing path {i2cpath}, altitude {altitude}")
            _LOGGER.debug(f"Initializing API")
            api = SCD4xAPI(i2cpath, altitude, temperature_offset)
            serial = await api.async_initialize()
        except Exception as exception:
            _LOGGER.error(f"Exception while testing i2c path: {exception}")
            if api is not None:
                await api.async_stop()
            raise exception
        finally:
            _LOGGER.debug(f"Stopping API")
            await api.async_stop()

            if serial is None or serial == 0:
                _LOGGER.debug(f"No serial found: {serial}")
                return False, None
            else:
                _LOGGER.debug(f"Serial found: {serial}")
                return True, serial
