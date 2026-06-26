"""Tidal OAuth (Authorization Code + PKCE) via httpx.

Tidal's current flow uses PKCE (no client secret): we generate a code_verifier/challenge,
send the challenge on authorize, and the verifier on token exchange. Scopes are dotted
names. See PLANNING.md §7a for the distilled API spec.
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import httpx

from backend.common.config import get_settings

TIDAL_AUTH_URL = "https://login.tidal.com/authorize"
TIDAL_TOKEN_URL = "https://auth.tidal.com/v1/oauth2/token"
TIDAL_SCOPE = "user.read playlists.read playlists.write"


def generate_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for a PKCE S256 exchange."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return verifier, challenge


def login_url(state: str, code_challenge: str) -> str:
    s = get_settings()
    params = {
        "response_type": "code",
        "client_id": s.tidal_client_id,
        "redirect_uri": s.tidal_redirect_uri,
        "scope": TIDAL_SCOPE,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{TIDAL_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str, code_verifier: str) -> dict:
    s = get_settings()
    resp = httpx.post(
        TIDAL_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": s.tidal_redirect_uri,
            "client_id": s.tidal_client_id,
            "code_verifier": code_verifier,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def refresh(refresh_token: str) -> dict:
    s = get_settings()
    resp = httpx.post(
        TIDAL_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": s.tidal_client_id,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
