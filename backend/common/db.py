"""SQLite engine + session helpers.

One SQLite file (path from Settings.database_url) holds credentials, mappings, run history,
and the match cache. `check_same_thread=False` so background sync threads can open their own
sessions. Call `init_db()` once at startup to create tables.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from backend.common.config import get_settings

# Import models so SQLModel.metadata knows every table before create_all().
from backend.models import tables as _tables  # noqa: F401

_settings = get_settings()

# Ensure the SQLite directory exists (e.g. /app/data) before the engine touches the file.
if _settings.database_url.startswith("sqlite:///"):
    _db_path = Path(_settings.database_url.replace("sqlite:///", "", 1))
    _db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    _settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: a request-scoped session."""
    with Session(engine) as session:
        yield session


def new_session() -> Session:
    """A standalone session for background threads (own lifecycle, caller closes it)."""
    return Session(engine)
