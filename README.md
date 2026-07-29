# Spotify Playlist Select

[![HACS Default](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/default)
[![Hassfest](https://img.shields.io/github/actions/workflow/status/jstnjx/ha-intg-spotify/hassfest.yml?branch=main&label=Hassfest&style=for-the-badge)](https://github.com/jstnjx/ha-intg-spotify/actions/workflows/hassfest.yml)
[![HACS Validation](https://img.shields.io/github/actions/workflow/status/jstnjx/ha-intg-spotify/hacs.yml?branch=main&label=HACS&style=for-the-badge)](https://github.com/jstnjx/ha-intg-spotify/actions/workflows/hacs.yml)
[![GitHub Release](https://img.shields.io/github/v/release/jstnjx/ha-intg-spotify?style=for-the-badge)](https://github.com/jstnjx/ha-intg-spotify/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/jstnjx/ha-intg-spotify/total?style=for-the-badge)](https://github.com/jstnjx/ha-intg-spotify/releases)
[![License](https://img.shields.io/github/license/jstnjx/ha-intg-spotify?style=for-the-badge)](LICENSE)

A Home Assistant custom integration that adds Spotify playlist selection, Spotify Connect device selection, a lightweight Spotify media player, and playback sensors using the Spotify Web API.

> **Not affiliated with or endorsed by Spotify.**

---

## Features

- Native Home Assistant Config Flow
- Application Credentials (OAuth2)
- One Spotify account per Home Assistant instance
- Spotify Connect device selection
- Playlist track selection
- Lightweight Spotify `media_player`
- Playback status sensor
- Automatic OAuth token refresh
- Configurable playback behavior
- Fully compatible with HACS

---

## Compatibility

| Component | Version |
|-----------|---------|
| Home Assistant | 2026.1.0+ |
| Installation | HACS / Manual |
| Spotify Account | Premium |
| Authentication | OAuth2 (Application Credentials) |

---

## Installation

### HACS (Recommended)

1. Open **HACS → Integrations**
2. Click **⋮ → Custom repositories**
3. Add

```
https://github.com/jstnjx/ha-intg-spotify
```

Category:

```
Integration
```

4. Install the integration.
5. Restart Home Assistant.

---

### Manual

Download the latest release and copy

```
custom_components/spotify_playlist_select
```

to

```
config/custom_components/
```

Restart Home Assistant afterwards.

---

## Spotify OAuth Setup

### 1. Create a Spotify Developer App

Create an application on the Spotify Developer Dashboard:

https://developer.spotify.com/dashboard

Copy the:

- Client ID
- Client Secret

---

### 2. Configure the Redirect URI

Add the following redirect URI to your Spotify application:

```
https://<YOUR_HOME_ASSISTANT_URL>/auth/external/callback
```

Example:

```
https://homeassistant.example.com/auth/external/callback
```

or

```
https://<your-nabu-casa-url>/auth/external/callback
```

The redirect URI **must match exactly**.

---

### 3. Configure Application Credentials

Navigate to

**Settings → Devices & Services → Application Credentials**

Add credentials for **Spotify Playlist Select** using the Client ID and Client Secret.

---

### 4. Add the Integration

Go to

**Settings → Devices & Services → Add Integration**

Select **Spotify Playlist Select**, choose your playback mode and authorize Spotify.

Required Spotify scopes:

- `playlist-read-private`
- `playlist-read-collaborative`
- `user-read-playback-state`
- `user-modify-playback-state`

---

## Entities

### Select Entities

| Entity | Description |
|---------|-------------|
| Spotify Connect Device | Selects the active playback device |
| Playlist Track Select | One entity per playlist containing all tracks |

Selecting a track immediately starts playback on the selected device.

---

### Media Player

Provides:

- Play / Pause
- Next / Previous
- Shuffle
- Repeat
- Playlist selection (`source_list`)
- Device selection (`sound_mode`)
- Album artwork
- Metadata
- Playback progress

A small command debounce reduces Spotify "restriction violated" errors caused by rapid repeated commands.

---

### Playback Sensor

State:

- Playing
- Paused
- Idle

Attributes include:

- Selected device
- Available devices
- Current track
- Album artwork
- Playlist / Context
- Shuffle
- Repeat
- Progress
- Cached playlists

---

## Playback Modes

### Play

Starts playback at the selected track within the playlist.

Playback continues normally through the playlist.

---

### Queue + Play

If an active player exists:

- Switch playlist
- Queue selected track
- Skip to queued track

Otherwise it falls back to standard playlist playback.

---

## Notes

- Large playlists create large Select entities.
- Duplicate Spotify device names automatically receive a short identifier.
- Spotify playback commands may occasionally return **restriction violated** depending on the current playback state.
- Playback state is refreshed approximately every **15 seconds**.

---

## Troubleshooting

### Permissions Missing / 401

Remove:

- Integration
- Application Credentials
- Spotify authorization (Spotify Account → Manage Apps)

Then add the integration again.

---

### No Spotify Devices

Spotify Connect devices only appear while they are online.

Open Spotify once on the target device before refreshing.

---

## Support

- **Issues:** https://github.com/jstnjx/ha-intg-spotify/issues
- Please include:
  - Home Assistant version
  - Integration version
  - Relevant logs

---

## License

This project is licensed under the [MIT License](LICENSE).