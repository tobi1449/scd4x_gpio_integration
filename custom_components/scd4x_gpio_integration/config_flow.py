"""Adds config flow for Blueprint."""
from homeassistant import config_entries
from homeassistant.core import callback
import voluptuous as vol
import logging

from . import SCD4xAPI
from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_I2C, CONF_SERIAL
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
            _LOGGER.info(f"User gave {user_input[CONF_I2C]} as path. Testing.")
            valid, serial = await self._test_i2cpath(user_input[CONF_I2C])
            _LOGGER.info(f"Path Test Result: {valid}")
            if valid:
                _LOGGER.info(f"Device Serial Number: {serial}")
                user_input[CONF_SERIAL] = serial
                return self.async_create_entry(
                    title=user_input[CONF_I2C], data=user_input
                )
            else:
                self._errors["base"] = "unable_to_connect"

            return await self._show_config_form(user_input)

        user_input = {CONF_I2C: ""}
        # Provide defaults for form

        return await self._show_config_form(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return Scd4xOptionsFlowHandler(config_entry)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_I2C, default=user_input[CONF_I2C]): str,
                }
            ),
            errors=self._errors,
        )

    async def _test_i2cpath(self, i2cpath):
        serial = None
        try:
            _LOGGER.info(f"Testing path {i2cpath}")
            _LOGGER.info(f"Initializing API")
            api = SCD4xAPI(i2cpath)
            serial = await api.async_initialize()
        except Exception as exception:
            _LOGGER.error("Exception while testing i2c path.")
            await api.async_stop()
            print(exception.args)
            raise exception
        finally:
            _LOGGER.info(f"Stopping API")
            await api.async_stop()

            if serial is None or serial == 0:
                _LOGGER.info(f"No serial found: {serial}")
                return False,
            else:
                _LOGGER.info(f"Serial found: {serial}")
                return True, serial


class Scd4xOptionsFlowHandler(config_entries.OptionsFlow):
    """Blueprint config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(x, default=self.options.get(x, True)): bool
                    for x in sorted(PLATFORMS)
                }
            ),
        )

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(
            title=self.config_entry.data.get(CONF_I2C), data=self.options
        )