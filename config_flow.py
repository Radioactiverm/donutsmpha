"""Config flow for Donut SMP integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import API_LOOKUP_URL, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Optional("api_key"): str,
    }
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    username = data["username"]
    api_key = data.get("api_key")

    headers = {}
    if api_key and api_key.lower() != "none":
        # Using the standard custom API key header (X-API-Key) instead of Authorization
        headers["X-API-Key"] = api_key

    # Test the credentials by making a request to the lookup endpoint
    test_url = API_LOOKUP_URL.format(username)
    
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(test_url) as response:
                
                # The API returns 404 if the user is not found, or possibly 401 if the key is bad.
                if response.status == 404:
                    _LOGGER.warning("User not found: %s", username)
                    raise InvalidAuth("user_not_found")
                
                response.raise_for_status() # Raises for 4xx/5xx status codes (e.g., 401 Unauthorized)

                data = await response.json()
                
                # If the API returns 200 but the data structure is unexpected (e.g., missing expected fields)
                if not data or not data.get("uuid"):
                    raise InvalidAuth("user_not_found") 

    except aiohttp.ClientConnectorError as err:
        _LOGGER.error("Connection error: %s", err)
        raise CannotConnect from err
    except aiohttp.ClientResponseError as err:
        _LOGGER.error("API response error (status %s) for user %s: %s", err.status, username, err)
        if err.status == 401:
            raise InvalidAuth("invalid_api_key")
        if err.status == 404:
            # Although handled above, this catches it if raise_for_status is triggered first
            raise InvalidAuth("user_not_found")
        raise InvalidAuth("unknown_api_error") from err
    except InvalidAuth:
        # Re-raise explicit InvalidAuth exceptions (like user_not_found, invalid_api_key)
        raise
    except Exception as err:
        _LOGGER.error("An unexpected error occurred during validation: %s", err)
        raise InvalidAuth("unknown_api_error") from err

    # Return info that you want to store in the config entry.
    return {"title": f"Donut SMP: {username}", "uuid": data["uuid"]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Donut SMP."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth as e:
                errors["base"] = str(e)
            except Exception: # Catch other unknown errors during validation
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Prevent duplicate entries for the same username
                await self.async_set_unique_id(info["uuid"])
                self.async_abort_if_unique_id_configured()
                
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""
