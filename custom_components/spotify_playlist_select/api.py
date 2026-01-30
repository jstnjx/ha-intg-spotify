from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp


class SpotifyApiError(Exception):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"{status} {body}")
        self.status = status
        self.body = body



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


@dataclass(frozen=True)
class SpotifyRecentItem:
    uri: str
    name: str
    artists: str
    played_at: str | None


class SpotifyApi:
    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        self._session = session
        self._token = token

    def set_token(self, token: str) -> None:
        self._token = token

    async def _request(self, method: str, url: str, **kwargs) -> dict[str, Any]:
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self._token}"

        if "json" in kwargs:
            headers["Content-Type"] = "application/json"

        if "params" in kwargs and kwargs["params"] is None:
            kwargs.pop("params")

        async with self._session.request(method, url, headers=headers, **kwargs) as resp:
            if resp.status == 204:
                return {}

            if resp.status >= 400:
                txt = await resp.text()
                raise SpotifyApiError(resp.status, txt)

            ctype = resp.headers.get("Content-Type", "")
            if "application/json" not in ctype.lower():
                await resp.read()
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

    async def get_playlist_tracks(self, playlist_id: str, limit_total: int = 128) -> list[SpotifyTrack]:
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?limit=100"
        out: list[SpotifyTrack] = []

        while url and len(out) < limit_total:
            data = await self._request("GET", url)
            for item in data.get("items", []):
                t = item.get("track") or {}
                uri = t.get("uri")
                if not uri:
                    continue
                name = t.get("name", "Unknown")
                artists = ", ".join(a.get("name", "") for a in (t.get("artists") or [])) or "Unknown"
                out.append(SpotifyTrack(uri=uri, name=name, artists=artists))
                if len(out) >= limit_total:
                    break
            url = data.get("next")

        return out

    async def get_saved_tracks(self, limit: int = 50) -> list[SpotifyTrack]:
        url = "https://api.spotify.com/v1/me/tracks?limit=50"
        out: list[SpotifyTrack] = []

        while url and len(out) < limit:
            data = await self._request("GET", url)
            for item in data.get("items", []):
                t = (item or {}).get("track") or {}
                uri = t.get("uri")
                if not uri:
                    continue
                name = t.get("name", "Unknown")
                artists = ", ".join(a.get("name", "") for a in (t.get("artists") or [])) or "Unknown"
                out.append(SpotifyTrack(uri=uri, name=name, artists=artists))
                if len(out) >= limit:
                    break
            url = data.get("next")

        return out

    async def get_recently_played(self, limit: int = 50) -> list[SpotifyRecentItem]:
        url = f"https://api.spotify.com/v1/me/player/recently-played?limit={min(limit, 50)}"
        out: list[SpotifyRecentItem] = []

        data = await self._request("GET", url)
        for item in data.get("items", []):
            t = (item or {}).get("track") or {}
            uri = t.get("uri")
            if not uri:
                continue
            name = t.get("name", "Unknown")
            artists = ", ".join(a.get("name", "") for a in (t.get("artists") or [])) or "Unknown"
            out.append(
                SpotifyRecentItem(
                    uri=uri,
                    name=name,
                    artists=artists,
                    played_at=item.get("played_at"),
                )
            )

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

    async def get_player(self) -> dict[str, Any]:
        return await self._request("GET", "https://api.spotify.com/v1/me/player")

    async def pause(self, device_id: str | None = None) -> None:
        await self._request(
            "PUT",
            "https://api.spotify.com/v1/me/player/pause",
            params={"device_id": device_id} if device_id else None,
        )

    async def resume(self, device_id: str | None = None) -> None:
        await self._request(
            "PUT",
            "https://api.spotify.com/v1/me/player/play",
            params={"device_id": device_id} if device_id else None,
        )

    async def next_track(self, device_id: str | None = None) -> None:
        await self._request(
            "POST",
            "https://api.spotify.com/v1/me/player/next",
            params={"device_id": device_id} if device_id else None,
        )

    async def previous_track(self, device_id: str | None = None) -> None:
        await self._request(
            "POST",
            "https://api.spotify.com/v1/me/player/previous",
            params={"device_id": device_id} if device_id else None,
        )

    async def set_shuffle(self, shuffle: bool, device_id: str | None = None) -> None:
        await self._request(
            "PUT",
            "https://api.spotify.com/v1/me/player/shuffle",
            params={"state": "true" if shuffle else "false", **({"device_id": device_id} if device_id else {})},
        )

    async def set_repeat(self, state: str, device_id: str | None = None) -> None:
        await self._request(
            "PUT",
            "https://api.spotify.com/v1/me/player/repeat",
            params={"state": state, **({"device_id": device_id} if device_id else {})},
        )

    async def start_playlist(self, device_id: str, playlist_id: str) -> None:
        await self._request(
            "PUT",
            "https://api.spotify.com/v1/me/player/play",
            params={"device_id": device_id},
            json={"context_uri": f"spotify:playlist:{playlist_id}"},
        )

    async def start_playlist_at_track(self, device_id: str, playlist_id: str, track_uri: str) -> None:
        await self._request(
            "PUT",
            "https://api.spotify.com/v1/me/player/play",
            params={"device_id": device_id},
            json={
                "context_uri": f"spotify:playlist:{playlist_id}",
                "offset": {"uri": track_uri},
            },
        )

    async def transfer_playback(self, device_id: str, play: bool = True) -> None:
        await self._request(
            "PUT",
            "https://api.spotify.com/v1/me/player",
            json={"device_ids": [device_id], "play": play},
        )

