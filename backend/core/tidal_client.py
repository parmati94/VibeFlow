"""Tidal v2 JSON:API client (raw httpx).

Ported from the distilled spec in PLANNING.md §7a. Every call carries countryCode; writes
use the application/vnd.api+json envelope. Includes retry with exponential backoff on rate
limits (429) and transient 5xx, since recurring syncs amplify Tidal's rate limiting.
"""

from __future__ import annotations

import re
import time
from urllib.parse import quote

import httpx

from backend.common.config import get_settings
from backend.common.logging_config import logger

TIDAL_API_BASE = "https://openapi.tidal.com"
_JSON_API = "application/vnd.api+json"
_MAX_RETRIES = 4
_ADD_CHUNK = 20
_ISRC_BATCH = 20          # ISRCs per /v2/tracks?filter[isrc]=a,b,c lookup
# Tidal exposes no quota headers — empirically a small token bucket (~5 quick, then 429
# with Retry-After: 4). Pace requests to stay under it; backoff handles the occasional miss.
_MIN_INTERVAL = 0.34      # ≈ 3 requests/sec


_ISO_DUR = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def _iso8601_seconds(value: str | None) -> int | None:
    """Parse Tidal's ISO-8601 track duration ('PT3M10S') to whole seconds."""
    if not value:
        return None
    m = _ISO_DUR.fullmatch(value)
    if not m:
        return None
    h, mins, secs = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mins * 60 + secs


class TidalError(Exception):
    pass


class TidalClient:
    def __init__(self, access_token: str, country_code: str | None = None):
        self._token = access_token
        self._country = country_code or get_settings().tidal_country_code
        self._client = httpx.Client(base_url=TIDAL_API_BASE, timeout=30)
        self._last = 0.0  # monotonic time of the last request (for throttling)

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
            self._pace()
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

    def _pace(self) -> None:
        """Keep at least _MIN_INTERVAL between requests so we don't drain Tidal's bucket."""
        now = time.monotonic()
        wait = self._last + _MIN_INTERVAL - now
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()

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

    def playlist_exists(self, playlist_id: str) -> bool:
        """Whether a Tidal playlist still exists (it may have been deleted in the Tidal app)."""
        resp = self._request("GET", f"/v2/playlists/{playlist_id}", accept=_JSON_API)
        return resp.status_code < 400

    def remove_items(self, playlist_id: str, items: list[dict]) -> None:
        """Remove specific playlist items (mirror mode). Tidal requires each item's per-entry
        `meta.itemId` (not just the track id) to identify what to delete. `items` are dicts
        of {track_id, item_id} as returned by playlist_items()."""
        for i in range(0, len(items), _ADD_CHUNK):
            chunk = items[i : i + _ADD_CHUNK]
            resp = self._request(
                "DELETE",
                f"/v2/playlists/{playlist_id}/relationships/items",
                json={
                    "data": [
                        {"id": str(it["track_id"]), "type": "tracks",
                         "meta": {"itemId": it["item_id"]}}
                        for it in chunk
                    ]
                },
            )
            if resp.status_code >= 400:
                raise TidalError(f"remove_items failed {resp.status_code}: {resp.text}")

    def playlist_items(self, playlist_id: str) -> list[dict]:
        """All items in a Tidal playlist as {track_id, item_id} — drives diff detection and
        mirror removal (item_id is the per-entry id Tidal needs to delete a specific item).

        Cursor-paginated: Tidal pages 20 at a time and its `links.next` omits the /v2 prefix
        (so following it 404s); we re-request with the cursor from `links.meta.nextCursor`."""
        out: list[dict] = []
        path = f"/v2/playlists/{playlist_id}/relationships/items"
        cursor: str | None = None
        for _ in range(500):  # safety bound (~10k items at 20/page)
            params = {"page[cursor]": cursor} if cursor else None
            resp = self._request("GET", path, params=params, accept=_JSON_API)
            if resp.status_code >= 400:
                logger.warning("playlist_items %s: %s", resp.status_code, resp.text)
                break
            body = resp.json()
            for entry in body.get("data", []):
                if entry.get("type") == "tracks":
                    out.append({
                        "track_id": str(entry["id"]),
                        "item_id": (entry.get("meta") or {}).get("itemId"),
                    })
            cursor = ((body.get("links") or {}).get("meta") or {}).get("nextCursor")
            if not cursor:
                break
        return out

    # ── search ───────────────────────────────────────────────────────────────
    def search_by_isrc(self, isrc: str) -> str | None:
        resp = self._request(
            "GET", "/v2/tracks", params={"filter[isrc]": isrc}, accept=_JSON_API
        )
        if resp.status_code >= 400:
            return None
        data = resp.json().get("data") or []
        return str(data[0]["id"]) if data else None

    def tracks_by_isrc(self, isrcs: list[str]) -> dict[str, str]:
        """Resolve many ISRCs at once → {isrc: tidal_track_id}. Tidal's filter[isrc] takes a
        comma-separated list, so this is ~20x fewer requests than one lookup per track."""
        out: dict[str, str] = {}
        unique = [i for i in dict.fromkeys(isrcs) if i]
        for i in range(0, len(unique), _ISRC_BATCH):
            chunk = unique[i : i + _ISRC_BATCH]
            resp = self._request(
                "GET", "/v2/tracks",
                params={"filter[isrc]": ",".join(chunk)}, accept=_JSON_API,
            )
            if resp.status_code >= 400:
                continue
            for entry in resp.json().get("data", []):
                isrc = (entry.get("attributes") or {}).get("isrc")
                if isrc and isrc not in out:
                    out[isrc] = str(entry["id"])
        return out

    def search_candidates(self, query: str, limit: int = 12) -> list[dict]:
        """Return ranked candidate tracks for a free-text query, each with the fields the
        matcher scores against: id, title, artists (names), duration (seconds), isrc.

        Uses include=tracks.artists — the only include that returns per-candidate artist
        names (plain `tracks` leaves artists empty). Order follows Tidal's own ranking.
        """
        resp = self._request(
            "GET",
            f"/v2/searchResults/{quote(query)}",
            params={"include": "tracks.artists"},
            accept=_JSON_API,
        )
        if resp.status_code >= 400:
            return []
        body = resp.json()
        refs = (
            (((body.get("data") or {}).get("relationships") or {}).get("tracks") or {})
            .get("data")
            or []
        )
        included = body.get("included", [])
        tracks_by_id = {x["id"]: x for x in included if x.get("type") == "tracks"}
        artist_name = {
            x["id"]: (x.get("attributes") or {}).get("name", "")
            for x in included
            if x.get("type") == "artists"
        }

        out: list[dict] = []
        for ref in refs[:limit]:
            t = tracks_by_id.get(ref["id"])
            if not t:
                continue
            attrs = t.get("attributes") or {}
            art_refs = ((t.get("relationships") or {}).get("artists") or {}).get("data") or []
            out.append(
                {
                    "id": str(t["id"]),
                    "title": attrs.get("title", ""),
                    "artists": [artist_name.get(a["id"], "") for a in art_refs],
                    "duration": _iso8601_seconds(attrs.get("duration")),
                    "isrc": attrs.get("isrc"),
                }
            )
        return out

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
