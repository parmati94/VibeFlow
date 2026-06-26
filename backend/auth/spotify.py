"""Spotify OAuth via spotipy.

spotipy's SpotifyOAuth builds the authorize URL, exchanges the code, and refreshes tokens.
Its on-disk token cache is disabled — the DB (Credentials table) is our token store.
"""

from __future__ import annotations

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from backend.common.config import get_settings

# Read access to the user's playlists + their tracks (incl. ISRCs).
SPOTIFY_SCOPE = "playlist-read-private playlist-read-collaborative"


class _NoCache(spotipy.cache_handler.CacheHandler):
    """Disable spotipy's disk cache — the DB is the token store."""

    def get_cached_token(self):
        return None

    def save_token_to_cache(self, token_info):
        pass


def _oauth() -> SpotifyOAuth:
    s = get_settings()
    return SpotifyOAuth(
        client_id=s.spotify_client_id,
        client_secret=s.spotify_client_secret,
        redirect_uri=s.spotify_redirect_uri,
        scope=SPOTIFY_SCOPE,
        cache_handler=_NoCache(),
    )


def login_url() -> str:
    return _oauth().get_authorize_url()


def exchange_code(code: str) -> dict:
    return _oauth().get_access_token(code, as_dict=True, check_cache=False)


def refresh(refresh_token: str) -> dict:
    return _oauth().refresh_access_token(refresh_token)


def is_expired(token_info: dict) -> bool:
    return _oauth().is_token_expired(token_info)
