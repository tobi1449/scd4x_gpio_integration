"""Constants for scd4x_gpio_integration."""
from homeassistant.const import Platform

# Base component constants
NAME = "SCD4x GPIO Integration"
DOMAIN = "scd4x_gpio_integration"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "0.0.1"
ATTRIBUTION = ""
ISSUE_URL = "https://github.com/tobi1449/scd4x_gpio_integration/issues"

# Icons
TEMP_ICON = "mdi:thermometer"
HUMIDITY_ICON = "mdi:water-percent"
CO2_ICON = "mdi:molecule-co2"

# Sensor Keys
TEMP_SENSOR = "temperature_sensor"
CO2_SENSOR = "co2_sensor"
HUMIDITY_SENSOR = "humidity_sensor"

# Platforms
PLATFORMS = [Platform.SENSOR]

# Configuration and options
CONF_ENABLED = "enabled"
CONF_I2C = "i2c_path"
CONF_SERIAL = "device_serial_number"
CONF_ALTITUDE = "altitude"
CONF_AVERAGE_WINDOW = "moving_average_window"

# Defaults
DEFAULT_NAME = DOMAIN


STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""
