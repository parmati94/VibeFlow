"""App login endpoints (open — these are the gate itself).

Status drives the SPA: when login is enabled and there's no session, the frontend bounces to
/login.html. Login/logout manage the session identity used by `require_auth`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.common.auth import SESSION_USER_KEY, verify_credentials
from backend.common.config import Settings, get_settings

router = APIRouter(prefix="/api/auth", tags=["app-auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.get("/status")
def auth_status(
    request: Request, settings: Settings = Depends(get_settings)
) -> dict:
    if not settings.enable_login:
        return {"enabled": False, "authenticated": True}
    return {
        "enabled": True,
        "authenticated": request.session.get(SESSION_USER_KEY) is not None,
    }


@router.post("/login")
def login(
    body: LoginRequest, request: Request, settings: Settings = Depends(get_settings)
) -> dict:
    if not settings.enable_login:
        raise HTTPException(status_code=400, detail="Login is not enabled.")
    if not verify_credentials(body.username, body.password, settings):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    request.session[SESSION_USER_KEY] = body.username
    return {"success": True, "username": body.username}


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.pop(SESSION_USER_KEY, None)
    return {"success": True}
