"""Spotify + Tidal OAuth round-trips.

These live under /auth (no /api prefix) and are proxied as-is by nginx so the whole flow,
including the provider redirects, stays on the single public origin. On success the tokens
are persisted to the DB (Credentials) — the durable store the headless scheduler reads —
and the browser is bounced back to the SPA.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from backend.auth import spotify as spotify_auth
from backend.auth import store
from backend.auth import tidal as tidal_auth
from backend.common.config import Settings, get_settings
from backend.common.logging_config import logger
from backend.deps import get_session

router = APIRouter(prefix="/auth", tags=["auth"])


# ── Spotify ──────────────────────────────────────────────────────────────────
@router.get("/spotify/login")
def spotify_login(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    # Dev bypass: mint + persist tokens from a pre-captured refresh token (no browser, no
    # registered redirect URI). Gated by DEV_AUTH; never reached in a real deploy.
    if settings.spotify_dev_login:
        try:
            token_info = spotify_auth.refresh(settings.spotify_dev_refresh_token)
            token_info.setdefault("refresh_token", settings.spotify_dev_refresh_token)
            store.save_spotify(session, token_info)
            logger.warning("DEV_AUTH: Spotify connected via refresh-token bypass.")
            return RedirectResponse(url="/?connected=spotify")
        except Exception as exc:  # noqa: BLE001
            logger.error("Dev Spotify login failed: %s", exc)
            return RedirectResponse(url="/?error=spotify_dev_login_failed")

    if not settings.spotify_configured:
        return RedirectResponse(url="/?error=spotify_not_configured")
    return RedirectResponse(spotify_auth.login_url())


@router.get("/spotify/callback")
def spotify_callback(
    request: Request, session: Session = Depends(get_session)
) -> RedirectResponse:
    code = request.query_params.get("code")
    if not code:
        return RedirectResponse(url="/?error=spotify_no_code")
    try:
        token_info = spotify_auth.exchange_code(code)
        store.save_spotify(session, token_info)
    except Exception as exc:  # noqa: BLE001
        logger.error("Spotify code exchange failed: %s", exc)
        return RedirectResponse(url="/?error=spotify_auth_failed")
    logger.info("Spotify connected; tokens persisted.")
    return RedirectResponse(url="/?connected=spotify")


@router.post("/spotify/logout")
def spotify_logout(session: Session = Depends(get_session)) -> dict:
    store.disconnect(session, "spotify")
    return {"message": "Spotify disconnected."}


# ── Tidal (PKCE) ─────────────────────────────────────────────────────────────
@router.get("/tidal/login")
def tidal_login(
    request: Request, settings: Settings = Depends(get_settings)
) -> RedirectResponse:
    if not settings.tidal_configured:
        return RedirectResponse(url="/?error=tidal_not_configured")
    state = secrets.token_urlsafe(8)
    verifier, challenge = tidal_auth.generate_pkce()
    # Transient PKCE state rides the session cookie between login and callback.
    request.session["tidal_state"] = state
    request.session["tidal_verifier"] = verifier
    return RedirectResponse(tidal_auth.login_url(state, challenge))


@router.get("/tidal/callback")
def tidal_callback(
    request: Request, session: Session = Depends(get_session)
) -> RedirectResponse:
    error = request.query_params.get("error")
    if error:
        logger.error("Tidal authorization error: %s", error)
        return RedirectResponse(url=f"/?error=tidal_{error}")

    code = request.query_params.get("code")
    state = request.query_params.get("state")
    if not code:
        return RedirectResponse(url="/?error=tidal_no_code")
    if state != request.session.get("tidal_state"):
        return RedirectResponse(url="/?error=tidal_state_mismatch")

    verifier = request.session.get("tidal_verifier")
    if not verifier:
        return RedirectResponse(url="/?error=tidal_missing_verifier")
    try:
        token = tidal_auth.exchange_code(code, verifier)
        store.save_tidal(session, token)
    except Exception as exc:  # noqa: BLE001
        logger.error("Tidal token exchange failed: %s", exc)
        return RedirectResponse(url="/?error=tidal_auth_failed")
    request.session.pop("tidal_verifier", None)
    request.session.pop("tidal_state", None)
    logger.info("Tidal connected; tokens persisted.")
    return RedirectResponse(url="/?connected=tidal")


@router.post("/tidal/logout")
def tidal_logout(session: Session = Depends(get_session)) -> dict:
    store.disconnect(session, "tidal")
    return {"message": "Tidal disconnected."}
