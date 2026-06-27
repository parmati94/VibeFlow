"""User accounts: password hashing and account management.

Auth is in-app and DB-backed (no external IdP). Passwords are bcrypt-hashed. The bootstrap
admin is created empty (no password) on first launch by `db._bootstrap_admin`; `needs_setup`
reports that pre-setup state so the frontend can show the first-run setup screen.
"""

from __future__ import annotations

import bcrypt
from sqlmodel import Session, func, select

from backend.models.tables import User

# bcrypt hashes at most 72 bytes of input; longer passwords are silently truncated by the
# algorithm. Encode once here so hashing and verification treat input identically.
_MAX_BYTES = 72


def _encode(password: str) -> bytes:
    return password.encode("utf-8")[:_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_encode(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(_encode(password), password_hash.encode("utf-8"))
    except ValueError:
        return False


def authenticate(session: Session, username: str, password: str) -> User | None:
    """Return the user iff the username exists, is set up, and the password matches."""
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def set_password(session: Session, user: User, password: str) -> User:
    user.password_hash = hash_password(password)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_user(
    session: Session, username: str, password: str, *, is_admin: bool = False
) -> User:
    user = User(username=username, password_hash=hash_password(password), is_admin=is_admin)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def get_by_username(session: Session, username: str) -> User | None:
    return session.exec(select(User).where(User.username == username)).first()


def list_users(session: Session) -> list[User]:
    return list(session.exec(select(User).order_by(User.id)).all())


def delete_user(session: Session, user_id: int) -> None:
    user = session.get(User, user_id)
    if user:
        session.delete(user)
        session.commit()


def count_users(session: Session) -> int:
    return session.exec(select(func.count()).select_from(User)).one()


def count_admins(session: Session) -> int:
    return session.exec(
        select(func.count()).select_from(User).where(User.is_admin == True)  # noqa: E712
    ).one()


def bootstrap_admin(session: Session) -> User | None:
    """The implicit owner used when the login gate is disabled — the first admin (lowest id)."""
    admin = session.exec(
        select(User).where(User.is_admin == True).order_by(User.id)  # noqa: E712
    ).first()
    return admin or session.exec(select(User).order_by(User.id)).first()


def needs_setup(session: Session) -> bool:
    """True when no account has a password yet — i.e. the bootstrap admin is unclaimed."""
    return session.exec(
        select(func.count()).select_from(User).where(User.password_hash.is_not(None))
    ).one() == 0
