"""DB-backed token storage + refresh.

Persists each provider's tokens in the Credentials table and hands out a valid access
token on demand, refreshing transparently when expired. This is what lets a headless
scheduled sync authenticate with no browser/session in play.
"""

from __future__ import annotations

import time
from datetime import datetime

from sqlmodel import Session, select

from backend.auth import spotify as spotify_auth
from backend.auth import tidal as tidal_auth
from backend.common.logging_config import logger
from backend.models.tables import Credentials

# Refresh a little early so a token doesn't expire mid-request.
_EXPIRY_SKEW = 60


def _upsert(session: Session, provider: str, **fields) -> Credentials:
    cred = session.get(Credentials, provider)
    if cred is None:
        cred = Credentials(provider=provider, access_token="")
    for key, value in fields.items():
        setattr(cred, key, value)
    cred.updated_at = datetime.utcnow()
    session.add(cred)
    session.commit()
    session.refresh(cred)
    return cred


def save_spotify(session: Session, token_info: dict) -> None:
    _upsert(
        session,
        "spotify",
        access_token=token_info["access_token"],
        refresh_token=token_info.get("refresh_token"),
        expires_at=float(token_info.get("expires_at", 0)),
        scope=token_info.get("scope"),
    )


def save_tidal(session: Session, token: dict, extra: str | None = None) -> None:
    expires_at = time.time() + float(token.get("expires_in", 0))
    _upsert(
        session,
        "tidal",
        access_token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        expires_at=expires_at,
        scope=token.get("scope"),
        extra=extra,
    )


def get_credentials(session: Session, provider: str) -> Credentials | None:
    return session.get(Credentials, provider)


def is_connected(session: Session, provider: str) -> bool:
    return session.exec(
        select(Credentials).where(Credentials.provider == provider)
    ).first() is not None


def disconnect(session: Session, provider: str) -> None:
    cred = session.get(Credentials, provider)
    if cred:
        session.delete(cred)
        session.commit()


def valid_spotify_token(session: Session) -> str | None:
    cred = session.get(Credentials, "spotify")
    if not cred:
        return None
    if cred.expires_at - _EXPIRY_SKEW > time.time():
        return cred.access_token
    if not cred.refresh_token:
        return cred.access_token
    logger.info("Spotify token expired; refreshing.")
    token_info = spotify_auth.refresh(cred.refresh_token)
    # spotipy omits refresh_token from some refresh responses; keep the old one.
    token_info.setdefault("refresh_token", cred.refresh_token)
    save_spotify(session, token_info)
    return token_info["access_token"]


def valid_tidal_token(session: Session) -> str | None:
    cred = session.get(Credentials, "tidal")
    if not cred:
        return None
    if cred.expires_at - _EXPIRY_SKEW > time.time():
        return cred.access_token
    if not cred.refresh_token:
        return cred.access_token
    logger.info("Tidal token expired; refreshing.")
    token = tidal_auth.refresh(cred.refresh_token)
    token.setdefault("refresh_token", cred.refresh_token)
    save_tidal(session, token, extra=cred.extra)
    return token["access_token"]
