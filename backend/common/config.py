"""Centralised configuration.

One place that reads the environment (and a `.env` file), validates it, and hands typed
settings to the rest of the app. Import `get_settings()` where you need values; it is
cached so the `.env` is read once and validation happens once.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_COMMON = Path(__file__).resolve().parent  # backend/common/
_PKG = _COMMON.parent                      # backend/
_ROOT = _PKG.parent                        # repo root


class Settings(BaseSettings):
    # Environment variables take precedence; the project-root `.env` is canonical, with
    # `backend/.env` read as a fallback. Later entries win.
    model_config = SettingsConfigDict(
        env_file=(_PKG / ".env", _ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Spotify (required for real use; optional at boot so Phase 0 runs bare) ---
    spotify_client_id: str | None = Field(None, alias="SPOTIFY_CLIENT_ID")
    spotify_client_secret: str | None = Field(None, alias="SPOTIFY_CLIENT_SECRET")
    # Spotify forbids "localhost" — the loopback literal 127.0.0.1 (or an HTTPS origin)
    # must match a Redirect URI registered on the Spotify app. Behind nginx this is the
    # single public origin + /auth/spotify/callback.
    spotify_redirect_uri: str = Field(
        "http://127.0.0.1:5570/auth/spotify/callback", alias="SPOTIFY_REDIRECT_URI"
    )

    # --- Tidal (PKCE) ---
    tidal_client_id: str | None = Field(None, alias="TIDAL_CLIENT_ID")
    # Optional: only needed if the Tidal app is registered as confidential (then the token
    # endpoint requires Basic auth). Public apps authenticate with PKCE alone.
    tidal_client_secret: str | None = Field(None, alias="TIDAL_CLIENT_SECRET")
    tidal_redirect_uri: str = Field(
        "http://127.0.0.1:5570/auth/tidal/callback", alias="TIDAL_REDIRECT_URI"
    )
    # Tidal requires a market for every call; default US.
    tidal_country_code: str = Field("US", alias="TIDAL_COUNTRY_CODE")

    # --- Sessions ---
    session_secret: str = Field("dev-secret-change-me", alias="SESSION_SECRET")

    # --- App login gate ---
    # With ENABLE_LOGIN on, the whole app sits behind per-user accounts (stored in the DB,
    # bcrypt-hashed) so a public origin doesn't expose anyone's connected accounts. When off
    # (local/dev), every request runs as the bootstrap admin. Accounts are created in-app
    # (first-run setup + admin-managed users), NOT via env vars.
    enable_login: bool = Field(False, alias="ENABLE_LOGIN")

    # --- Storage ---
    # SQLite file holding credentials, mappings, run history, match cache. Volume-mounted
    # in the container so it survives restarts (the scheduler depends on it).
    database_url: str = Field("sqlite:////app/data/vibeflow.db", alias="DATABASE_URL")

    # --- Logging ---
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    # --- Dev auth bypass (NEVER enable in a real deploy) ---
    # When on, the Spotify "Connect" seeds the session from a pre-captured refresh token
    # instead of running the browser OAuth flow — so a headless box (or one whose redirect
    # URI isn't registered) can authenticate. The refresh-token grant needs no redirect URI,
    # so this works with any client_id/secret the token was minted under (e.g. reuse another
    # app's). Defaults off.
    dev_auth: bool = Field(False, alias="DEV_AUTH")
    spotify_dev_refresh_token: str | None = Field(None, alias="SPOTIFY_DEV_REFRESH_TOKEN")

    @property
    def spotify_dev_login(self) -> bool:
        """Dev Spotify bypass is usable: enabled and a refresh token is configured."""
        return bool(self.dev_auth and self.spotify_dev_refresh_token)

    @property
    def spotify_configured(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)

    @property
    def tidal_configured(self) -> bool:
        return bool(self.tidal_client_id)


@lru_cache
def get_settings() -> Settings:
    """Load and validate settings once."""
    return Settings()  # type: ignore[call-arg]  # values come from env/.env
