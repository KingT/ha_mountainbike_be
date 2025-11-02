from __future__ import annotations
import logging
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.entity import CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from requests_html import HTMLSession
from .const import DOMAIN, URL, PROVINCES, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    await async_setup_entry(hass, None, async_add_entities)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator = MTBDataCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()
    async_add_entities([MTBSensor(coordinator)], True)

class MTBDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass):
        super().__init__(
            hass,
            _LOGGER,
            name="MTB Tour Calendar",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self):
        try:
            return await hass.async_add_executor_job(fetch_mbt_data)
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")

def fetch_mbt_data():
    session = HTMLSession()
    r = session.get(URL)
    r.html.render(timeout=30, sleep=3)

    rows = r.html.find("div.views-row")
    data = []
    for row in rows:
        text = row.text
        if not any(p in text for p in PROVINCES):
            continue

        def safe_sel(selector):
            el = row.find(selector, first=True)
            return el.text.strip() if el else ""

        data.append({
            "date": safe_sel(".views-field-field-toertocht-datum"),
            "title": safe_sel(".views-field-title"),
            "location": safe_sel(".views-field-field-gemeente"),
            "province": safe_sel(".views-field-field-provincie"),
            "distance": safe_sel(".views-field-field-afstanden"),
            "organizer": safe_sel(".views-field-field-club"),
            "link": "https://mountainbike.be" + row.find("a", first=True).attrs.get("href", ""),
        })

    session.close()
    return sorted(data, key=lambda x: x["date"])

class MTBSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_name = "MTB Tour Calendar"
        self._attr_unique_id = "mtb_tours"

    @property
    def native_value(self):
        return len(self.coordinator.data) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self):
        return {"tours": self.coordinator.data}
