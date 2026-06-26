"""Tidal v2 JSON:API client (raw httpx).

Ported from the distilled spec in PLANNING.md §7a. Every call carries countryCode; writes
use the application/vnd.api+json envelope. Includes retry with exponential backoff on rate
limits (429) and transient 5xx, since recurring syncs amplify Tidal's rate limiting.
"""

from __future__ import annotations

import time
from urllib.parse import quote

import httpx

from backend.common.config import get_settings
from backend.common.logging_config import logger

TIDAL_API_BASE = "https://openapi.tidal.com"
_JSON_API = "application/vnd.api+json"
_MAX_RETRIES = 4
_ADD_CHUNK = 20


class TidalError(Exception):
    pass


class TidalClient:
    def __init__(self, access_token: str, country_code: str | None = None):
        self._token = access_token
        self._country = country_code or get_settings().tidal_country_code
        self._client = httpx.Client(base_url=TIDAL_API_BASE, timeout=30)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "TidalClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ── transport ────────────────────────────────────────────────────────────
    def _request(self, method: str, path: str, *, json=None, params=None, accept=None):
        headers = {"Authorization": f"Bearer {self._token}"}
        if accept:
            headers["Accept"] = accept
        if json is not None:
            headers["Content-Type"] = _JSON_API
        params = {"countryCode": self._country, **(params or {})}

        backoff = 1.0
        for attempt in range(_MAX_RETRIES):
            resp = self._client.request(
                method, path, json=json, params=params, headers=headers
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = float(resp.headers.get("Retry-After", backoff))
                logger.warning(
                    "Tidal %s %s -> %s; retry %d/%d in %.1fs",
                    method, path, resp.status_code, attempt + 1, _MAX_RETRIES, wait,
                )
                time.sleep(wait)
                backoff *= 2
                continue
            return resp
        return resp  # exhausted retries; caller inspects status

    # ── playlists ────────────────────────────────────────────────────────────
    def create_playlist(self, name: str, description: str | None) -> str:
        resp = self._request(
            "POST",
            "/v2/playlists",
            json={
                "data": {
                    "type": "playlists",
                    "attributes": {
                        "name": name,
                        "description": description or "Synced from Spotify via VibeFlow",
                    },
                }
            },
        )
        if resp.status_code >= 400:
            raise TidalError(f"create_playlist failed {resp.status_code}: {resp.text}")
        return resp.json()["data"]["id"]

    def add_tracks(self, playlist_id: str, track_ids: list[str]) -> None:
        for i in range(0, len(track_ids), _ADD_CHUNK):
            chunk = track_ids[i : i + _ADD_CHUNK]
            resp = self._request(
                "POST",
                f"/v2/playlists/{playlist_id}/relationships/items",
                json={"data": [{"id": str(tid), "type": "tracks"} for tid in chunk]},
            )
            if resp.status_code >= 400:
                raise TidalError(f"add_tracks failed {resp.status_code}: {resp.text}")

    def existing_track_ids(self, playlist_id: str) -> set[str]:
        """Track ids already in a Tidal playlist — drives diff detection on re-sync."""
        ids: set[str] = set()
        path = f"/v2/playlists/{playlist_id}/relationships/items"
        params: dict | None = None
        while path:
            resp = self._request("GET", path, params=params, accept=_JSON_API)
            if resp.status_code >= 400:
                logger.warning("existing_track_ids %s: %s", resp.status_code, resp.text)
                break
            body = resp.json()
            for entry in body.get("data", []):
                if entry.get("type") == "tracks":
                    ids.add(str(entry["id"]))
            nxt = (body.get("links") or {}).get("next")
            if not nxt:
                break
            path, params = nxt, None  # next link carries its own query
        return ids

    # ── search ───────────────────────────────────────────────────────────────
    def search_by_isrc(self, isrc: str) -> str | None:
        resp = self._request(
            "GET", "/v2/tracks", params={"filter[isrc]": isrc}, accept=_JSON_API
        )
        if resp.status_code >= 400:
            return None
        data = resp.json().get("data") or []
        return str(data[0]["id"]) if data else None

    def search_by_metadata(self, name: str, artists: list[str]) -> str | None:
        query = quote(f"{name} {' '.join(artists)}")
        resp = self._request(
            "GET",
            f"/v2/searchResults/{query}",
            params={"include": "tracks"},
            accept=_JSON_API,
        )
        if resp.status_code >= 400:
            return None
        body = resp.json()
        rel = (((body.get("data") or {}).get("relationships") or {}).get("tracks") or {})
        refs = rel.get("data") or []
        if not refs:
            return None
        included = [x for x in body.get("included", []) if x.get("type") == "tracks"]
        lname = name.lower()
        for track in included:
            if (track.get("attributes") or {}).get("title", "").lower() == lname:
                return str(track["id"])
        # Fall back to the first referenced track id.
        return str(refs[0]["id"])

    def list_playlists(self) -> list[dict]:
        """Best-effort: the user's Tidal playlists (for picking a sync target)."""
        resp = self._request("GET", "/v2/playlists", accept=_JSON_API)
        if resp.status_code >= 400:
            return []
        out = []
        for entry in resp.json().get("data", []):
            attrs = entry.get("attributes") or {}
            out.append({"id": entry["id"], "name": attrs.get("name", "Untitled")})
        return out
