"""Pydantic request/response models for the JSON API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ServiceState(BaseModel):
    configured: bool
    connected: bool


class SessionResponse(BaseModel):
    spotify: ServiceState
    tidal: ServiceState
    dev: bool = False


class PlaylistSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    track_count: int = 0
    image_url: str | None = None


class SyncRequest(BaseModel):
    playlist_ids: list[str]
    mode: str = "add"  # add | mirror (for this one-time sync)


class UnmatchedTrack(BaseModel):
    name: str
    artists: list[str]


class SyncRunView(BaseModel):
    id: int
    spotify_playlist_id: str
    playlist_name: str
    scheduled: bool = False
    status: str
    total: int
    processed: int
    matched_isrc: int
    matched_meta: int
    not_found: int
    added: int
    tidal_playlist_id: str | None
    unmatched: list[UnmatchedTrack] = []
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class MessageResponse(BaseModel):
    message: str


class ScheduleFields(BaseModel):
    frequency: str | None = None  # hourly | daily | weekly | monthly
    at_hour: int | None = None
    at_minute: int = 0
    day_of_week: int | None = None  # 0=Mon
    day_of_month: int | None = None  # 1-28
    mode: str = "add"  # add | mirror


class MappingCreate(ScheduleFields):
    spotify_playlist_id: str
    spotify_name: str
    enabled: bool = True


class MappingUpdate(ScheduleFields):
    enabled: bool | None = None


class MappingView(BaseModel):
    id: int
    spotify_playlist_id: str
    spotify_name: str
    tidal_playlist_id: str | None
    tidal_name: str | None
    enabled: bool
    mode: str
    frequency: str | None
    at_hour: int | None
    at_minute: int
    day_of_week: int | None
    day_of_month: int | None
    interval_minutes: int | None
    last_run_at: datetime | None
    last_status: str | None = None
    next_run_at: datetime | None = None
    created_at: datetime
