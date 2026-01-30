DOMAIN = "spotify_playlist_select"

CONF_PLAY_MODE = "play_mode"
PLAY_MODE_PLAY = "play"
PLAY_MODE_QUEUE_PLAY = "queue_play"

SPOTIFY_SCOPES = [
    "playlist-read-private",
    "playlist-read-collaborative",
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-library-read",        
    "user-read-recently-played"
]

RUNTIME_SELECTED_DEVICE_ID = "selected_device_id"
RUNTIME_CONTEXT = "spotify_context"
RUNTIME_CONTEXT_ITEM = "spotify_context_item"

CONTEXT_PLAYLISTS = "playlists"
CONTEXT_SAVED = "saved_tracks"
CONTEXT_RECENT = "recently_played"

PLATFORMS = ["select", "media_player", "sensor"]

SERVICE_PLAY_PLAYLIST = "play_playlist"
SERVICE_PLAY_TRACK_IN_PLAYLIST = "play_track_in_playlist"
SERVICE_QUEUE_TRACK = "queue_track"
SERVICE_REFRESH_LIBRARY = "refresh_library"

TRACK_LIMIT_PER_PLAYLIST = 128
SAVED_TRACKS_LIMIT = 128
RECENT_TRACKS_LIMIT = 50
LIKED_SONGS_LIMIT = 128
RECENTLY_PLAYED_LIMIT = 128

CONF_SELECTED_PLAYLIST_IDS = "selected_playlist_ids"
