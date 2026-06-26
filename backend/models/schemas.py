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


class PlaylistSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    track_count: int = 0
    image_url: str | None = None


class SyncRequest(BaseModel):
    playlist_ids: list[str]


class UnmatchedTrack(BaseModel):
    name: str
    artists: list[str]


class SyncRunView(BaseModel):
    id: int
    spotify_playlist_id: str
    playlist_name: str
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
