"""APScheduler-driven auto-sync.

Each enabled Mapping with an interval gets a job that periodically enqueues a sync. Jobs are
held in memory and rebuilt from the DB on startup (the Mapping table is the source of truth),
so no separate job store is needed. The actual sync runs through the same single-worker queue
as manual syncs (`core.jobs`), so scheduled and manual runs never overlap.
"""

from __future__ import annotations

from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import select

from backend.common.db import new_session
from backend.common.logging_config import logger
from backend.core import jobs
from backend.models.tables import Mapping, SyncRun

_scheduler = BackgroundScheduler(daemon=True)


def _job_id(mapping_id: int) -> str:
    return f"mapping-{mapping_id}"


def start() -> None:
    if not _scheduler.running:
        _scheduler.start()
    reload_jobs()
    logger.info("Scheduler started with %d job(s).", len(_scheduler.get_jobs()))


def shutdown() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)


def reload_jobs() -> None:
    """Rebuild all jobs from the enabled mappings (called on startup)."""
    for job in _scheduler.get_jobs():
        job.remove()
    session = new_session()
    try:
        mappings = session.exec(select(Mapping).where(Mapping.enabled == True)).all()  # noqa: E712
        for m in mappings:
            schedule_mapping(m)
    finally:
        session.close()


def schedule_mapping(mapping: Mapping) -> None:
    """Add or replace the job for one mapping. Disabled / interval-less mappings are removed."""
    unschedule_mapping(mapping.id)
    if not (mapping.enabled and mapping.interval_minutes):
        return
    _scheduler.add_job(
        trigger_mapping_sync,
        trigger=IntervalTrigger(minutes=mapping.interval_minutes),
        id=_job_id(mapping.id),
        args=[mapping.id],
        replace_existing=True,
        coalesce=True,          # if runs pile up, collapse to one
        max_instances=1,
    )


def unschedule_mapping(mapping_id: int) -> None:
    job = _scheduler.get_job(_job_id(mapping_id))
    if job:
        job.remove()


def next_run_at(mapping_id: int) -> datetime | None:
    job = _scheduler.get_job(_job_id(mapping_id))
    return job.next_run_time if job else None


def trigger_mapping_sync(mapping_id: int) -> int | None:
    """Create a SyncRun for the mapping and enqueue it. Returns the run id (or None if the
    mapping vanished/was disabled). Used by both the scheduler and the manual "run now"."""
    session = new_session()
    try:
        mapping = session.get(Mapping, mapping_id)
        if mapping is None:
            return None
        run = SyncRun(
            mapping_id=mapping.id,
            spotify_playlist_id=mapping.spotify_playlist_id,
            playlist_name=mapping.spotify_name,
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    finally:
        session.close()
    jobs.submit([run_id])
    return run_id
