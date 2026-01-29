from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SpotifyApi, SpotifyDevice, SpotifyPlaylist, SpotifyTrack


@dataclass
class SpotifyData:
    devices: list[SpotifyDevice]
    playlists: list[SpotifyPlaylist]
    playlist_tracks: dict[str, list[SpotifyTrack]]


class SpotifyCoordinator(DataUpdateCoordinator[SpotifyData]):
    def __init__(self, hass: HomeAssistant, api: SpotifyApi) -> None:
        super().__init__(
            hass,
            logger=__import__("logging").getLogger(__name__),
            name="Spotify Playlist Select",
            update_interval=timedelta(seconds=15),
        )
        self.api = api
        self._static_loaded = False

    async def _async_update_data(self) -> SpotifyData:
        try:
            if not self._static_loaded:
                playlists = await self.api.get_playlists()
                playlist_tracks: dict[str, list[SpotifyTrack]] = {}
                for pl in playlists:
                    playlist_tracks[pl.id] = await self.api.get_playlist_tracks(pl.id)
                self._static_loaded = True
            else:
                playlists = self.data.playlists if self.data else []
                playlist_tracks = self.data.playlist_tracks if self.data else {}

            devices = await self.api.get_devices()
            return SpotifyData(devices=devices, playlists=playlists, playlist_tracks=playlist_tracks)
        except Exception as err:
            raise UpdateFailed(str(err)) from err
