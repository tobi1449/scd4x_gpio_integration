import logging
import asyncio
from typing import Optional

import async_timeout

from .sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection
from .sensirion_i2c_scd import Scd4xI2cDevice

TIMEOUT = 15

_LOGGER: logging.Logger = logging.getLogger(__package__)

HEADERS = {"Content-type": "application/json; charset=UTF-8"}


class SCD4xAPI:
    def __init__(self, i2cpath: str) -> None:
        _LOGGER.info("Initializing SCD4x API")
        self._scd4x = None
        self._i2c_connection = None
        self._i2c_transceiver = None
        self._connection_established = False
        self._i2cpath = i2cpath

    async def async_initialize(self) -> int:
        async with async_timeout.timeout(TIMEOUT):
            _LOGGER.info("Initialize API called.")
            _LOGGER.info("Creating i2c transceiver.")
            self._i2c_transceiver = LinuxI2cTransceiver(self._i2cpath)
            _LOGGER.info("Try opening connection via i2c transceiver.")
            self._i2c_transceiver.open()

            _LOGGER.info("Creating i2c connection.")
            self._i2c_connection = I2cConnection(self._i2c_transceiver)
            _LOGGER.info("Creating scd4x i2c device.")
            self._scd4x = Scd4xI2cDevice(self._i2c_connection)

            _LOGGER.info("Stopping periodic measurements.")
            await self._scd4x.async_stop_periodic_measurement()
            await asyncio.sleep(1)
            _LOGGER.info("Reinitializing device.")
            await self._scd4x.async_reinit()
            await asyncio.sleep(5)

            _LOGGER.info("Reading serial number.")
            serial = await self._scd4x.async_read_serial_number()
            _LOGGER.info(f"Serial Number {serial}")

            await self._scd4x.async_start_periodic_measurement()
            _LOGGER.info("Starting periodic measurements.")

            await asyncio.sleep(1)

            self._connection_established = True
            return serial

    async def async_stop(self) -> None:
        async with async_timeout.timeout(TIMEOUT):
            _LOGGER.info("Stop API called.")
            try:
                if self._scd4x is not None:
                    await self._scd4x.async_stop_periodic_measurement()
            except Exception as exception:
                _LOGGER.warning(f"Unable to stop SCD4x perodic measurements: {exception}")
            try:
                if self._i2c_transceiver is not None:
                    self._i2c_transceiver.close()
            except Exception as exception:
                _LOGGER.warning(f"Unable to close i2c transceiver: {exception}")
            finally:
                self._connection_established = False

    async def async_read_data(self) -> Optional[tuple[float, float, float]]:
        if not self._connection_established:
            return None

        async with async_timeout.timeout(TIMEOUT):

            while not await self._scd4x.async_get_data_ready_status():
                await asyncio.sleep(0.2)

            _LOGGER.info("Data ready, getting data")
            co2, temp, humidity = await self._scd4x.async_read_measurement()
            _LOGGER.info(f"Data available: {co2.co2};{temp.degrees_celsius};{humidity.percent_rh}")
            return round(co2.co2, 2), round(temp.degrees_celsius, 2), round(humidity.percent_rh, 2)

    async def async_set_altitude(self, altitude: float):
        if not self._connection_established:
            return

        await self._scd4x.async_set_sensor_altitude(altitude)

    async def async_get_serial_number(self):
        if not self._connection_established:
            return False

        async with async_timeout.timeout(TIMEOUT):
            return await self._scd4x.async_read_serial_number()
