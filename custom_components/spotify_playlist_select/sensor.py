from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SpotifyCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SpotifyCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([SpotifyPlaybackSensor(hass, entry, coordinator)])


class SpotifyPlaybackSensor(CoordinatorEntity[SpotifyCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Spotify Playback"
    _attr_icon = "mdi:spotify"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: SpotifyCoordinator,
    ) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_playback_sensor"

    @property
    def native_value(self) -> str | None:
        player = self.coordinator.data.player
        if not player:
            return "idle"
        return "playing" if player.get("is_playing") else "paused"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data: dict[str, Any] = {}

        runtime = self.hass.data[DOMAIN][self.entry.entry_id]
        selected_device_id = runtime.get("selected_device_id")
        data["selected_device_id"] = selected_device_id

        devices = self.coordinator.data.devices or []
        data["devices"] = [
            {
                "id": d.id,
                "name": d.name,
                "is_active": d.is_active,
            }
            for d in devices
        ]

        player = self.coordinator.data.player or {}
        if not player:
            data["player_available"] = False
            return data

        data["player_available"] = True
        data["is_playing"] = player.get("is_playing")
        data["shuffle_state"] = player.get("shuffle_state")
        data["repeat_state"] = player.get("repeat_state")
        data["progress_ms"] = player.get("progress_ms")
        data["timestamp"] = player.get("timestamp")

        item = player.get("item") or {}
        data["item_type"] = item.get("type")
        data["track_name"] = item.get("name")
        data["track_uri"] = item.get("uri")
        data["duration_ms"] = item.get("duration_ms")

        artists = item.get("artists") or []
        data["artists"] = [a.get("name") for a in artists if a.get("name")]
        data["artist"] = ", ".join(data["artists"]) if data["artists"] else None

        album = item.get("album") or {}
        data["album_name"] = album.get("name")
        data["album_uri"] = album.get("uri")

        images = album.get("images") or []
        data["image_url"] = images[0].get("url") if images else None
        data["images"] = images 

        ctx = player.get("context") or {}
        data["context_type"] = ctx.get("type")
        data["context_uri"] = ctx.get("uri")

        dev = player.get("device") or {}
        data["active_device_id"] = dev.get("id")
        data["active_device_name"] = dev.get("name")
        data["active_device_type"] = dev.get("type")
        data["active_device_volume_percent"] = dev.get("volume_percent")
        data["active_device_is_active"] = dev.get("is_active")
        data["active_device_is_restricted"] = dev.get("is_restricted")

        playlists = self.coordinator.data.playlists or []
        data["playlists"] = [{"id": p.id, "name": p.name} for p in playlists]

        return data
