"""App login gate (DB-backed per-user accounts, session-backed).

Reuses VibeFlow's signed session cookie (from SessionMiddleware): the logged-in user's id is
stored under "user_id". When the login gate is disabled (ENABLE_LOGIN=false, for local/dev),
every request runs as the bootstrap admin so single-user/DEV_AUTH flows keep working.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from backend.common.config import Settings, get_settings
from backend.core import users
from backend.deps import get_session
from backend.models.tables import User

SESSION_USER_KEY = "user_id"


def current_user(
    request: Request, session: Session, settings: Settings
) -> User | None:
    """The session's logged-in account. When login is disabled everyone is the implicit owner
    (the bootstrap admin); otherwise it's the user from the session, or None."""
    if not settings.enable_login:
        return users.bootstrap_admin(session)
    user_id = request.session.get(SESSION_USER_KEY)
    if user_id is None:
        return None
    return session.get(User, user_id)


def require_auth(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    """Dependency: allow through when login is disabled, else require a session. Returns the
    current user (routes scope their data by `user.id`)."""
    user = current_user(request, session, settings)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated."
        )
    return user


def require_admin(user: User = Depends(require_auth)) -> User:
    """Dependency: require the current user to be an admin (user-management routes)."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required."
        )
    return user
