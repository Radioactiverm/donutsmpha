"""DataUpdateCoordinator for Donut SMP."""
from __future__ import annotations

import logging
import aiohttp
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN, API_STATS_URL, API_LOOKUP_URL, UPDATE_INTERVAL_SECONDS, CONF_USERNAME, CONF_API_KEY

_LOGGER = logging.getLogger(__name__)

class DonutSMPCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Donut SMP data."""

    def __init__(self, hass: HomeAssistant, entry):
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.username = entry.data[CONF_USERNAME]
        self.api_key = entry.data[CONF_API_KEY]
        self.session = aiohttp.ClientSession()

    async def _async_update_data(self):
        """Fetch data from API."""
        stats_url = API_STATS_URL.format(self.username)
        lookup_url = API_LOOKUP_URL.format(self.username)
        
        headers = {"User-Agent": "Home Assistant DonutSMP Integration"}
        if self.api_key and self.api_key.lower() != "none":
            headers["Authorization"] = self.api_key

        data = {}

        try:
            # 1. Fetch Stats
            async with self.session.get(stats_url, headers=headers) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Error fetching stats: {resp.status}")
                stats_json = await resp.json()
                
                if stats_json.get("status") == 200 and "result" in stats_json:
                    data.update(stats_json["result"])
                else:
                    _LOGGER.warning("Failed to fetch stats for %s: %s", self.username, stats_json)

            # 2. Fetch Lookup (Location/Rank)
            async with self.session.get(lookup_url, headers=headers) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Error fetching lookup: {resp.status}")
                lookup_json = await resp.json()
                
                if lookup_json.get("status") == 200 and "result" in lookup_json:
                    data.update(lookup_json["result"])
                else:
                    _LOGGER.warning("Failed to fetch lookup for %s: %s", self.username, lookup_json)
            
            return data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
