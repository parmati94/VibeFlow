"""SQLite engine + session helpers.

One SQLite file (path from Settings.database_url) holds credentials, mappings, run history,
and the match cache. `check_same_thread=False` so background sync threads can open their own
sessions. Call `init_db()` once at startup to create tables.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine, select

from backend.common.config import get_settings

# Import models so SQLModel.metadata knows every table before create_all().
from backend.models import tables as _tables  # noqa: F401
from backend.models.tables import User

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
    # Add any new columns before bootstrap: _bootstrap_admin() runs an ORM query over User,
    # which references every model column — so a freshly-added column must exist on the table
    # first (on an upgraded DB create_all won't have added it).
    _add_columns()
    admin_id = _bootstrap_admin()
    _migrate(admin_id)


def _bootstrap_admin() -> int:
    """Ensure an admin account exists. On a brand-new instance this creates one empty admin
    (no password) which the first-run setup screen then claims. Returns the admin's id — the
    owner that pre-multi-user data is migrated onto."""
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.is_admin == True)).first()  # noqa: E712
        if admin is None:
            admin = session.exec(select(User)).first()  # any user, if somehow no admin flagged
        if admin is None:
            admin = User(username="admin", password_hash=None, is_admin=True)
            session.add(admin)
            session.commit()
            session.refresh(admin)
        return admin.id


# Columns added after a table first shipped. SQLite create_all() only creates missing
# tables, never new columns, so add them by hand (additive, non-destructive).
_TABLE_ADDS = {
    "user": {
        "allow_duplicates": "BOOLEAN DEFAULT 0",
    },
    "mapping": {
        "frequency": "VARCHAR",
        "at_hour": "INTEGER",
        "at_minute": "INTEGER DEFAULT 0",
        "day_of_week": "INTEGER",
        "day_of_month": "INTEGER",
        "mode": "VARCHAR DEFAULT 'add'",
        "user_id": "INTEGER",
    },
    "syncrun": {
        "trigger": "VARCHAR DEFAULT 'manual'",
        "mode": "VARCHAR DEFAULT 'add'",
        "user_id": "INTEGER",
    },
}


def _add_columns() -> None:
    """Additive schema migration: add columns that postdate a table's first ship. Safe to run
    before bootstrap (no data dependencies). SQLite create_all() only creates missing tables."""
    with engine.begin() as conn:
        for table, adds in _TABLE_ADDS.items():
            existing = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            for col, ddl in adds.items():
                if col not in existing:
                    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")


def _migrate(admin_id: int) -> None:
    """Data migration: attach pre-multi-user rows to the bootstrap admin and rebuild the
    credentials PK. Runs after columns exist and the admin is known."""
    with engine.begin() as conn:
        for table, adds in _TABLE_ADDS.items():
            # Backfill ownership only on tables that actually have a user_id (e.g. not `user`).
            if "user_id" in adds:
                conn.exec_driver_sql(
                    f"UPDATE {table} SET user_id = {admin_id} WHERE user_id IS NULL"
                )
        _migrate_credentials_pk(conn, admin_id)


def _migrate_credentials_pk(conn, admin_id: int) -> None:
    """Old `credentials` had provider as the sole PK (one global account). Rebuild it with a
    composite (user_id, provider) PK, attaching the pre-existing tokens to the bootstrap admin.
    SQLite can't ALTER a primary key, so we rebuild the table. Runs once (skipped once the
    user_id column is present)."""
    cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(credentials)")}
    if not cols or "user_id" in cols:
        return  # fresh table already has the new shape, or nothing to migrate
    conn.exec_driver_sql(
        """
        CREATE TABLE credentials_new (
            user_id INTEGER NOT NULL,
            provider VARCHAR NOT NULL,
            access_token VARCHAR NOT NULL,
            refresh_token VARCHAR,
            expires_at FLOAT,
            scope VARCHAR,
            extra VARCHAR,
            updated_at DATETIME,
            PRIMARY KEY (user_id, provider),
            FOREIGN KEY (user_id) REFERENCES user (id)
        )
        """
    )
    conn.exec_driver_sql(
        f"""
        INSERT INTO credentials_new
            (user_id, provider, access_token, refresh_token, expires_at, scope, extra, updated_at)
        SELECT {admin_id}, provider, access_token, refresh_token, expires_at, scope, extra, updated_at
        FROM credentials
        """
    )
    conn.exec_driver_sql("DROP TABLE credentials")
    conn.exec_driver_sql("ALTER TABLE credentials_new RENAME TO credentials")


def get_session() -> Iterator[Session]:
    """FastAPI dependency: a request-scoped session."""
    with Session(engine) as session:
        yield session


def new_session() -> Session:
    """A standalone session for background threads (own lifecycle, caller closes it)."""
    return Session(engine)
