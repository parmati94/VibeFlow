"""Per-user Discord webhook notifications.

Best-effort by design: a webhook POST never raises into the caller — a failed notification
must not break a sync run or a token refresh. Each event looks up the owner's
NotificationConfig and only fires when notifications are enabled and that event is opted in.
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from backend.common.config import get_settings
from backend.common.db import new_session
from backend.common.logging_config import logger
from backend.models.tables import NotificationConfig, SyncRun

_TIMEOUT = 10.0

# Discord embed accent colors.
_RED = 0xEF4444
_AMBER = 0xF59E0B
_GREEN = 0x10B981

_TERMINAL = {"success", "partial", "error"}


def _enabled_config(session, user_id: int) -> NotificationConfig | None:
    """The user's config only if it's usable (enabled + has a webhook); else None."""
    cfg = session.get(NotificationConfig, user_id)
    if cfg and cfg.enabled and cfg.webhook_url:
        return cfg
    return None


def _post(webhook_url: str, embed: dict) -> bool:
    """POST one embed to a Discord webhook. Brands every message with the app logo (sender
    avatar + an author line) and a timestamped footer. Returns success; never raises."""
    avatar = get_settings().notify_avatar_url
    embed.setdefault("author", {"name": "VibeFlow", "icon_url": avatar})
    embed.setdefault("footer", {"text": "VibeFlow"})
    embed.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    payload = {"username": "VibeFlow", "avatar_url": avatar, "embeds": [embed]}
    try:
        resp = httpx.post(webhook_url, json=payload, timeout=_TIMEOUT)
        if resp.status_code >= 400:
            logger.warning(
                "Discord webhook returned %s: %s", resp.status_code, resp.text[:200]
            )
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Discord webhook failed: %s", exc)
        return False


def _tidal_url(playlist_id: str | None) -> str | None:
    """Public Tidal playlist link. Opens the native app on mobile (universal link), the web
    player on desktop. Discord only makes http(s) links clickable, so this is the right form."""
    return f"https://tidal.com/playlist/{playlist_id}" if playlist_id else None


def notify_run_finished(run_id: int) -> None:
    """Announce a finished sync run to its owner, if their config opts in. Errors fire the
    `on_failure` event; success/partial fire `on_success` (off by default — completions are
    frequent). Opens its own session since the sync's session is already closed by now."""
    session = new_session()
    try:
        run = session.get(SyncRun, run_id)
        if run is None or run.status not in _TERMINAL:
            return
        cfg = _enabled_config(session, run.user_id)
        if cfg is None:
            return

        if run.status == "error":
            if not cfg.on_failure:
                return
            embed = {
                "title": run.playlist_name,
                "description": f"Sync failed — {run.error or 'unknown error'}",
                "color": _RED,
            }
        else:  # success | partial
            if not cfg.on_success:
                return
            matched = run.matched_isrc + run.matched_meta
            embed = {
                "title": run.playlist_name,
                "description": (
                    f"Synced to Tidal  ·  **{run.added}** added, "
                    f"**{matched}** matched, **{run.not_found}** unmatched"
                ),
                "color": _AMBER if run.status == "partial" else _GREEN,
            }
        url = _tidal_url(run.tidal_playlist_id)
        if url:
            embed["url"] = url
        _post(cfg.webhook_url, embed)
    finally:
        session.close()


def notify_token_revoked(user_id: int, provider: str) -> None:
    """Announce that a provider connection was rejected (token revoked) and needs reconnecting.
    Fires the `on_revocation` event. Opens its own session for isolation from the caller."""
    session = new_session()
    try:
        cfg = _enabled_config(session, user_id)
        if cfg is None or not cfg.on_revocation:
            return
        name = provider.title()
        _post(
            cfg.webhook_url,
            {
                "title": f"{name} disconnected",
                "description": (
                    f"VibeFlow's {name} connection was rejected (likely revoked or a changed "
                    f"password). Scheduled syncs will stop until you reconnect {name} in VibeFlow."
                ),
                "color": _AMBER,
            },
        )
    finally:
        session.close()


def send_test(webhook_url: str) -> bool:
    """Send a test embed to an arbitrary webhook (used by the 'Send test' button before the
    config is necessarily saved). Returns whether Discord accepted it."""
    return _post(
        webhook_url,
        {
            "title": "Test notification",
            "description": "Your webhook is wired up correctly.",
            "color": _GREEN,
        },
    )
