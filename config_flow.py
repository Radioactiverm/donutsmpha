import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("api_key"): str,
    }
)

API_LOOKUP_URL = "https://api.donutsmp.net/v1/lookup/{0}"
API_STATS_URL = "https://api.donutsmp.net/v1/stats/{0}"


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect."""

    username = data["username"].strip()
    raw_api_key = data["api_key"].strip()

    headers = {
        "X-API-Key": raw_api_key
    }

    test_url = API_LOOKUP_URL.format(username)
    session = aiohttp_client.async_get_clientsession(hass)

    try:
        async with session.get(test_url, headers=headers, timeout=10) as response:
            if response.status == 404:
                _LOGGER.warning("User not found: %s", username)
                raise InvalidAuth("user_not_found")
            elif response.status == 401:
                raise InvalidAuth("invalid_api_key")
            response.raise_for_status()
            data = await response.json()
            if not data or not data.get("uuid"):
                raise InvalidAuth("user_not_found")
    except Exception as err:
        _LOGGER.error("Error connecting to API: %s", err)
        raise CannotConnect from err

    # Return info that you want to store in the config entry.
    # Storing lookup and stats URLs for later use
    return {
        "title": f"Donut SMP: {username}",
        "username": username,
        "api_key": raw_api_key,
        "uuid": data.get("uuid", "unknown"),
        "lookup_url": test_url,
        "stats_url": API_STATS_URL.format(username),
    }


class DonutsmphaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Donuts SMP HA."""

    VERSION = 1

    def __init__(self):
        self.data: Optional[Dict[str, Any]] = None

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        errors = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"

            if not errors:
                # Save info for later use!
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        "username": info["username"],
                        "api_key": info["api_key"],
                        "uuid": info["uuid"],
                        "lookup_url": info["lookup_url"],
                        "stats_url": info["stats_url"],
                    }
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
