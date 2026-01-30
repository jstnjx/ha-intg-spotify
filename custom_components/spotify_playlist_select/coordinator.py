from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers import config_entry_oauth2_flow

from .api import SpotifyApi, SpotifyDevice, SpotifyPlaylist, SpotifyTrack, SpotifyRecentItem
from .const import TRACK_LIMIT_PER_PLAYLIST, SAVED_TRACKS_LIMIT, RECENTLY_PLAYED_LIMIT


@dataclass
class SpotifyData:
    devices: list[SpotifyDevice]
    playlists: list[SpotifyPlaylist]
    saved_tracks: list[SpotifyTrack]
    recent_tracks: list[SpotifyRecentItem]
    playlist_tracks: dict[str, list[SpotifyTrack]]
    player: dict[str, Any] | None


class SpotifyCoordinator(DataUpdateCoordinator[SpotifyData]):
    def __init__(
        self,
        hass: HomeAssistant,
        api: SpotifyApi,
        oauth: config_entry_oauth2_flow.OAuth2Session,
    ) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name="Spotify Playlist Select",
            update_interval=timedelta(seconds=15),
        )
        self.api = api
        self.oauth = oauth
        self._static_loaded = False

    async def _async_update_data(self) -> SpotifyData:
        try:
            await self.oauth.async_ensure_token_valid()
            self.api.set_token(self.oauth.token["access_token"])

            if not self._static_loaded:
                playlists = await self.api.get_playlists()
                playlist_tracks: dict[str, list[SpotifyTrack]] = {}
                for pl in playlists:
                    playlist_tracks[pl.id] = await self.api.get_playlist_tracks(
                        pl.id, limit_total=TRACK_LIMIT_PER_PLAYLIST
                    )
                self._static_loaded = True
            else:
                playlists = self.data.playlists if self.data else []
                playlist_tracks = self.data.playlist_tracks if self.data else {}

            devices = await self.api.get_devices()

            player_data = await self.api.get_player()
            player = player_data if player_data else None

            try:
                saved_tracks = await self.api.get_saved_tracks(limit=SAVED_TRACKS_LIMIT)
            except Exception:
                saved_tracks = []

            try:
                recent_tracks = await self.api.get_recently_played(limit=RECENTLY_PLAYED_LIMIT)
            except Exception:
                recent_tracks = []

            return SpotifyData(
                devices=devices,
                playlists=playlists,
                saved_tracks=saved_tracks,
                recent_tracks=recent_tracks,
                playlist_tracks=playlist_tracks,
                player=player,
            )

        except Exception as err:
            raise UpdateFailed(str(err)) from err

    async def async_refresh_library(self) -> None:
        self._static_loaded = False
        await self.async_request_refresh()
