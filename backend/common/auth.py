"""App login gate (single shared username/password, session-backed).

Mirrors the lens apps' approach but reuses VibeFlow's existing signed session cookie (from
SessionMiddleware) instead of a second cookie. The logged-in username is stored in the
session under "user" — that key is the seam a future per-user model would hang off of.
"""

from __future__ import annotations

from secrets import compare_digest

from fastapi import Depends, HTTPException, Request, status

from backend.common.config import Settings, get_settings

SESSION_USER_KEY = "user"


def verify_credentials(username: str, password: str, settings: Settings) -> bool:
    """Constant-time check against the configured credentials."""
    return compare_digest(username, settings.auth_username) and compare_digest(
        password, settings.auth_password
    )


def current_user(request: Request, settings: Settings) -> str | None:
    """The session's logged-in identity. When login is disabled everyone is the implicit
    single owner ("owner"); otherwise it's the username from the session, or None."""
    if not settings.enable_login:
        return "owner"
    return request.session.get(SESSION_USER_KEY)


def require_auth(
    request: Request, settings: Settings = Depends(get_settings)
) -> str:
    """Dependency: allow through when login is disabled, else require a session. Returns the
    current user identity (handy once routes become user-scoped)."""
    user = current_user(request, settings)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated."
        )
    return user
