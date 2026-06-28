"""FastAPI application entry point.

Creates the app, wires session middleware, initializes the DB, and includes the routers.
Business logic lives in `core/`; OAuth/token handling in `auth/`; route handlers in
`routers/` stay thin. Run with `uvicorn backend.main:app`.

URL scheme (same-origin behind nginx):
  /auth/spotify/*, /auth/tidal/*   OAuth round-trips (proxied as-is)
  /api/*                           JSON endpoints called by the frontend
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from backend.common.config import get_settings
from backend.common.db import init_db
from backend.common.logging_config import logger, setup_logging
from backend.core import jobs, scheduler
from backend.routers import (
    appauth,
    mappings,
    notifications,
    oauth,
    playlists,
    sync,
    system,
    users,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Re-apply the level from Settings so the configured LOG_LEVEL actually drives logging
    # (the import-time setup_logging() runs before Settings is loaded).
    setup_logging(settings.log_level)
    init_db()
    logger.info("VibeFlow starting up (db ready).")
    # Fail any runs stranded mid-flight by the previous shutdown — the in-memory worker
    # queue doesn't survive a restart, so those rows would never reach a terminal state.
    jobs.reconcile_interrupted_runs()
    if settings.dev_auth:
        logger.warning(
            "DEV_AUTH enabled — Spotify 'Connect' uses the refresh-token bypass, "
            "not real OAuth. Never enable this in a real deploy."
        )
    if settings.enable_login:
        logger.info("Login gate ENABLED (per-user accounts; first run shows setup screen).")
    else:
        logger.warning(
            "Login gate DISABLED — anyone who can reach this origin acts as the bootstrap "
            "admin with full access. Set ENABLE_LOGIN=true on a public deploy."
        )
    scheduler.start()
    yield
    scheduler.shutdown()
    logger.info("VibeFlow shutting down.")


app = FastAPI(title="VibeFlow", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    https_only=False,  # cookie works over HTTPS without Secure; set True to harden
)

app.include_router(system.router)
app.include_router(appauth.router)
app.include_router(users.router)
app.include_router(oauth.router)
app.include_router(playlists.router)
app.include_router(sync.router)
app.include_router(mappings.router)
app.include_router(notifications.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
