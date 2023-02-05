"""Adds config flow for Blueprint."""
from typing import Optional

from homeassistant import config_entries
import voluptuous as vol
import logging

from . import SCD4xAPI
from .const import (
    DOMAIN,
    CONF_I2C, CONF_SERIAL, CONF_ALTITUDE
)

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
            altitude = None
            if CONF_ALTITUDE in user_input:
                altitude = user_input.get(CONF_ALTITUDE)

            if altitude is int and (-100 >= altitude or altitude >= 10000):
                _LOGGER.info(f"Invalid altitude: {altitude}")
                self._errors["base"] = "invalid_altitude"
            else:
                i2c_path = user_input[CONF_I2C]
                _LOGGER.info(f"User gave {i2c_path} as path. Testing.")
                valid, serial = await self._test_i2cpath(i2c_path, altitude)

                if valid:
                    _LOGGER.info(f"Device Serial Number: {serial}")
                    user_input[CONF_SERIAL] = serial
                    return self.async_create_entry(title="SCD4x Sensor", data=user_input)
                else:
                    self._errors["base"] = "unable_to_connect"

            return await self._show_config_form(user_input)

        user_input = {CONF_I2C: "", CONF_ALTITUDE: None}
        # Provide defaults for form

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_I2C, default=user_input[CONF_I2C]): str,
                    vol.Optional(CONF_ALTITUDE): int,
                }
            ),
            errors=self._errors,
        )

    async def _test_i2cpath(self, i2cpath: str, altitude: Optional[int]):
        serial = None
        api = None
        try:
            _LOGGER.info(f"Testing path {i2cpath}, altitude {altitude}")
            _LOGGER.info(f"Initializing API")
            api = SCD4xAPI(i2cpath, altitude)
            serial = await api.async_initialize()
        except Exception as exception:
            _LOGGER.error(f"Exception while testing i2c path: {exception}")
            if api is not None:
                await api.async_stop()
            raise exception
        finally:
            _LOGGER.info(f"Stopping API")
            await api.async_stop()

            if serial is None or serial == 0:
                _LOGGER.info(f"No serial found: {serial}")
                return False, None
            else:
                _LOGGER.info(f"Serial found: {serial}")
                return True, serial
