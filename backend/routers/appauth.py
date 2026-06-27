"""App login endpoints (open — these are the gate itself).

Status drives the SPA: when login is enabled and there's no session, the frontend bounces to
/login.html (or its setup mode when no account is set up yet). Login/setup manage the session
identity used by `require_auth`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session

from backend.common.auth import SESSION_USER_KEY, current_user
from backend.common.config import Settings, get_settings
from backend.core import users
from backend.deps import get_session

router = APIRouter(prefix="/api/auth", tags=["app-auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class SetupRequest(BaseModel):
    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@router.get("/status")
def auth_status(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    user = current_user(request, session, settings)
    return {
        "enabled": settings.enable_login,
        "authenticated": user is not None,
        "needs_setup": users.needs_setup(session),
        "user": (
            {"id": user.id, "username": user.username, "is_admin": user.is_admin}
            if user
            else None
        ),
    }


@router.post("/setup")
def setup(
    body: SetupRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    """First-run: claim the empty bootstrap admin by setting its username + password. Only
    works while no account has been set up; afterwards new users come from the admin panel."""
    if not users.needs_setup(session):
        raise HTTPException(status_code=400, detail="Setup has already been completed.")
    admin = users.bootstrap_admin(session)
    if admin is None:  # defensive — bootstrap runs at startup
        raise HTTPException(status_code=500, detail="No admin account to set up.")
    admin.username = body.username
    admin.is_admin = True
    users.set_password(session, admin, body.password)
    request.session[SESSION_USER_KEY] = admin.id
    return {"success": True, "username": admin.username}


@router.post("/login")
def login(
    body: LoginRequest, request: Request, session: Session = Depends(get_session)
) -> dict:
    user = users.authenticate(session, body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    request.session[SESSION_USER_KEY] = user.id
    return {"success": True, "username": user.username, "is_admin": user.is_admin}


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.pop(SESSION_USER_KEY, None)
    return {"success": True}


@router.post("/password")
def change_password(
    body: PasswordChangeRequest,
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Change the current user's own password."""
    user = current_user(request, session, settings)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")
    if not users.verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    users.set_password(session, user, body.new_password)
    return {"success": True}
