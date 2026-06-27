"""Admin-only user management. No public sign-up — the admin creates accounts here."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from backend.common.auth import require_admin
from backend.core import users
from backend.deps import get_session
from backend.models.tables import User

router = APIRouter(
    prefix="/api/users", tags=["users"], dependencies=[Depends(require_admin)]
)


class UserView(BaseModel):
    id: int
    username: str
    is_admin: bool


class CreateUserRequest(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class ResetPasswordRequest(BaseModel):
    new_password: str


def _view(u: User) -> UserView:
    return UserView(id=u.id, username=u.username, is_admin=u.is_admin)


@router.get("", response_model=list[UserView])
def list_users(session: Session = Depends(get_session)) -> list[UserView]:
    return [_view(u) for u in users.list_users(session)]


@router.post("", response_model=UserView)
def create_user(
    body: CreateUserRequest, session: Session = Depends(get_session)
) -> UserView:
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(status_code=400, detail="Username and password are required.")
    if users.get_by_username(session, username):
        raise HTTPException(status_code=409, detail="That username is already taken.")
    user = users.create_user(session, username, body.password, is_admin=body.is_admin)
    return _view(user)


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
) -> dict:
    target = session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="You can't delete your own account.")
    if target.is_admin and users.count_admins(session) <= 1:
        raise HTTPException(status_code=400, detail="Can't delete the last admin.")
    users.delete_user(session, user_id)
    return {"success": True}


@router.post("/{user_id}/password")
def reset_password(
    user_id: int,
    body: ResetPasswordRequest,
    session: Session = Depends(get_session),
) -> dict:
    target = session.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if not body.new_password:
        raise HTTPException(status_code=400, detail="A new password is required.")
    users.set_password(session, target, body.new_password)
    return {"success": True}
