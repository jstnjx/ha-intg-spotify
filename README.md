# Spotify Playlist Select (Home Assistant)

Custom integration for Home Assistant that:
- Authenticates with Spotify (OAuth2)
- Reads your playlists + tracks
- Creates a select entity per playlist (options = tracks)
- Creates a device select for Spotify Connect devices
- Selecting a track plays it on the selected device (or queue + play)

## Install (HACS)
1. Add this repository to HACS as a **Custom Repository** (Integration).
2. Install **Spotify Playlist Select**
3. Restart Home Assistant
4. Settings → Devices & services → Add integration → **Spotify Playlist Select**

## Spotify App setup
Create an app at https://developer.spotify.com/dashboard

Set Redirect URI to:
`https://<your-home-assistant-url>/auth/external/callback`

> Your Home Assistant URL must be reachable by your browser during auth.

## Playback Mode
During setup you can choose:
- `playlist select -> song plays`
- `playlist select -> queue + play`

## Entities
- `select.spotify_connect_device`
- `select.spotify_<playlist>`

## Notes
- Very large playlists can result in a lot of select options.
- Device names may not be unique; the integration appends a short id.
