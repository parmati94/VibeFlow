"""Tidal OAuth (Authorization Code + PKCE) via httpx.

We generate a code_verifier/challenge, send the challenge on authorize, and the verifier on
token exchange. With PKCE the verifier proves the client, so a public app needs only the
client_id. If the Tidal app is registered as confidential, its token endpoint also requires
HTTP Basic auth (client_id:client_secret) — so a TIDAL_CLIENT_SECRET, when configured, is
sent as Basic auth and PKCE still applies. Scopes are dotted names. See PLANNING.md §7a.
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


def _token_request(data: dict) -> dict:
    """POST to the token endpoint. When a client secret is configured, authenticate the
    client via HTTP Basic (confidential app); otherwise rely on PKCE alone (public app)."""
    s = get_settings()
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if s.tidal_client_secret:
        basic = base64.b64encode(
            f"{s.tidal_client_id}:{s.tidal_client_secret}".encode()
        ).decode()
        headers["Authorization"] = f"Basic {basic}"
    else:
        # Public client: identify via client_id in the body.
        data = {**data, "client_id": s.tidal_client_id}
    resp = httpx.post(TIDAL_TOKEN_URL, data=data, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


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
    return _token_request(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": s.tidal_redirect_uri,
            "code_verifier": code_verifier,
        }
    )


def refresh(refresh_token: str) -> dict:
    return _token_request(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    )
