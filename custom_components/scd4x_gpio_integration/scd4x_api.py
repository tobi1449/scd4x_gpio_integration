import asyncio
import functools
import logging
import traceback
from typing import Optional

import async_timeout
from sensirion_i2c_driver import LinuxI2cTransceiver, I2cConnection
from sensirion_i2c_scd import Scd4xI2cDevice

TIMEOUT = 30

_LOGGER: logging.Logger = logging.getLogger(__package__)

HEADERS = {"Content-type": "application/json; charset=UTF-8"}


async def run_async(method):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, method)


async def stop_periodic_measurement(scd4x: Scd4xI2cDevice):
    await run_async(functools.partial(Scd4xI2cDevice.stop_periodic_measurement, self=scd4x))


async def reinit(scd4x: Scd4xI2cDevice):
    await run_async(functools.partial(Scd4xI2cDevice.reinit, self=scd4x))


async def read_serial_number(scd4x: Scd4xI2cDevice) -> int:
    return await run_async(functools.partial(Scd4xI2cDevice.read_serial_number, self=scd4x))


async def start_periodic_measurement(scd4x: Scd4xI2cDevice):
    await run_async(functools.partial(Scd4xI2cDevice.start_periodic_measurement, self=scd4x))


async def get_data_ready_status(scd4x: Scd4xI2cDevice) -> bool:
    return await run_async(functools.partial(Scd4xI2cDevice.get_data_ready_status, self=scd4x))


async def read_measurement(scd4x: Scd4xI2cDevice) -> tuple:
    return await run_async(functools.partial(Scd4xI2cDevice.read_measurement, self=scd4x))


async def set_sensor_altitude(scd4x: Scd4xI2cDevice, sensor_altitude):
    await run_async(functools.partial(Scd4xI2cDevice.set_sensor_altitude, self=scd4x, sensor_altitude=sensor_altitude))


async def get_sensor_altitude(scd4x: Scd4xI2cDevice) -> int:
    return await run_async(functools.partial(Scd4xI2cDevice.get_sensor_altitude, self=scd4x))


async def set_temperature_offset(scd4x: Scd4xI2cDevice, temperature_offset):
    await run_async(
        functools.partial(Scd4xI2cDevice.set_temperature_offset, self=scd4x, temperature_offset=temperature_offset))


async def get_temperature_offset(scd4x: Scd4xI2cDevice) -> float:
    return await run_async(functools.partial(Scd4xI2cDevice.get_temperature_offset, self=scd4x))


async def persist_settings(scd4x: Scd4xI2cDevice):
    await run_async(functools.partial(Scd4xI2cDevice.persist_settings, self=scd4x))


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
            await stop_periodic_measurement(self._scd4x)
            await asyncio.sleep(1)

            _LOGGER.debug("Reading serial number.")
            serial = await read_serial_number(self._scd4x)
            _LOGGER.debug(f"Serial Number {serial}")

            should_save = False

            saved_altitude = await get_sensor_altitude(self._scd4x)
            altitude = self._altitude if self._altitude is not None else 0
            if altitude is not saved_altitude:
                _LOGGER.debug(f"Setting altitude to {self._altitude}")
                await set_sensor_altitude(self._scd4x, self._altitude)
                should_save = True

            saved_temperature_offset = get_temperature_offset(self._scd4x)
            temperature_offset = self._temperature_offset if self._temperature_offset is not None else 4.0
            if temperature_offset is not saved_temperature_offset:
                _LOGGER.debug(f"Setting temperature offset to {self._temperature_offset}")
                await set_temperature_offset(self._scd4x, self._temperature_offset)
                should_save = True

            if should_save is True:
                await persist_settings(self._scd4x)

            _LOGGER.debug("Reinitializing device.")
            await reinit(self._scd4x)
            await asyncio.sleep(5)

            await start_periodic_measurement(self._scd4x)
            _LOGGER.debug("Starting periodic measurements.")

            await asyncio.sleep(1)

            self._connection_established = True
            return serial

    async def async_stop(self) -> None:
        async with async_timeout.timeout(TIMEOUT):
            _LOGGER.debug("Stop API called.")
            try:
                if self._scd4x is not None:
                    await stop_periodic_measurement(self._scd4x)
            except Exception as exception:
                _LOGGER.warning(f"Unable to stop SCD4x periodic measurements: {exception}"
                                f"\r\n{traceback.format_exception(exception)}")
            try:
                if self._i2c_transceiver is not None:
                    self._i2c_transceiver.close()
            except Exception as exception:
                _LOGGER.warning(f"Unable to close i2c transceiver: {exception}"
                                f"\r\n{traceback.format_exception(exception)}")
            finally:
                self._connection_established = False

    async def async_read_data(self) -> Optional[tuple[float, float, float]]:
        if not self._connection_established:
            return None

        async with async_timeout.timeout(TIMEOUT):

            while not await get_data_ready_status(self._scd4x):
                await asyncio.sleep(0.2)

            _LOGGER.debug("Data ready, getting data")
            co2, temp, humidity = await read_measurement(self._scd4x)
            _LOGGER.debug(f"Data available: {co2.co2};{temp.degrees_celsius};{humidity.percent_rh}")
            return co2.co2, temp.degrees_celsius, humidity.percent_rh
