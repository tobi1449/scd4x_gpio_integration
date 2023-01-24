"""BlueprintEntity class"""
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME, VERSION, ATTRIBUTION, CONF_SERIAL


class SCD4XEntity(CoordinatorEntity):
    def __init__(self, coordinator, config_entry : ConfigEntry):
        super().__init__(coordinator)
        self.config_entry = config_entry
        self._serial = config_entry.data[CONF_SERIAL]

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial)},
            name=NAME,
            model=VERSION,
            manufacturer=NAME
        )

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "attribution": ATTRIBUTION,
            "id": str(self.coordinator.data.get("id")),
            "integration": DOMAIN,
        }
