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
    _migrate()


# Columns added to `mapping` after the table first shipped. SQLite create_all() only creates
# missing tables, never new columns, so add them by hand (additive, non-destructive).
_MAPPING_ADDS = {
    "frequency": "VARCHAR",
    "at_hour": "INTEGER",
    "at_minute": "INTEGER DEFAULT 0",
    "day_of_week": "INTEGER",
    "day_of_month": "INTEGER",
}


def _migrate() -> None:
    with engine.begin() as conn:
        existing = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(mapping)")}
        for col, ddl in _MAPPING_ADDS.items():
            if col not in existing:
                conn.exec_driver_sql(f"ALTER TABLE mapping ADD COLUMN {col} {ddl}")


def get_session() -> Iterator[Session]:
    """FastAPI dependency: a request-scoped session."""
    with Session(engine) as session:
        yield session


def new_session() -> Session:
    """A standalone session for background threads (own lifecycle, caller closes it)."""
    return Session(engine)
