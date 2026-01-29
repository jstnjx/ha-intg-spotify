from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .const import (
    DOMAIN,
    CONF_PLAY_MODE,
    PLAY_MODE_PLAY,
    PLAY_MODE_QUEUE_PLAY,
    SPOTIFY_SCOPES,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Config flow for Spotify Playlist Select using Application Credentials OAuth2."""

    DOMAIN = DOMAIN
    VERSION = 1
    
    def __init__(self) -> None:
        self._pending: dict[str, Any] = {}

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    @property
    def scopes(self) -> list[str]:
        return SPOTIFY_SCOPES

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        return {"scope": " ".join(self.scopes)}


    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        await self.async_set_unique_id("single_account")
        self._abort_if_unique_id_configured()

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_PLAY_MODE, default=PLAY_MODE_PLAY): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {"label": "playlist select -> song plays", "value": PLAY_MODE_PLAY},
                                {"label": "playlist select -> queue + play", "value": PLAY_MODE_QUEUE_PLAY},
                            ],
                            mode="dropdown",
                        )
                    ),
                }
            )
            return self.async_show_form(step_id="user", data_schema=schema)

        self._pending = {CONF_PLAY_MODE: user_input[CONF_PLAY_MODE]}

        return await self.async_step_pick_implementation()

    async def async_step_pick_implementation(self, user_input: dict[str, Any] | None = None):
        return await super().async_step_pick_implementation(user_input)

    async def async_step_auth(self, user_input: dict[str, Any] | None = None):
        self.logger.debug("OAuth scopes requested: %s", self.scopes)
        return await super().async_step_auth(user_input)

    async def async_oauth_create_entry(self, data: dict[str, Any]):
        entry_data = {**self._pending, **data}
        return self.async_create_entry(title="Spotify Playlist Select", data=entry_data)
