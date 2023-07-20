import asyncio
import logging
from typing import Optional

import async_timeout
from asyncer import asyncify
from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection
from sensirion_i2c_scd import Scd4xI2cDevice

TIMEOUT = 30

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

def get_sensor_altitude(scd4x: Scd4xI2cDevice) -> int:
    return scd4x.get_sensor_altitude()

def set_temperature_offset(scd4x: Scd4xI2cDevice, temperature_offset):
    scd4x.set_temperature_offset(temperature_offset)

def get_temperature_offset(scd4x: Scd4xI2cDevice) -> float:
    return scd4x.get_temperature_offset()

def persist_settings(scd4x: Scd4xI2cDevice):
    scd4x.persist_settings()


class SCD4xAPI:
    def __init__(self, i2cpath: str, altitude: Optional[int], temperature_offset: Optional[float]) -> None:
        _LOGGER.info("Initializing SCD4x API")
        self._scd4x = None
        self._i2c_connection = None
        self._i2c_transceiver = None
        self._connection_established = False
        self._i2cpath = i2cpath
        self._altitude = altitude
        self._temperature_offset = temperature_offset

    async def async_initialize(self) -> int:
        async with async_timeout.timeout(TIMEOUT):
            _LOGGER.debug("Initialize API called.")
            _LOGGER.debug("Creating i2c transceiver.")
            self._i2c_transceiver = LinuxI2cTransceiver(self._i2cpath)
            _LOGGER.debug("Try opening connection via i2c transceiver.")
            self._i2c_transceiver.open()

            _LOGGER.debug("Creating i2c connection.")
            self._i2c_connection = I2cConnection(self._i2c_transceiver)
            _LOGGER.debug("Creating scd4x i2c device.")
            self._scd4x = Scd4xI2cDevice(self._i2c_connection)

            _LOGGER.debug("Stopping periodic measurements.")
            await asyncify(stop_periodic_measurement)(scd4x=self._scd4x)
            await asyncio.sleep(1)

            _LOGGER.debug("Reading serial number.")
            serial = await asyncify(read_serial_number)(scd4x=self._scd4x)
            _LOGGER.debug(f"Serial Number {serial}")

            should_save = False

            saved_altitude = asyncify(get_sensor_altitude)(scd4x=self._scd4x)
            altitude = self._altitude if self._altitude is not None else 0
            if altitude is not saved_altitude:
                _LOGGER.debug(f"Setting altitude to {self._altitude}")
                await asyncify(set_sensor_altitude)(scd4x=self._scd4x, sensor_altitude=self._altitude)
                should_save = True

            saved_temperature_offset = asyncify(get_temperature_offset)(scd4x=self._scd4x)
            temperature_offset = self._temperature_offset if self._temperature_offset is not None else 4.0
            if temperature_offset is not saved_temperature_offset:
                _LOGGER.debug(f"Setting temperature offset to {self._temperature_offset}")
                await asyncify(set_temperature_offset)(scd4x=self._scd4x, temperature_offset=self._temperature_offset)
                should_save = True

            if should_save is True:
                await asyncify(persist_settings)(scd4x=self._scd4x)

            _LOGGER.debug("Reinitializing device.")
            await asyncify(reinit)(scd4x=self._scd4x)
            await asyncio.sleep(5)

            await asyncify(start_periodic_measurement)(scd4x=self._scd4x)
            _LOGGER.debug("Starting periodic measurements.")

            await asyncio.sleep(1)

            self._connection_established = True
            return serial

    async def async_stop(self) -> None:
        async with async_timeout.timeout(TIMEOUT):
            _LOGGER.debug("Stop API called.")
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

            _LOGGER.debug("Data ready, getting data")
            co2, temp, humidity = await asyncify(read_measurement)(scd4x=self._scd4x)
            _LOGGER.debug(f"Data available: {co2.co2};{temp.degrees_celsius};{humidity.percent_rh}")
            return co2.co2, temp.degrees_celsius, humidity.percent_rh
