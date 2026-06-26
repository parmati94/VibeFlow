"""Spotify→Tidal track matching, backed by the TrackMatch cache.

Strategy: ISRC first (exact), then a normalized metadata search. Every resolution — hit or
confirmed miss — is cached by Spotify track id so recurring syncs skip the search entirely.
"""

from __future__ import annotations

import re
from datetime import datetime

from sqlmodel import Session

from backend.core.tidal_client import TidalClient
from backend.models.tables import TrackMatch

# Strip parenthetical/dash noise that hurts metadata matching:
# "Song (feat. X) - 2011 Remaster" → "Song".
_NOISE = re.compile(
    r"\s*[\(\[].*?(feat|with|remaster|remastered|version|edit|mix|live|acoustic).*?[\)\]]"
    r"|\s*-\s*.*?(remaster|remastered|version|edit|mix|live|acoustic).*$",
    re.IGNORECASE,
)


def normalize_title(name: str) -> str:
    cleaned = _NOISE.sub("", name).strip()
    return cleaned or name.strip()


def resolve(
    session: Session,
    track: dict,
    tidal: TidalClient,
    *,
    use_cache: bool = True,
) -> tuple[str | None, str]:
    """Return (tidal_id_or_None, matched_by). matched_by ∈ isrc|metadata|cache|none."""
    spotify_id = track["spotify_id"]

    if use_cache:
        cached = session.get(TrackMatch, spotify_id)
        if cached is not None:
            return cached.tidal_id, "cache"

    tidal_id: str | None = None
    matched_by = "none"

    isrc = track.get("isrc")
    if isrc:
        tidal_id = tidal.search_by_isrc(isrc)
        if tidal_id:
            matched_by = "isrc"

    if not tidal_id:
        tidal_id = tidal.search_by_metadata(
            normalize_title(track["name"]), track.get("artists", [])
        )
        if tidal_id:
            matched_by = "metadata"

    _cache(session, spotify_id, isrc, tidal_id, matched_by)
    return tidal_id, matched_by


def _cache(
    session: Session, spotify_id: str, isrc: str | None, tidal_id: str | None, by: str
) -> None:
    row = session.get(TrackMatch, spotify_id)
    if row is None:
        row = TrackMatch(spotify_id=spotify_id)
    row.isrc = isrc
    row.tidal_id = tidal_id
    row.matched_by = by
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
