from __future__ import annotations

from typing import Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_PLAY_MODE, PLAY_MODE_PLAY, PLAY_MODE_QUEUE_PLAY
from .coordinator import SpotifyCoordinator
from .api import SpotifyPlaylist


def _device_label(name: str, device_id: str) -> str:
    return f"{name} [{device_id[:6]}]"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SpotifyCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SelectEntity] = [SpotifyDeviceSelect(hass, entry, coordinator)]

    for pl in coordinator.data.playlists:
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
            label = base
            if label in self._option_to_uri:
                i = 2
                label = f"{base} ({i})"
                while label in self._option_to_uri:
                    i += 1
                    label = f"{base} ({i})"
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
            await api.start_playback(device_id, uri)
            return

        if play_mode == PLAY_MODE_QUEUE_PLAY:
            await api.add_to_queue(device_id, uri)
            await api.start_playback(device_id, uri)
            return
