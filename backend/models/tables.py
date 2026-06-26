"""Persisted tables (SQLModel / SQLite).

Single-user app: one row per provider in `credentials`. Tokens live here (not just the
session cookie) so scheduled, headless syncs can authenticate without a browser. Sync
results and the Spotify→Tidal match cache persist so re-syncs are fast and resumable.
"""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.utcnow()


class Credentials(SQLModel, table=True):
    """OAuth tokens for one provider. provider is the PK ('spotify' | 'tidal')."""

    provider: str = Field(primary_key=True)
    access_token: str
    refresh_token: str | None = None
    expires_at: float = 0.0  # epoch seconds
    scope: str | None = None
    extra: str | None = None  # JSON blob, e.g. Tidal user id
    updated_at: datetime = Field(default_factory=_utcnow)


class Mapping(SQLModel, table=True):
    """A saved Spotify→Tidal playlist link. Drives scheduled auto-sync (Phase 4); also the
    target a manual sync writes to so re-syncs reuse the same Tidal playlist."""

    id: int | None = Field(default=None, primary_key=True)
    spotify_playlist_id: str
    spotify_name: str
    tidal_playlist_id: str | None = None
    tidal_name: str | None = None
    enabled: bool = False
    # Schedule: frequency + when. frequency ∈ hourly|daily|weekly|monthly.
    #   hourly  → at_minute
    #   daily   → at_hour:at_minute
    #   weekly  → day_of_week (0=Mon) at at_hour:at_minute
    #   monthly → day_of_month (1-28) at at_hour:at_minute
    frequency: str | None = None
    at_hour: int | None = None
    at_minute: int = 0
    day_of_week: int | None = None
    day_of_month: int | None = None
    interval_minutes: int | None = None  # legacy fixed-interval mappings (pre-cron)
    last_run_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)


class SyncRun(SQLModel, table=True):
    """One sync attempt (manual or scheduled). Progress fields are updated live so the UI
    can poll for a progress bar; terminal status is success | partial | error."""

    id: int | None = Field(default=None, primary_key=True)
    mapping_id: int | None = Field(default=None, foreign_key="mapping.id")
    spotify_playlist_id: str
    playlist_name: str
    status: str = "queued"  # queued | running | success | partial | error
    total: int = 0
    processed: int = 0
    matched_isrc: int = 0
    matched_meta: int = 0
    not_found: int = 0
    added: int = 0
    tidal_playlist_id: str | None = None
    unmatched: str | None = None  # JSON list of {name, artists}
    error: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None


class TrackMatch(SQLModel, table=True):
    """Match cache. tidal_id None = a confirmed miss (track searched, not on Tidal), so
    recurring syncs don't re-search it. matched_by: isrc | metadata | manual | none."""

    spotify_id: str = Field(primary_key=True)
    isrc: str | None = None
    tidal_id: str | None = None
    matched_by: str | None = None
    updated_at: datetime = Field(default_factory=_utcnow)
