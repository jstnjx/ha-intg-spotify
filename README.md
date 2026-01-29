# Spotify Playlist Select (Home Assistant)

Custom HACS integration for **Home Assistant 2026.1+** that adds Spotify playlist + device selection, a lightweight Spotify `media_player`, and a playback sensor using the Spotify Web API.

Repository: https://github.com/jstnjx/ha-intg-spotify

> Not affiliated with or endorsed by Spotify.

---

## Features

### Setup (UI / Config Flow)
- Uses Home Assistant **Config Flow**
- Uses **Application Credentials** (Spotify OAuth2)
- **Single Spotify account** (the integration enforces a single configured entry)

During setup you can choose playback behavior for the playlist track selects:
- **playlist select → song plays** (plays the selected track, then continues through the playlist)
- **playlist select → queue + play** (queues the selected track and plays it next, then continues through the playlist)

### Entities

#### `select` entities
- **Spotify Connect device select**
  - Lets you choose the active output device
  - Options are dynamically populated from available Spotify Connect devices
- **One playlist track select per playlist**
  - Each playlist becomes a `select` entity
  - Options are the tracks from that playlist (`Track — Artist`)
  - Selecting a track triggers playback on the currently selected device

#### `media_player` entity
- `play`, `pause`
- `next`, `previous`
- `shuffle`, `repeat`
- **Sound mode list** = Spotify Connect devices (selects the active device for this integration)
- **Source list** = playlists (selecting a source starts playing that playlist)
- Displays standard metadata (title, artist, album, artwork, duration/position)

> The media player includes a small command debounce to reduce Spotify “restriction violated” errors on rapid clicks.

#### `sensor` entity
- A playback sensor (`Spotify Playback`) with a simple state (`idle`, `paused`, `playing`)
- Exposes useful Spotify information as attributes, including:
  - selected device id
  - available devices (list)
  - playback state (shuffle/repeat/progress)
  - current track metadata + artwork URL
  - current context (playlist/album/etc)
  - cached playlists (list)

---

## Installation (HACS)

1. In Home Assistant, open **HACS → Integrations**
2. Click the menu (⋮) → **Custom repositories**
3. Add this repository URL:
   - `https://github.com/jstnjx/ha-intg-spotify`
4. Category: **Integration**
5. Install, then **restart Home Assistant**

---

## Spotify App / OAuth Setup (Application Credentials)

This integration uses Home Assistant’s **Application Credentials** UI.

### 1) Create a Spotify Developer App
- Go to: https://developer.spotify.com/dashboard
- Create an app
- Copy **Client ID** and **Client Secret**

### 2) Configure the Redirect URI in Spotify
Add this Redirect URI in the Spotify app settings:

`https://<YOUR_HOME_ASSISTANT_URL>/auth/external/callback`

Examples:
- `https://homeassistant.example.com/auth/external/callback`
- `https://<nabu-casa-url>/auth/external/callback`

> The redirect URI must match exactly.

### 3) Add Application Credentials in Home Assistant
- **Settings → Devices & services → Application Credentials**
- Add credentials for **Spotify Playlist Select**
- Enter Client ID / Client Secret

### 4) Add the integration
- **Settings → Devices & services → Add integration**
- Search for **Spotify Playlist Select**
- Choose your playback mode
- Select the Application Credential
- Log in to Spotify and approve permissions

**Required scopes**
This integration requests:
- `playlist-read-private`
- `playlist-read-collaborative`
- `user-read-playback-state`
- `user-modify-playback-state`

If you change scopes in code, you must remove:
- the config entry,
- the application credential,
- and the Spotify app authorization (Spotify Account → Manage apps),
then re-auth.

---

## How playback works

### Track selects (per playlist)
- **Play mode**: starts playback in the *playlist context* at the selected track (so it continues through the playlist).
- **Queue + play mode**:
  - If Spotify has an active player: sets the playlist context, queues the selected track, and skips to it.
  - If no active player is available: falls back to starting the playlist at the selected track.

### Media player playlist “Source”
- Selecting a playlist from `source_list` starts that playlist on the selected device.

### Device selection
- The integration stores a “selected device id” internally.
- Device select (`select`) and media player `sound_mode` both update that selected device.

---

## Notes / Limitations

- Very large playlists can make `select` entities heavy (many options).
- Spotify device names can be duplicated; the UI appends a short id.
- Spotify playback commands may fail with “restriction violated” depending on device/account state; rapid repeated button presses can trigger this.
- The integration polls Spotify (default 15s) to keep devices and player state up to date.

---

## Troubleshooting

### “Permissions missing” / 401
You did not grant the required Spotify scopes. Remove:
1. the integration entry,
2. the application credential,
3. the Spotify authorization (Spotify Account → Manage apps),
then re-add and re-auth.

### No devices listed
Spotify Connect devices only appear if they are online and available to your account. Open Spotify on the device once.

---

## Support / Issues
- Issues: https://github.com/jstnjx/ha-intg-spotify/issues
- Please include logs and your Home Assistant version (2026.1+).
