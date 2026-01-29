from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.media_player import MediaPlayerEntity, MediaPlayerEntityFeature
from homeassistant.components.media_player.const import RepeatMode
from homeassistant.components.media_player.const import MediaPlayerState
from homeassistant.components.media_player.const import MediaType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from homeassistant.exceptions import HomeAssistantError
from time import monotonic



from .const import DOMAIN
from .coordinator import SpotifyCoordinator


def _device_label(name: str, device_id: str) -> str:
    return f"{name} [{device_id[:6]}]"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SpotifyCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([SpotifyPlaylistMediaPlayer(hass, entry, coordinator)])


class SpotifyPlaylistMediaPlayer(CoordinatorEntity[SpotifyCoordinator], MediaPlayerEntity):
    _attr_icon = "mdi:spotify"
    _attr_has_entity_name = True
    _attr_name = "Spotify Player"

    _attr_supported_features = (
        MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.NEXT_TRACK
        | MediaPlayerEntityFeature.PREVIOUS_TRACK
        | MediaPlayerEntityFeature.SHUFFLE_SET
        | MediaPlayerEntityFeature.REPEAT_SET
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    )

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: SpotifyCoordinator) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_media_player"
        self._last_command_ts: float = 0.0
        self._debounce_seconds: float = 0.5

    def _debounce(self) -> None:
        now = monotonic()
        if now - self._last_command_ts < self._debounce_seconds:
            raise HomeAssistantError("Command ignored (debounced)")
        self._last_command_ts = now



    def _runtime(self) -> dict[str, Any]:
        return self.hass.data[DOMAIN][self.entry.entry_id]

    def _selected_device_id(self) -> Optional[str]:
        return self._runtime().get("selected_device_id")

    async def _refresh_token(self) -> None:
        oauth = self._runtime()["oauth"]
        await oauth.async_ensure_token_valid()
        api = self._runtime()["api"]
        api.set_token(oauth.token["access_token"])

    @property
    def sound_mode_list(self) -> list[str] | None:
        return [_device_label(d.name, d.id) for d in (self.coordinator.data.devices or [])]

    @property
    def sound_mode(self) -> str | None:
        sel = self._selected_device_id()
        if not sel:
            return None
        d = next((d for d in self.coordinator.data.devices if d.id == sel), None)
        return _device_label(d.name, d.id) if d else None

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        if not self._debounce():
            return
        for d in self.coordinator.data.devices:
            if sound_mode == _device_label(d.name, d.id):
                self._runtime()["selected_device_id"] = d.id
                self.async_write_ha_state()
                return

    @property
    def source_list(self) -> list[str] | None:
        return [p.name for p in (self.coordinator.data.playlists or [])]

    @property
    def source(self) -> str | None:
        player = self.coordinator.data.player or {}
        ctx = (player.get("context") or {})
        if ctx.get("type") != "playlist":
            return None
        uri = ctx.get("uri")  
        if not uri:
            return None
        playlist_id = uri.split(":")[-1]
        pl = next((p for p in self.coordinator.data.playlists if p.id == playlist_id), None)
        return pl.name if pl else None

    async def async_select_source(self, source: str) -> None:
        if not self._debounce():
            return
        device_id = self._selected_device_id()
        if not device_id:
            return

        pl = next((p for p in self.coordinator.data.playlists if p.name == source), None)
        if not pl:
            return

        await self._refresh_token()
        api = self._runtime()["api"]
        await api.start_playlist(device_id, pl.id)
        await self.coordinator.async_request_refresh()

    @property
    def state(self) -> MediaPlayerState | None:
        player = self.coordinator.data.player
        if not player:
            return None
        return MediaPlayerState.PLAYING if player.get("is_playing") else MediaPlayerState.PAUSED

    @property
    def media_title(self) -> str | None:
        item = (self.coordinator.data.player or {}).get("item") or {}
        return item.get("name")

    @property
    def media_artist(self) -> str | None:
        item = (self.coordinator.data.player or {}).get("item") or {}
        artists = item.get("artists") or []
        if not artists:
            return None
        return ", ".join(a.get("name", "") for a in artists if a.get("name"))

    @property
    def media_album_name(self) -> str | None:
        item = (self.coordinator.data.player or {}).get("item") or {}
        album = item.get("album") or {}
        return album.get("name")

    @property
    def media_image_url(self) -> str | None:
        item = (self.coordinator.data.player or {}).get("item") or {}
        album = item.get("album") or {}
        images = album.get("images") or []
        return images[0].get("url") if images else None

    @property
    def media_content_type(self) -> str | None:
        player = self.coordinator.data.player or {}
        item = player.get("item") or {}
        if item.get("type") == "episode":
            return MediaType.PODCAST
        if item.get("type") == "track":
            return MediaType.MUSIC
        return None

    @property
    def media_duration(self) -> int | None:
        item = (self.coordinator.data.player or {}).get("item") or {}
        dur_ms = item.get("duration_ms")
        return int(dur_ms / 1000) if dur_ms else None

    @property
    def media_position(self) -> int | None:
        prog_ms = (self.coordinator.data.player or {}).get("progress_ms")
        return int(prog_ms / 1000) if prog_ms is not None else None

    @property
    def media_position_updated_at(self):
        if self.media_position is None:
            return None
        return dt_util.utcnow()


    @property
    def shuffle(self) -> bool | None:
        player = self.coordinator.data.player or {}
        if not player:
            return None
        return bool(player.get("shuffle_state"))

    @property
    def repeat(self) -> RepeatMode | None:
        rep = (self.coordinator.data.player or {}).get("repeat_state")
        if rep == "track":
            return RepeatMode.ONE
        if rep == "context":
            return RepeatMode.ALL
        if rep == "off":
            return RepeatMode.OFF
        return None

    async def async_media_play(self) -> None:
        if not self._debounce():
            return
        device_id = self._selected_device_id()
        await self._refresh_token()
        api = self._runtime()["api"]
        await api.resume(device_id)
        await self.coordinator.async_request_refresh()

    async def async_media_pause(self) -> None:
        if not self._debounce():
            return
        device_id = self._selected_device_id()
        await self._refresh_token()
        api = self._runtime()["api"]
        await api.pause(device_id)
        await self.coordinator.async_request_refresh()

    async def async_media_next_track(self) -> None:
        if not self._debounce():
            return
        device_id = self._selected_device_id()
        await self._refresh_token()
        api = self._runtime()["api"]
        await api.next_track(device_id)
        await self.coordinator.async_request_refresh()

    async def async_media_previous_track(self) -> None:
        if not self._debounce():
            return
        device_id = self._selected_device_id()
        await self._refresh_token()
        api = self._runtime()["api"]
        await api.previous_track(device_id)
        await self.coordinator.async_request_refresh()

    async def async_set_shuffle(self, shuffle: bool) -> None:
        if not self._debounce():
            return
        device_id = self._selected_device_id()
        await self._refresh_token()
        api = self._runtime()["api"]
        await api.set_shuffle(shuffle, device_id)
        await self.coordinator.async_request_refresh()

    async def async_set_repeat(self, repeat: RepeatMode) -> None:
        if not self._debounce():
            return
        device_id = self._selected_device_id()
        await self._refresh_token()
        api = self._runtime()["api"]

        if repeat == RepeatMode.ONE:
            state = "track"
        elif repeat == RepeatMode.ALL:
            state = "context"
        else:
            state = "off"

        await api.set_repeat(state, device_id)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        rt = self._runtime()
        if rt.get("selected_device_id") is None:
            active = next((d for d in self.coordinator.data.devices if d.is_active), None)
            if active:
                rt["selected_device_id"] = active.id
        super()._handle_coordinator_update()
