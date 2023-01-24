import logging
import asyncio
import async_timeout
from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection
from sensirion_i2c_scd import Scd4xI2cDevice
from sensirion_i2c_scd.scd4x.response_types import Scd4xCarbonDioxide, Scd4xTemperature, Scd4xHumidity

TIMEOUT = 10


_LOGGER: logging.Logger = logging.getLogger(__package__)

HEADERS = {"Content-type": "application/json; charset=UTF-8"}


class SCD4xAPI:
    def __init__(self, i2cpath: str) -> None:
        self._scd4x = None
        self._i2c_connection = None
        self._i2c_transceiver = None
        self._i2cpath = i2cpath

    async def async_initialize(self) -> None:
        try:
            async with async_timeout.timeout(TIMEOUT):
                _LOGGER.info("Initialize API called.")
                self._i2c_transceiver = LinuxI2cTransceiver(self._i2cpath)
                self._i2c_transceiver.open()

                self._i2c_connection = I2cConnection(self._i2c_transceiver)
                self._scd4x = Scd4xI2cDevice(self._i2c_connection)

                self._scd4x.stop_periodic_measurement()
                await asyncio.sleep(1)
                self._scd4x.reinit()
                await asyncio.sleep(5)
                self._scd4x.start_periodic_measurement()

        except Exception as exception:
            _LOGGER.error("An exception occured! - %s", exception)

    async def async_stop(self) -> None:
        try:
            async with async_timeout.timeout(TIMEOUT):
                _LOGGER.info("Stop API called.")
                self._scd4x.stop_periodic_measurement()
                self._i2c_transceiver.close()

        except Exception as exception:
            _LOGGER.error("An exception occured! - %s", exception)

    async def async_read_data(self) -> tuple[Scd4xCarbonDioxide, Scd4xTemperature, Scd4xHumidity]:
        try:
            async with async_timeout.timeout(TIMEOUT):
                return self._scd4x.read_measurement()
        except Exception as exception:
            _LOGGER.error("An exception occured! - %s", exception)

    async def async_get_serial(self):
        try:
            async with async_timeout.timeout(TIMEOUT):
                return self._scd4x.get_serial()
        except Exception as exception:
            _LOGGER.error("An exception occured! - %s", exception)

