from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .api import SpotifyApi
from .const import (
    DOMAIN,
    CONF_PLAY_MODE,
    PLAY_MODE_PLAY,
    PLAY_MODE_QUEUE_PLAY,
    SPOTIFY_SCOPES,
    CONF_SELECTED_PLAYLIST_IDS,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):

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
                    )
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
        self._pending.update(data)
        return await self.async_step_playlists()

    async def async_step_playlists(self, user_input: dict[str, Any] | None = None):
        session = async_get_clientsession(self.hass)

        token = self._pending.get("token", {})
        access_token = token.get("access_token")
        if not access_token:
            return self.async_abort(reason="oauth_error")

        api = SpotifyApi(session, access_token)
        playlists = await api.get_playlists()

        pl_options = [{"label": p.name, "value": p.id} for p in playlists]

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_SELECTED_PLAYLIST_IDS, default=[]): SelectSelector(
                        SelectSelectorConfig(
                            options=pl_options,
                            multiple=True,
                            mode="list",
                        )
                    )
                }
            )
            return self.async_show_form(step_id="playlists", data_schema=schema)

        selected_ids = user_input[CONF_SELECTED_PLAYLIST_IDS]
        self._pending[CONF_SELECTED_PLAYLIST_IDS] = selected_ids
        return self.async_create_entry(title="Spotify Playlist Select", data=self._pending)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return OptionsFlowHandler(config_entry)



class OptionsFlowHandler(config_entries.OptionsFlow):

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        session = async_get_clientsession(self.hass)

        implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
            self.hass, self.entry
        )
        oauth = config_entry_oauth2_flow.OAuth2Session(self.hass, self.entry, implementation)
        await oauth.async_ensure_token_valid()

        api = SpotifyApi(session, oauth.token["access_token"])
        playlists = await api.get_playlists()
        pl_options = [{"label": p.name, "value": p.id} for p in playlists]

        current = self.entry.options.get(CONF_SELECTED_PLAYLIST_IDS) or self.entry.data.get(CONF_SELECTED_PLAYLIST_IDS, [])

        if user_input is None:
            schema = vol.Schema(
                {
                    vol.Required(CONF_SELECTED_PLAYLIST_IDS, default=current): SelectSelector(
                        SelectSelectorConfig(
                            options=pl_options,
                            multiple=True,
                            mode="list",
                        )
                    )
                }
            )
            return self.async_show_form(step_id="init", data_schema=schema)

        return self.async_create_entry(title="", data=user_input)



