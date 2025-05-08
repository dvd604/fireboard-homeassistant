"""Config flow for the fireboard integration."""

from __future__ import annotations

import logging

from fireboard_cloud_api_client import FireboardAPI
import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


class FireBoardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # Could call FireBoard API to validate token
            fb_client = FireboardAPI(user_input["email"], user_input["password"])
            logging.getLogger("fireboard").info(fb_client)
            return self.async_create_entry(title=DOMAIN, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required("email"): str, vol.Required("password"): str}
            ),
        )
