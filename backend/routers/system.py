"""Health + session/connection-status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from backend.auth import store
from backend.common.auth import require_auth
from backend.common.config import Settings, get_settings
from backend.deps import get_session
from backend.models.schemas import ServiceState, SessionResponse
from backend.models.tables import User

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "vibeflow"}


@router.get("/session", response_model=SessionResponse)
def session_status(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    user: User = Depends(require_auth),
) -> SessionResponse:
    """Per-service state for the UI. `configured` = client creds present; `connected` = this
    user's tokens persisted in the DB (so it survives a fresh browser)."""
    return SessionResponse(
        spotify=ServiceState(
            # In dev-bypass mode treat Spotify as configured even without client creds,
            # since the refresh-token grant doesn't need the browser OAuth app.
            configured=settings.spotify_configured or settings.spotify_dev_login,
            connected=store.is_connected(session, user.id, "spotify"),
        ),
        tidal=ServiceState(
            configured=settings.tidal_configured,
            connected=store.is_connected(session, user.id, "tidal"),
        ),
        dev=settings.dev_auth,
    )
