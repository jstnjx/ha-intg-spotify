from __future__ import annotations

from typing import Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import SpotifyPlaylist, SpotifyTrack, SpotifyRecentItem
from .coordinator import SpotifyCoordinator
from .device import spotify_device_info
from .const import (
    DOMAIN,
    CONF_PLAY_MODE,
    PLAY_MODE_PLAY,
    PLAY_MODE_QUEUE_PLAY,
    CONF_SELECTED_PLAYLIST_IDS,
)




def _device_label(name: str, device_id: str) -> str:
    return f"{name} [{device_id[:6]}]"


def _dedupe_label(base: str, existing: dict[str, str]) -> str:
    label = base
    if label in existing:
        i = 2
        label = f"{base} ({i})"
        while label in existing:
            i += 1
            label = f"{base} ({i})"
    return label

def _selected_playlist_ids(entry: ConfigEntry) -> set[str]:
    ids = entry.options.get(CONF_SELECTED_PLAYLIST_IDS) or entry.data.get(CONF_SELECTED_PLAYLIST_IDS, [])
    return set(ids or [])


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: SpotifyCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SelectEntity] = [
        SpotifyDeviceSelect(hass, entry, coordinator),
        SpotifyTransferPlaybackSelect(hass, entry, coordinator),
        SpotifyLikedSongsSelect(hass, entry, coordinator),
        SpotifyRecentlyPlayedSelect(hass, entry, coordinator),
        SpotifyAllPlaylistsSelect(hass, entry, coordinator),
    ]

    selected = entry.options.get(CONF_SELECTED_PLAYLIST_IDS) or entry.data.get(CONF_SELECTED_PLAYLIST_IDS, [])
    selected = set(selected or [])

    for pl in coordinator.data.playlists:
        if pl.id not in selected:
            continue
        entities.append(SpotifyPlaylistTrackSelect(hass, entry, coordinator, pl))

    async_add_entities(entities)



class SpotifyDeviceSelect(CoordinatorEntity[SpotifyCoordinator], SelectEntity):
    _attr_name = "Spotify Connect Device"
    _attr_icon = "mdi:speaker"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: SpotifyCoordinator) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_device_select"
        self._current_option: Optional[str] = None

    @property
    def options(self) -> list[str]:
        return [_device_label(d.name, d.id) for d in (self.coordinator.data.devices or [])]

    @property
    def current_option(self) -> str | None:
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        for d in self.coordinator.data.devices:
            if option == _device_label(d.name, d.id):
                self.hass.data[DOMAIN][self.entry.entry_id]["selected_device_id"] = d.id
                self._current_option = option
                self.async_write_ha_state()
                return

    @callback
    def _handle_coordinator_update(self) -> None:
        if self._current_option is None:
            active = next((d for d in self.coordinator.data.devices if d.is_active), None)
            if active:
                self._current_option = _device_label(active.name, active.id)
                self.hass.data[DOMAIN][self.entry.entry_id]["selected_device_id"] = active.id
        super()._handle_coordinator_update()


class SpotifyTransferPlaybackSelect(CoordinatorEntity[SpotifyCoordinator], SelectEntity):
    _attr_name = "Spotify: Transfer Playback"
    _attr_icon = "mdi:cast-audio"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: SpotifyCoordinator) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_transfer_playback_select"
        self._current_option: Optional[str] = None

    @property
    def options(self) -> list[str]:
        return [_device_label(d.name, d.id) for d in (self.coordinator.data.devices or [])]

    @property
    def current_option(self) -> str | None:
        sel = self.hass.data[DOMAIN][self.entry.entry_id].get("selected_device_id")
        if not sel:
            return self._current_option
        d = next((d for d in self.coordinator.data.devices if d.id == sel), None)
        return _device_label(d.name, d.id) if d else self._current_option

    async def async_select_option(self, option: str) -> None:
        device_id: str | None = None
        for d in self.coordinator.data.devices:
            if option == _device_label(d.name, d.id):
                device_id = d.id
                break

        if not device_id:
            return

        oauth = self.hass.data[DOMAIN][self.entry.entry_id]["oauth"]
        await oauth.async_ensure_token_valid()
        api = self.hass.data[DOMAIN][self.entry.entry_id]["api"]
        api.set_token(oauth.token["access_token"])

        await api.transfer_playback(device_id, play=True)

        self.hass.data[DOMAIN][self.entry.entry_id]["selected_device_id"] = device_id
        self._current_option = option
        self.async_write_ha_state()

        await self.coordinator.async_request_refresh()


class SpotifyAllPlaylistsSelect(CoordinatorEntity[SpotifyCoordinator], SelectEntity):
    _attr_icon = "mdi:playlist-play"
    _attr_should_poll = False
    _attr_name = "Spotify: Playlists"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: SpotifyCoordinator) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_all_playlists_select"
        self._current_option: Optional[str] = None
        self._name_to_id: dict[str, str] = {}

    @property
    def options(self) -> list[str]:
        self._name_to_id = {}
        opts: list[str] = []

        selected = _selected_playlist_ids(self.entry)

        for pl in (self.coordinator.data.playlists or []):
            if selected and pl.id not in selected:
                continue

            label = _dedupe_label(pl.name, self._name_to_id)
            self._name_to_id[label] = pl.id
            opts.append(label)

        return opts


    @property
    def current_option(self) -> str | None:
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        self._current_option = option
        self.async_write_ha_state()

        device_id = self.hass.data[DOMAIN][self.entry.entry_id].get("selected_device_id")
        if not device_id:
            return

        playlist_id = self._name_to_id.get(option)
        if not playlist_id:
            return

        oauth = self.hass.data[DOMAIN][self.entry.entry_id]["oauth"]
        await oauth.async_ensure_token_valid()
        api = self.hass.data[DOMAIN][self.entry.entry_id]["api"]
        api.set_token(oauth.token["access_token"])

        await api.start_playlist(device_id, playlist_id)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self):
        return spotify_device_info(self.entry.entry_id)


class SpotifyPlaylistTrackSelect(CoordinatorEntity[SpotifyCoordinator], SelectEntity):
    _attr_icon = "mdi:playlist-music"
    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: SpotifyCoordinator,
        playlist: SpotifyPlaylist,
    ) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry
        self.playlist = playlist

        self._attr_name = f"Spotify: {playlist.name}"
        self._attr_unique_id = f"{entry.entry_id}_playlist_{playlist.id}"
        self._current_option: Optional[str] = None

        self._option_to_uri: dict[str, str] = {}

    @property
    def options(self) -> list[str]:
        tracks = self.coordinator.data.playlist_tracks.get(self.playlist.id, [])
        self._option_to_uri = {}

        opts: list[str] = []
        for t in tracks:
            base = f"{t.name} — {t.artists}"
            label = _dedupe_label(base, self._option_to_uri)
            self._option_to_uri[label] = t.uri
            opts.append(label)

        return opts

    @property
    def current_option(self) -> str | None:
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        self._current_option = option
        self.async_write_ha_state()

        device_id = self.hass.data[DOMAIN][self.entry.entry_id].get("selected_device_id")
        if not device_id:
            return

        uri = self._option_to_uri.get(option)
        if not uri:
            return

        oauth = self.hass.data[DOMAIN][self.entry.entry_id]["oauth"]
        await oauth.async_ensure_token_valid()
        api = self.hass.data[DOMAIN][self.entry.entry_id]["api"]
        api.set_token(oauth.token["access_token"])

        play_mode = self.entry.data.get(CONF_PLAY_MODE, PLAY_MODE_PLAY)

        if play_mode == PLAY_MODE_PLAY:
            await api.start_playlist_at_track(device_id, self.playlist.id, uri)
            await self.coordinator.async_request_refresh()
            return

        if play_mode == PLAY_MODE_QUEUE_PLAY:
            player = self.coordinator.data.player
            if not player:
                await api.start_playlist_at_track(device_id, self.playlist.id, uri)
                await self.coordinator.async_request_refresh()
                return

            await api.start_playlist(device_id, self.playlist.id)
            await api.add_to_queue(device_id, uri)
            await api.next_track(device_id)
            await self.coordinator.async_request_refresh()
            return

    @property
    def device_info(self):
        return spotify_device_info(self.entry.entry_id)


class SpotifyLikedSongsSelect(CoordinatorEntity[SpotifyCoordinator], SelectEntity):
    _attr_name = "Liked Songs"
    _attr_icon = "mdi:heart"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: SpotifyCoordinator) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_liked_songs_select"
        self._current_option: Optional[str] = None
        self._option_to_uri: dict[str, str] = {}

    @property
    def options(self) -> list[str]:
        self._option_to_uri = {}
        opts: list[str] = []

        for t in (self.coordinator.data.saved_tracks or []):
            base = f"{t.name} — {t.artists}"
            label = _dedupe_label(base, self._option_to_uri)
            self._option_to_uri[label] = t.uri
            opts.append(label)

        return opts

    @property
    def current_option(self) -> str | None:
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        self._current_option = option
        self.async_write_ha_state()

        device_id = self.hass.data[DOMAIN][self.entry.entry_id].get("selected_device_id")
        if not device_id:
            return

        uri = self._option_to_uri.get(option)
        if not uri:
            return

        rt = self.hass.data[DOMAIN][self.entry.entry_id]
        oauth = rt["oauth"]
        await oauth.async_ensure_token_valid()
        api = rt["api"]
        api.set_token(oauth.token["access_token"])

        play_mode = self.entry.data.get(CONF_PLAY_MODE, PLAY_MODE_PLAY)

        if play_mode == PLAY_MODE_PLAY:
            await api.start_playback(device_id, uri)
        else:
            player = self.coordinator.data.player
            if not player:
                await api.start_playback(device_id, uri)
            else:
                await api.add_to_queue(device_id, uri)
                await api.next_track(device_id)

        await self.coordinator.async_request_refresh()

    @property
    def device_info(self):
        return spotify_device_info(self.entry.entry_id)

class SpotifyRecentlyPlayedSelect(CoordinatorEntity[SpotifyCoordinator], SelectEntity):
    _attr_name = "Recently Played"
    _attr_icon = "mdi:history"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: SpotifyCoordinator) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_recently_played_select"
        self._current_option: Optional[str] = None
        self._option_to_uri: dict[str, str] = {}

    @property
    def options(self) -> list[str]:
        self._option_to_uri = {}
        opts: list[str] = []

        for r in (self.coordinator.data.recent_tracks or []):
            base = f"{r.name} — {r.artists}"
            label = _dedupe_label(base, self._option_to_uri)
            self._option_to_uri[label] = r.uri
            opts.append(label)

        return opts

    @property
    def current_option(self) -> str | None:
        return self._current_option

    async def async_select_option(self, option: str) -> None:
        self._current_option = option
        self.async_write_ha_state()

        device_id = self.hass.data[DOMAIN][self.entry.entry_id].get("selected_device_id")
        if not device_id:
            return

        uri = self._option_to_uri.get(option)
        if not uri:
            return

        rt = self.hass.data[DOMAIN][self.entry.entry_id]
        oauth = rt["oauth"]
        await oauth.async_ensure_token_valid()
        api = rt["api"]
        api.set_token(oauth.token["access_token"])

        play_mode = self.entry.data.get(CONF_PLAY_MODE, PLAY_MODE_PLAY)

        if play_mode == PLAY_MODE_PLAY:
            await api.start_playback(device_id, uri)
        else:
            player = self.coordinator.data.player
            if not player:
                await api.start_playback(device_id, uri)
            else:
                await api.add_to_queue(device_id, uri)
                await api.next_track(device_id)

        await self.coordinator.async_request_refresh()

    @property
    def device_info(self):
        return spotify_device_info(self.entry.entry_id)