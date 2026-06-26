"""Health + session/connection-status endpoints.

Thin handlers under /api. In Phase 0 the connection states are stubbed False; Phase 1
wires them to the persisted Spotify/Tidal credentials. nginx has a separate /healthz for
container liveness — this /api/health proves the backend itself is up through the proxy.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.common.config import Settings, get_settings

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "vibeflow"}


@router.get("/session")
def session_status(
    request: Request, settings: Settings = Depends(get_settings)
) -> dict:
    """Per-service connection state for the UI auth-gate. Stubbed in Phase 0; Phase 1
    reports whether valid Spotify/Tidal credentials are persisted."""
    return {
        "spotify": {
            "configured": settings.spotify_configured,
            "connected": bool(request.session.get("spotify_connected")),
        },
        "tidal": {
            "configured": settings.tidal_configured,
            "connected": bool(request.session.get("tidal_connected")),
        },
    }
