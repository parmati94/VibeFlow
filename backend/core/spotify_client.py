"""Spotify reads: playlists + tracks (with ISRCs).

Thin wrapper over a token-authenticated spotipy client. Tracks are normalized to the shape
the matcher/sync engine expect, dropping local files (not resolvable on Tidal).
"""

from __future__ import annotations

import time

import spotipy


class SpotifyClient:
    def __init__(self, access_token: str):
        self._sp = spotipy.Spotify(auth=access_token)

    def list_playlists(self) -> list[dict]:
        items: list[dict] = []
        results = self._sp.current_user_playlists(limit=50)
        while results:
            for pl in results["items"]:
                if not pl:
                    continue
                images = pl.get("images") or []
                items.append(
                    {
                        "id": pl["id"],
                        "name": pl["name"],
                        "description": pl.get("description"),
                        "track_count": pl["tracks"]["total"],
                        "image_url": images[0]["url"] if images else None,
                    }
                )
            results = self._sp.next(results) if results.get("next") else None
        return items

    def get_playlist(self, playlist_id: str) -> dict:
        # snapshot_id is Spotify's playlist-version id — it changes whenever the contents
        # change, so the sync engine uses it to skip a re-sync that would add nothing.
        # _cb is a cache-buster: Spotify edge-caches this response by URL and can serve a
        # stale snapshot_id for ~a minute after an edit; a unique param forces a fresh read
        # so the short-circuit never skips a just-changed playlist.
        pl = self._sp._get(
            f"playlists/{playlist_id}",
            fields="id,name,description,snapshot_id,tracks.total",
            _cb=str(time.time()),
        )
        return {
            "id": pl["id"],
            "name": pl["name"],
            "description": pl.get("description"),
            "track_count": pl["tracks"]["total"],
            "snapshot_id": pl.get("snapshot_id"),
        }

    def get_tracks(self, playlist_id: str) -> list[dict]:
        tracks: list[dict] = []
        results = self._sp.playlist_items(
            playlist_id,
            limit=100,
            additional_types=("track",),
        )
        while results:
            for item in results["items"]:
                track = item.get("track")
                if not track or track.get("is_local") or not track.get("id"):
                    continue
                tracks.append(
                    {
                        "spotify_id": track["id"],
                        "name": track["name"],
                        "artists": [a["name"] for a in track.get("artists", [])],
                        "album": (track.get("album") or {}).get("name"),
                        "isrc": (track.get("external_ids") or {}).get("isrc"),
                        "duration_ms": track.get("duration_ms"),
                    }
                )
            results = self._sp.next(results) if results.get("next") else None
        return tracks
