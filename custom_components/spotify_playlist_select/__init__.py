from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SpotifyApi
from .const import DOMAIN, PLATFORMS
from .coordinator import SpotifyCoordinator
from .services import async_setup_services


SERVICES_SETUP = "services_setup"

async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)

    implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
        hass, entry
    )

    oauth = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    await oauth.async_ensure_token_valid()
    api = SpotifyApi(session, oauth.token["access_token"])

    coordinator = SpotifyCoordinator(hass, api, oauth)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "oauth": oauth,
        "api": api,
        "coordinator": coordinator,
        "selected_device_id": None,
    }

    if not hass.data[DOMAIN].get(SERVICES_SETUP):
        await async_setup_services(hass)
        hass.data[DOMAIN][SERVICES_SETUP] = True

    entry.async_on_unload(entry.add_update_listener(_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok
