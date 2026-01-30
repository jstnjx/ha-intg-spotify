from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN
from .coordinator import SpotifyCoordinator


SERVICE_PLAY_PLAYLIST = "play_playlist"
SERVICE_PLAY_TRACK_IN_PLAYLIST = "play_track_in_playlist"
SERVICE_QUEUE_TRACK = "queue_track"
SERVICE_REFRESH_LIBRARY = "refresh_library"

ATTR_PLAYLIST_ID = "playlist_id"
ATTR_PLAYLIST_NAME = "playlist_name"
ATTR_TRACK_URI = "track_uri"
ATTR_DEVICE_ID = "device_id"
ATTR_PLAY_NOW = "play_now"


def _get_single_entry_id(hass: HomeAssistant) -> str:
    entries = list(hass.data.get(DOMAIN, {}).keys())
    if not entries:
        raise ValueError("Integration not set up")

    return entries[0]


async def _get_api_and_oauth(hass: HomeAssistant):
    entry_id = _get_single_entry_id(hass)
    rt = hass.data[DOMAIN][entry_id]
    oauth: config_entry_oauth2_flow.OAuth2Session = rt["oauth"]
    api = rt["api"]
    coordinator: SpotifyCoordinator = rt["coordinator"]
    return entry_id, rt, oauth, api, coordinator


async def async_setup_services(hass: HomeAssistant) -> None:
    async def handle_play_playlist(call: ServiceCall) -> None:
        _, rt, oauth, api, coordinator = await _get_api_and_oauth(hass)

        playlist_id = call.data.get(ATTR_PLAYLIST_ID)
        playlist_name = call.data.get(ATTR_PLAYLIST_NAME)
        device_id = call.data.get(ATTR_DEVICE_ID) or rt.get("selected_device_id")

        if not device_id:
            raise vol.Invalid("No device_id provided and no selected_device_id set")

        if not playlist_id and not playlist_name:
            raise vol.Invalid("Provide playlist_id or playlist_name")

        if not playlist_id and playlist_name:
            pl = next((p for p in coordinator.data.playlists if p.name == playlist_name), None)
            if not pl:
                raise vol.Invalid(f"Playlist not found by name: {playlist_name}")
            playlist_id = pl.id

        await oauth.async_ensure_token_valid()
        api.set_token(oauth.token["access_token"])

        await api.start_playlist(device_id, playlist_id)
        await coordinator.async_request_refresh()

    async def handle_play_track_in_playlist(call: ServiceCall) -> None:
        _, rt, oauth, api, coordinator = await _get_api_and_oauth(hass)

        playlist_id = call.data[ATTR_PLAYLIST_ID]
        track_uri = call.data[ATTR_TRACK_URI]
        device_id = call.data.get(ATTR_DEVICE_ID) or rt.get("selected_device_id")

        if not device_id:
            raise vol.Invalid("No device_id provided and no selected_device_id set")

        await oauth.async_ensure_token_valid()
        api.set_token(oauth.token["access_token"])

        await api.start_playlist_at_track(device_id, playlist_id, track_uri)
        await coordinator.async_request_refresh()

    async def handle_queue_track(call: ServiceCall) -> None:
        _, rt, oauth, api, coordinator = await _get_api_and_oauth(hass)

        track_uri = call.data[ATTR_TRACK_URI]
        device_id = call.data.get(ATTR_DEVICE_ID) or rt.get("selected_device_id")
        play_now = call.data.get(ATTR_PLAY_NOW, False)

        if not device_id:
            raise vol.Invalid("No device_id provided and no selected_device_id set")

        await oauth.async_ensure_token_valid()
        api.set_token(oauth.token["access_token"])

        player = coordinator.data.player

        if not player:
            await api.start_playback(device_id, track_uri)
            await coordinator.async_request_refresh()
            return

        await api.add_to_queue(device_id, track_uri)

        if play_now:
            await api.next_track(device_id)

        await coordinator.async_request_refresh()

    async def handle_refresh_library(call: ServiceCall) -> None:
        _, _, _, _, coordinator = await _get_api_and_oauth(hass)
        await coordinator.async_refresh_library()

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_PLAYLIST,
        handle_play_playlist,
        schema=vol.Schema(
            {
                vol.Optional(ATTR_PLAYLIST_ID): cv.string,
                vol.Optional(ATTR_PLAYLIST_NAME): cv.string,
                vol.Optional(ATTR_DEVICE_ID): cv.string,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_TRACK_IN_PLAYLIST,
        handle_play_track_in_playlist,
        schema=vol.Schema(
            {
                vol.Required(ATTR_PLAYLIST_ID): cv.string,
                vol.Required(ATTR_TRACK_URI): cv.string,
                vol.Optional(ATTR_DEVICE_ID): cv.string,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_QUEUE_TRACK,
        handle_queue_track,
        schema=vol.Schema(
            {
                vol.Required(ATTR_TRACK_URI): cv.string,
                vol.Optional(ATTR_DEVICE_ID): cv.string,
                vol.Optional(ATTR_PLAY_NOW, default=False): cv.boolean,
            }
        ),
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_LIBRARY,
        handle_refresh_library,
        schema=vol.Schema({}),
    )
