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
from backend.models.tables import SyncRun

router = APIRouter(prefix="/api/sync", tags=["sync"], dependencies=[Depends(require_auth)])

_ACTIVE = ("queued", "running")


def _view(run: SyncRun) -> SyncRunView:
    unmatched = [UnmatchedTrack(**u) for u in json.loads(run.unmatched or "[]")]
    return SyncRunView(**run.model_dump(exclude={"unmatched", "mapping_id"}), unmatched=unmatched)


@router.post("", response_model=list[SyncRunView])
def start_sync(
    body: SyncRequest, session: Session = Depends(get_session)
) -> list[SyncRunView]:
    if not body.playlist_ids:
        raise HTTPException(status_code=400, detail="No playlists selected.")
    spotify_token = store.valid_spotify_token(session)
    tidal_token = store.valid_tidal_token(session)
    if not spotify_token or not tidal_token:
        raise HTTPException(status_code=401, detail="Connect both Spotify and Tidal first.")

    # One cheap call to label the runs with playlist names up front.
    names = {p["id"]: p["name"] for p in SpotifyClient(spotify_token).list_playlists()}

    runs: list[SyncRun] = []
    for pid in body.playlist_ids:
        run = SyncRun(spotify_playlist_id=pid, playlist_name=names.get(pid, pid))
        session.add(run)
        runs.append(run)
    session.commit()
    for run in runs:
        session.refresh(run)

    jobs.submit([run.id for run in runs])
    return [_view(run) for run in runs]


@router.get("/active", response_model=list[SyncRunView])
def active_runs(session: Session = Depends(get_session)) -> list[SyncRunView]:
    runs = session.exec(
        select(SyncRun).where(SyncRun.status.in_(_ACTIVE)).order_by(SyncRun.id)
    ).all()
    return [_view(r) for r in runs]


@router.get("/runs", response_model=list[SyncRunView])
def recent_runs(
    limit: int = 20, session: Session = Depends(get_session)
) -> list[SyncRunView]:
    runs = session.exec(
        select(SyncRun).order_by(SyncRun.id.desc()).limit(limit)
    ).all()
    return [_view(r) for r in runs]


@router.get("/runs/{run_id}", response_model=SyncRunView)
def get_run(run_id: int, session: Session = Depends(get_session)) -> SyncRunView:
    run = session.get(SyncRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    return _view(run)
