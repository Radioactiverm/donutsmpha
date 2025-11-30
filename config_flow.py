"""Config flow for Donut SMP integration."""
from __future__ import annotations

import logging
import voluptuous as vol
import aiohttp

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, API_STATS_URL

_LOGGER = logging.getLogger(__name__)

class DonutSMPConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Donut SMP."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            api_key = user_input[CONF_API_KEY]

            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            # Validate the user exists by making a test API call
            valid = await self._test_credentials(username, api_key)
            if valid:
                return self.async_create_entry(
                    title=username,
                    data=user_input,
                )
            else:
                errors["base"] = "user_not_found"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(CONF_USERNAME): str,
                }
            ),
            errors=errors,
        )

    async def _test_credentials(self, username: str, api_key: str) -> bool:
        """Validate credentials."""
        session = async_get_clientsession(self.hass)
        url = API_STATS_URL.format(username)
        headers = {"User-Agent": "Home Assistant DonutSMP Integration"}
        
        # Pass API key if relevant, though stats are often public
        if api_key:
             headers["Authorization"] = api_key

        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return False
                data = await response.json()
                # Check if result contains data (API usually returns status 200 even on some logic errors)
                if data.get("status") != 200:
                    return False
                return True
        except Exception:  # pylint: disable=broad-except
            return False
