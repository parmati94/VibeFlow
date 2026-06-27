"""Manual sync: kick off one or more playlist syncs, then poll their progress."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.auth import store
from backend.common.auth import require_auth
from backend.core import jobs
from backend.core.spotify_client import SpotifyClient
from backend.deps import get_session
from backend.models.schemas import SyncRequest, SyncRunView, UnmatchedTrack
from backend.models.tables import Mapping, SyncRun, User

router = APIRouter(prefix="/api/sync", tags=["sync"])

_ACTIVE = ("queued", "running")


def _view(run: SyncRun) -> SyncRunView:
    unmatched = [UnmatchedTrack(**u) for u in json.loads(run.unmatched or "[]")]
    return SyncRunView(
        **run.model_dump(exclude={"unmatched", "mapping_id", "trigger", "user_id"}),
        unmatched=unmatched,
        scheduled=run.trigger == "scheduled",
    )


@router.post("", response_model=list[SyncRunView])
def start_sync(
    body: SyncRequest,
    session: Session = Depends(get_session),
    user: User = Depends(require_auth),
) -> list[SyncRunView]:
    if not body.playlist_ids:
        raise HTTPException(status_code=400, detail="No playlists selected.")
    spotify_token = store.valid_spotify_token(session, user.id)
    tidal_token = store.valid_tidal_token(session, user.id)
    if not spotify_token or not tidal_token:
        raise HTTPException(status_code=401, detail="Connect both Spotify and Tidal first.")

    # One cheap call to label the runs with playlist names up front.
    names = {p["id"]: p["name"] for p in SpotifyClient(spotify_token).list_playlists()}

    runs: list[SyncRun] = []
    for pid in body.playlist_ids:
        name = names.get(pid, pid)
        # Find-or-create the Spotify→Tidal link so every sync targets ONE Tidal playlist
        # (no duplicates). A manual-only link has no schedule (frequency=None, enabled=False).
        mapping = session.exec(
            select(Mapping).where(
                Mapping.user_id == user.id, Mapping.spotify_playlist_id == pid
            )
        ).first()
        if mapping is None:
            mapping = Mapping(
                user_id=user.id, spotify_playlist_id=pid, spotify_name=name,
                enabled=False, mode="add",
            )
            session.add(mapping)
            session.commit()
            session.refresh(mapping)
        run = SyncRun(
            user_id=user.id, mapping_id=mapping.id, trigger="manual", mode=body.mode,
            spotify_playlist_id=pid, playlist_name=name,
        )
        session.add(run)
        runs.append(run)
    session.commit()
    for run in runs:
        session.refresh(run)

    jobs.submit([run.id for run in runs])
    return [_view(run) for run in runs]


@router.get("/active", response_model=list[SyncRunView])
def active_runs(
    session: Session = Depends(get_session), user: User = Depends(require_auth)
) -> list[SyncRunView]:
    runs = session.exec(
        select(SyncRun)
        .where(SyncRun.user_id == user.id, SyncRun.status.in_(_ACTIVE))
        .order_by(SyncRun.id)
    ).all()
    return [_view(r) for r in runs]


@router.get("/runs", response_model=list[SyncRunView])
def recent_runs(
    limit: int = 20,
    session: Session = Depends(get_session),
    user: User = Depends(require_auth),
) -> list[SyncRunView]:
    runs = session.exec(
        select(SyncRun)
        .where(SyncRun.user_id == user.id)
        .order_by(SyncRun.id.desc())
        .limit(limit)
    ).all()
    return [_view(r) for r in runs]


@router.get("/runs/{run_id}", response_model=SyncRunView)
def get_run(
    run_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(require_auth),
) -> SyncRunView:
    run = session.get(SyncRun, run_id)
    if not run or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="Run not found.")
    return _view(run)
