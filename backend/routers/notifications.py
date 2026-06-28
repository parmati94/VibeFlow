"""Per-user notification settings (Discord webhook + which events to announce)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from backend.common.auth import require_auth
from backend.core import notifications
from backend.deps import get_session
from backend.models.tables import NotificationConfig, User

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationConfigView(BaseModel):
    webhook_url: str | None = None
    enabled: bool = False
    on_failure: bool = True
    on_revocation: bool = True
    on_success: bool = False


class NotificationConfigUpdate(NotificationConfigView):
    pass


class TestRequest(BaseModel):
    webhook_url: str | None = None


def _view(cfg: NotificationConfig | None) -> NotificationConfigView:
    if cfg is None:
        return NotificationConfigView()
    return NotificationConfigView(
        webhook_url=cfg.webhook_url,
        enabled=cfg.enabled,
        on_failure=cfg.on_failure,
        on_revocation=cfg.on_revocation,
        on_success=cfg.on_success,
    )


@router.get("", response_model=NotificationConfigView)
def get_config(
    session: Session = Depends(get_session), user: User = Depends(require_auth)
) -> NotificationConfigView:
    return _view(session.get(NotificationConfig, user.id))


@router.put("", response_model=NotificationConfigView)
def update_config(
    body: NotificationConfigUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(require_auth),
) -> NotificationConfigView:
    webhook = (body.webhook_url or "").strip() or None
    if body.enabled and not webhook:
        raise HTTPException(
            status_code=400, detail="A webhook URL is required to enable notifications."
        )
    cfg = session.get(NotificationConfig, user.id) or NotificationConfig(user_id=user.id)
    cfg.webhook_url = webhook
    cfg.enabled = body.enabled
    cfg.on_failure = body.on_failure
    cfg.on_revocation = body.on_revocation
    cfg.on_success = body.on_success
    session.add(cfg)
    session.commit()
    session.refresh(cfg)
    return _view(cfg)


@router.post("/test")
def send_test(
    body: TestRequest,
    session: Session = Depends(get_session),
    user: User = Depends(require_auth),
) -> dict:
    # Test the URL from the request (so the user can verify before saving); fall back to the
    # saved one if the field is blank.
    webhook = (body.webhook_url or "").strip() or None
    if webhook is None:
        saved = session.get(NotificationConfig, user.id)
        webhook = saved.webhook_url if saved else None
    if not webhook:
        raise HTTPException(status_code=400, detail="Enter a webhook URL to test.")
    if not notifications.send_test(webhook):
        raise HTTPException(
            status_code=502, detail="Discord rejected the test — check the webhook URL."
        )
    return {"success": True}
