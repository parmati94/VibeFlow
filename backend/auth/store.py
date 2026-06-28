"""DB-backed token storage + refresh.

Persists each provider's tokens in the Credentials table and hands out a valid access
token on demand, refreshing transparently when expired. This is what lets a headless
scheduled sync authenticate with no browser/session in play.
"""

from __future__ import annotations

import time
from datetime import datetime

from sqlmodel import Session

from backend.auth import spotify as spotify_auth
from backend.auth import tidal as tidal_auth
from backend.common.logging_config import logger
from backend.models.tables import Credentials

# Refresh a little early so a token doesn't expire mid-request.
_EXPIRY_SKEW = 60


def _upsert(session: Session, user_id: int, provider: str, **fields) -> Credentials:
    cred = session.get(Credentials, (user_id, provider))
    if cred is None:
        cred = Credentials(user_id=user_id, provider=provider, access_token="")
    for key, value in fields.items():
        setattr(cred, key, value)
    cred.updated_at = datetime.utcnow()
    session.add(cred)
    session.commit()
    session.refresh(cred)
    return cred


def save_spotify(session: Session, user_id: int, token_info: dict) -> None:
    _upsert(
        session,
        user_id,
        "spotify",
        access_token=token_info["access_token"],
        refresh_token=token_info.get("refresh_token"),
        expires_at=float(token_info.get("expires_at", 0)),
        scope=token_info.get("scope"),
    )


def save_tidal(
    session: Session, user_id: int, token: dict, extra: str | None = None
) -> None:
    expires_at = time.time() + float(token.get("expires_in", 0))
    _upsert(
        session,
        user_id,
        "tidal",
        access_token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        expires_at=expires_at,
        scope=token.get("scope"),
        extra=extra,
    )


def get_credentials(
    session: Session, user_id: int, provider: str
) -> Credentials | None:
    return session.get(Credentials, (user_id, provider))


def is_connected(session: Session, user_id: int, provider: str) -> bool:
    return session.get(Credentials, (user_id, provider)) is not None


def disconnect(session: Session, user_id: int, provider: str) -> None:
    cred = session.get(Credentials, (user_id, provider))
    if cred:
        session.delete(cred)
        session.commit()


def valid_spotify_token(session: Session, user_id: int) -> str | None:
    cred = session.get(Credentials, (user_id, "spotify"))
    if not cred:
        return None
    if cred.expires_at - _EXPIRY_SKEW > time.time():
        return cred.access_token
    if not cred.refresh_token:
        return cred.access_token
    logger.info("Spotify token expired; refreshing.")
    try:
        token_info = spotify_auth.refresh(cred.refresh_token)
    except Exception as exc:  # noqa: BLE001
        _handle_refresh_failure(session, user_id, "spotify", exc)
        return None
    # spotipy omits refresh_token from some refresh responses; keep the old one.
    token_info.setdefault("refresh_token", cred.refresh_token)
    save_spotify(session, user_id, token_info)
    return token_info["access_token"]


def valid_tidal_token(session: Session, user_id: int) -> str | None:
    cred = session.get(Credentials, (user_id, "tidal"))
    if not cred:
        return None
    if cred.expires_at - _EXPIRY_SKEW > time.time():
        return cred.access_token
    if not cred.refresh_token:
        return cred.access_token
    logger.info("Tidal token expired; refreshing.")
    try:
        token = tidal_auth.refresh(cred.refresh_token)
    except Exception as exc:  # noqa: BLE001
        _handle_refresh_failure(session, user_id, "tidal", exc)
        return None
    token.setdefault("refresh_token", cred.refresh_token)
    save_tidal(session, user_id, token, extra=cred.extra)
    return token["access_token"]


def _handle_refresh_failure(
    session: Session, user_id: int, provider: str, exc: Exception
) -> None:
    """A refresh that fails with a real auth error (the refresh token was revoked) means the
    user must reconnect — so we disconnect that provider, which the UI surfaces as a
    reconnect prompt. A transient/network error keeps the credentials for the next attempt.
    """
    import httpx

    auth_failure = "invalid_grant" in str(exc).lower() or (
        isinstance(exc, httpx.HTTPStatusError)
        and exc.response.status_code in (400, 401)
    )
    if auth_failure:
        logger.warning(
            "%s refresh token rejected (revoked?) — disconnecting; user must reconnect.",
            provider.title(),
        )
        disconnect(session, user_id, provider)
        # Surface the silent failure: scheduled syncs will stop until the user reconnects.
        from backend.core import notifications

        notifications.notify_token_revoked(user_id, provider)
    else:
        logger.error("%s token refresh failed (transient): %s", provider.title(), exc)
