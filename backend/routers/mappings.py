"""Scheduled-sync mappings: saved Spotify→Tidal links that auto-sync on an interval."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.common.auth import require_auth
from backend.core import scheduler
from backend.deps import get_session
from backend.models.schemas import (
    MappingCreate,
    MappingUpdate,
    MappingView,
    MessageResponse,
)
from backend.models.tables import Mapping, SyncRun, User

router = APIRouter(prefix="/api/mappings", tags=["mappings"])


def _owned(session: Session, mapping_id: int, user: User) -> Mapping:
    """Fetch a mapping, 404ing if it doesn't exist or belongs to another user."""
    mapping = session.get(Mapping, mapping_id)
    if not mapping or mapping.user_id != user.id:
        raise HTTPException(status_code=404, detail="Mapping not found.")
    return mapping


def _last_status(session: Session, mapping_id: int) -> str | None:
    run = session.exec(
        select(SyncRun)
        .where(SyncRun.mapping_id == mapping_id)
        .order_by(SyncRun.id.desc())
    ).first()
    return run.status if run else None


def _view(session: Session, m: Mapping) -> MappingView:
    return MappingView(
        **m.model_dump(),
        last_status=_last_status(session, m.id),
        next_run_at=scheduler.next_run_at(m.id),
    )


@router.get("", response_model=list[MappingView])
def list_mappings(
    session: Session = Depends(get_session), user: User = Depends(require_auth)
) -> list[MappingView]:
    # Only scheduled links appear on the Schedules page; manual-only links (frequency=None,
    # created by "Sync once" to dedupe the Tidal playlist) stay hidden.
    mappings = session.exec(
        select(Mapping)
        .where(Mapping.user_id == user.id, Mapping.frequency.is_not(None))
        .order_by(Mapping.id.desc())
    ).all()
    return [_view(session, m) for m in mappings]


@router.post("", response_model=MappingView)
def create_mapping(
    body: MappingCreate,
    session: Session = Depends(get_session),
    user: User = Depends(require_auth),
) -> MappingView:
    # Upsert by playlist: a "Sync once" may have already created a (manual-only) link for this
    # playlist — scheduling it upgrades that same link rather than making a second one.
    mapping = session.exec(
        select(Mapping).where(
            Mapping.user_id == user.id,
            Mapping.spotify_playlist_id == body.spotify_playlist_id,
        )
    ).first()
    if mapping is None:
        mapping = Mapping(
            user_id=user.id,
            spotify_playlist_id=body.spotify_playlist_id,
            spotify_name=body.spotify_name,
        )
        session.add(mapping)
    mapping.spotify_name = body.spotify_name
    mapping.enabled = body.enabled
    mapping.mode = body.mode
    mapping.frequency = body.frequency
    mapping.at_hour = body.at_hour
    mapping.at_minute = body.at_minute
    mapping.day_of_week = body.day_of_week
    mapping.day_of_month = body.day_of_month
    session.commit()
    session.refresh(mapping)
    scheduler.schedule_mapping(mapping)
    return _view(session, mapping)


@router.patch("/{mapping_id}", response_model=MappingView)
def update_mapping(
    mapping_id: int,
    body: MappingUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(require_auth),
) -> MappingView:
    mapping = _owned(session, mapping_id, user)
    if body.enabled is not None:
        mapping.enabled = body.enabled
    # A schedule edit always sends the full set; only overwrite when a frequency is provided
    # (so an enable/disable-only PATCH doesn't wipe the schedule).
    if body.frequency is not None:
        mapping.frequency = body.frequency
        mapping.at_hour = body.at_hour
        mapping.at_minute = body.at_minute
        mapping.day_of_week = body.day_of_week
        mapping.day_of_month = body.day_of_month
        mapping.mode = body.mode
        mapping.interval_minutes = None  # migrated off the legacy interval
    session.add(mapping)
    session.commit()
    session.refresh(mapping)
    scheduler.schedule_mapping(mapping)
    return _view(session, mapping)


@router.delete("/{mapping_id}", response_model=MessageResponse)
def delete_mapping(
    mapping_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_auth),
) -> MessageResponse:
    """Remove the schedule. The Spotify→Tidal link is kept (frequency cleared) so manual
    syncs still target the same Tidal playlist instead of creating a duplicate."""
    mapping = _owned(session, mapping_id, user)
    scheduler.unschedule_mapping(mapping_id)
    mapping.frequency = None
    mapping.enabled = False
    mapping.at_hour = None
    mapping.at_minute = 0
    mapping.day_of_week = None
    mapping.day_of_month = None
    session.add(mapping)
    session.commit()
    return MessageResponse(message="Schedule removed.")


@router.post("/{mapping_id}/run", response_model=MessageResponse)
def run_mapping_now(
    mapping_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_auth),
) -> MessageResponse:
    _owned(session, mapping_id, user)
    run_id = scheduler.trigger_mapping_sync(mapping_id)
    if run_id is None:
        raise HTTPException(status_code=400, detail="Could not start the sync.")
    return MessageResponse(message="Sync started.")
