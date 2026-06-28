"""Persisted tables (SQLModel / SQLite).

Multi-user app: every user owns their own provider tokens, mappings, and run history, all
scoped by `user_id`. Tokens live here (not just the session cookie) so scheduled, headless
syncs can authenticate without a browser. The Spotify→Tidal match cache (`TrackMatch`) is
deliberately global — a track↔track mapping is user-agnostic and benefits everyone.
"""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.utcnow()


class User(SQLModel, table=True):
    """An app account. `password_hash` is None until the account is set up (the bootstrap
    admin is created empty on first launch and its password is set via the setup screen)."""

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str | None = None  # None = not yet set up
    is_admin: bool = False
    # Sync preference: when True, a track is added once per time it appears in the source
    # playlist; when False (default), accidental duplicates collapse to a single entry.
    allow_duplicates: bool = False
    created_at: datetime = Field(default_factory=_utcnow)


class Credentials(SQLModel, table=True):
    """OAuth tokens for one user's provider. PK is (user_id, provider)."""

    user_id: int = Field(foreign_key="user.id", primary_key=True)
    provider: str = Field(primary_key=True)  # 'spotify' | 'tidal'
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
    user_id: int = Field(foreign_key="user.id", index=True)
    spotify_playlist_id: str
    spotify_name: str
    tidal_playlist_id: str | None = None
    tidal_name: str | None = None
    enabled: bool = False
    # Reconcile mode for re-syncs: 'add' = append new tracks only; 'mirror' = make Tidal
    # match the source exactly (add new + remove tracks no longer in the Spotify playlist).
    mode: str = "add"
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
    user_id: int = Field(foreign_key="user.id", index=True)
    mapping_id: int | None = Field(default=None, foreign_key="mapping.id")
    trigger: str = "manual"  # manual | scheduled (how the run was started)
    mode: str = "add"        # add | mirror (effective for this run)
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


class NotificationConfig(SQLModel, table=True):
    """Per-user Discord webhook + which run/auth events to announce. No row (or enabled=False)
    means notifications are off for that user. One config per user (PK = user_id)."""

    user_id: int = Field(foreign_key="user.id", primary_key=True)
    webhook_url: str | None = None
    enabled: bool = False           # master switch
    on_failure: bool = True         # a sync run ended in error
    on_revocation: bool = True      # a provider token was rejected (reconnect needed)
    on_success: bool = False        # a run completed (success or partial) — opt-in, can be noisy
    updated_at: datetime = Field(default_factory=_utcnow)


class TrackMatch(SQLModel, table=True):
    """Match cache. tidal_id None = a confirmed miss (track searched, not on Tidal), so
    recurring syncs don't re-search it. matched_by: isrc | metadata | manual | none."""

    spotify_id: str = Field(primary_key=True)
    isrc: str | None = None
    tidal_id: str | None = None
    matched_by: str | None = None
    updated_at: datetime = Field(default_factory=_utcnow)
