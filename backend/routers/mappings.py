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
from backend.models.tables import Mapping, SyncRun

router = APIRouter(prefix="/api/mappings", tags=["mappings"], dependencies=[Depends(require_auth)])


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
def list_mappings(session: Session = Depends(get_session)) -> list[MappingView]:
    mappings = session.exec(select(Mapping).order_by(Mapping.id.desc())).all()
    return [_view(session, m) for m in mappings]


@router.post("", response_model=MappingView)
def create_mapping(
    body: MappingCreate, session: Session = Depends(get_session)
) -> MappingView:
    existing = session.exec(
        select(Mapping).where(Mapping.spotify_playlist_id == body.spotify_playlist_id)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A mapping for this playlist already exists.")
    mapping = Mapping(
        spotify_playlist_id=body.spotify_playlist_id,
        spotify_name=body.spotify_name,
        enabled=body.enabled,
        frequency=body.frequency,
        at_hour=body.at_hour,
        at_minute=body.at_minute,
        day_of_week=body.day_of_week,
        day_of_month=body.day_of_month,
    )
    session.add(mapping)
    session.commit()
    session.refresh(mapping)
    scheduler.schedule_mapping(mapping)
    return _view(session, mapping)


@router.patch("/{mapping_id}", response_model=MappingView)
def update_mapping(
    mapping_id: int, body: MappingUpdate, session: Session = Depends(get_session)
) -> MappingView:
    mapping = session.get(Mapping, mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found.")
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
        mapping.interval_minutes = None  # migrated off the legacy interval
    session.add(mapping)
    session.commit()
    session.refresh(mapping)
    scheduler.schedule_mapping(mapping)
    return _view(session, mapping)


@router.delete("/{mapping_id}", response_model=MessageResponse)
def delete_mapping(
    mapping_id: int, session: Session = Depends(get_session)
) -> MessageResponse:
    mapping = session.get(Mapping, mapping_id)
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found.")
    scheduler.unschedule_mapping(mapping_id)
    session.delete(mapping)
    session.commit()
    return MessageResponse(message="Mapping removed.")


@router.post("/{mapping_id}/run", response_model=MessageResponse)
def run_mapping_now(
    mapping_id: int, session: Session = Depends(get_session)
) -> MessageResponse:
    if not session.get(Mapping, mapping_id):
        raise HTTPException(status_code=404, detail="Mapping not found.")
    run_id = scheduler.trigger_mapping_sync(mapping_id)
    if run_id is None:
        raise HTTPException(status_code=400, detail="Could not start the sync.")
    return MessageResponse(message="Sync started.")
