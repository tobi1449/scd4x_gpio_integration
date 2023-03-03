import logging
import asyncio
from typing import Optional

import async_timeout
from asyncer import asyncify

from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection
from sensirion_i2c_scd import Scd4xI2cDevice

TIMEOUT = 15

_LOGGER: logging.Logger = logging.getLogger(__package__)

HEADERS = {"Content-type": "application/json; charset=UTF-8"}


def stop_periodic_measurement(scd4x: Scd4xI2cDevice):
    scd4x.stop_periodic_measurement()


def reinit(scd4x: Scd4xI2cDevice):
    scd4x.reinit()


def read_serial_number(scd4x: Scd4xI2cDevice) -> int:
    return scd4x.read_serial_number()


def start_periodic_measurement(scd4x: Scd4xI2cDevice):
    scd4x.start_periodic_measurement()


def get_data_ready_status(scd4x: Scd4xI2cDevice) -> bool:
    return scd4x.get_data_ready_status()


def read_measurement(scd4x: Scd4xI2cDevice) -> tuple:
    return scd4x.read_measurement()


def set_sensor_altitude(scd4x: Scd4xI2cDevice, sensor_altitude):
    scd4x.set_sensor_altitude(sensor_altitude)


class SCD4xAPI:
    def __init__(self, i2cpath: str, altitude: Optional[int]) -> None:
        _LOGGER.info("Initializing SCD4x API")
        self._scd4x = None
        self._i2c_connection = None
        self._i2c_transceiver = None
        self._connection_established = False
        self._i2cpath = i2cpath
        self._altitude = altitude

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
            await asyncify(stop_periodic_measurement)(scd4x=self._scd4x)
            await asyncio.sleep(1)

            _LOGGER.info("Reading serial number.")
            serial = await asyncify(read_serial_number)(scd4x=self._scd4x)
            _LOGGER.info(f"Serial Number {serial}")

            if self._altitude is not None:
                _LOGGER.info(f"Setting altitude to {self._altitude}")
                await asyncify(set_sensor_altitude)(scd4x=self._scd4x, sensor_altitude=self._altitude)
            else:
                _LOGGER.info("Setting altitude to 0")
                await asyncify(set_sensor_altitude)(scd4x=self._scd4x, sensor_altitude=0)

            _LOGGER.info("Reinitializing device.")
            await asyncify(reinit)(scd4x=self._scd4x)
            await asyncio.sleep(5)

            await asyncify(start_periodic_measurement)(scd4x=self._scd4x)
            _LOGGER.info("Starting periodic measurements.")

            await asyncio.sleep(1)

            self._connection_established = True
            return serial

    async def async_stop(self) -> None:
        async with async_timeout.timeout(TIMEOUT):
            _LOGGER.info("Stop API called.")
            try:
                if self._scd4x is not None:
                    await asyncify(stop_periodic_measurement)(scd4x=self._scd4x)
            except Exception as exception:
                _LOGGER.warning(f"Unable to stop SCD4x periodic measurements: {exception}")
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

            while not await asyncify(get_data_ready_status)(scd4x=self._scd4x):
                await asyncio.sleep(0.2)

            _LOGGER.info("Data ready, getting data")
            co2, temp, humidity = await asyncify(read_measurement)(scd4x=self._scd4x)
            _LOGGER.info(f"Data available: {co2.co2};{temp.degrees_celsius};{humidity.percent_rh}")
            return co2.co2, temp.degrees_celsius, humidity.percent_rh


