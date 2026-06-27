"""Playlist listings from Spotify (source) and Tidal (target)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from backend.auth import store
from backend.common.auth import require_auth
from backend.core.spotify_client import SpotifyClient
from backend.core.tidal_client import TidalClient
from backend.deps import get_session
from backend.models.schemas import PlaylistSummary
from backend.models.tables import User

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


@router.get("/spotify", response_model=list[PlaylistSummary])
def spotify_playlists(
    session: Session = Depends(get_session), user: User = Depends(require_auth)
) -> list[PlaylistSummary]:
    token = store.valid_spotify_token(session, user.id)
    if not token:
        raise HTTPException(status_code=401, detail="Spotify not connected.")
    return [PlaylistSummary(**p) for p in SpotifyClient(token).list_playlists()]


@router.get("/tidal", response_model=list[PlaylistSummary])
def tidal_playlists(
    session: Session = Depends(get_session), user: User = Depends(require_auth)
) -> list[PlaylistSummary]:
    token = store.valid_tidal_token(session, user.id)
    if not token:
        raise HTTPException(status_code=401, detail="Tidal not connected.")
    with TidalClient(token) as tidal:
        return [PlaylistSummary(**p) for p in tidal.list_playlists()]
