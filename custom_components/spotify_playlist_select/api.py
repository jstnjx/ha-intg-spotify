from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp


class SpotifyApiError(Exception):
    pass


@dataclass(frozen=True)
class SpotifyPlaylist:
    id: str
    name: str


@dataclass(frozen=True)
class SpotifyTrack:
    uri: str
    name: str
    artists: str


@dataclass(frozen=True)
class SpotifyDevice:
    id: str
    name: str
    is_active: bool


class SpotifyApi:
    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        self._session = session
        self._token = token

    def set_token(self, token: str) -> None:
        self._token = token

    async def _request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token}"
        headers["Content-Type"] = "application/json"
        async with self._session.request(method, url, headers=headers, **kwargs) as resp:
            if resp.status >= 400:
                txt = await resp.text()
                raise SpotifyApiError(f"{resp.status} {txt}")
            if resp.status == 204:
                return {}
            return await resp.json()

    async def get_playlists(self) -> list[SpotifyPlaylist]:
        url = "https://api.spotify.com/v1/me/playlists?limit=50"
        out: list[SpotifyPlaylist] = []
        while url:
            data = await self._request("GET", url)
            for it in data.get("items", []):
                out.append(SpotifyPlaylist(id=it["id"], name=it["name"]))
            url = data.get("next")
        return out

    async def get_playlist_tracks(self, playlist_id: str) -> list[SpotifyTrack]:
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=100"
        out: list[SpotifyTrack] = []
        while url:
            data = await self._request("GET", url)
            for item in data.get("items", []):
                t = item.get("track") or {}
                uri = t.get("uri")
                if not uri:
                    continue
                name = t.get("name", "Unknown")
                artists = ", ".join(a.get("name", "") for a in (t.get("artists") or [])) or "Unknown"
                out.append(SpotifyTrack(uri=uri, name=name, artists=artists))
            url = data.get("next")
        return out

    async def get_devices(self) -> list[SpotifyDevice]:
        data = await self._request("GET", "https://api.spotify.com/v1/me/player/devices")
        return [
            SpotifyDevice(
                id=d["id"],
                name=d["name"],
                is_active=d.get("is_active", False),
            )
            for d in data.get("devices", [])
            if d.get("id")
        ]

    async def start_playback(self, device_id: str, track_uri: str) -> None:
        await self._request(
            "PUT",
            f"https://api.spotify.com/v1/me/player/play?device_id={device_id}",
            json={"uris": [track_uri]},
        )

    async def add_to_queue(self, device_id: str, track_uri: str) -> None:
        await self._request(
            "POST",
            "https://api.spotify.com/v1/me/player/queue",
            params={"uri": track_uri, "device_id": device_id},
        )

    async def get_currently_playing(self) -> dict[str, Any]:
        return await self._request("GET", "https://api.spotify.com/v1/me/player")
