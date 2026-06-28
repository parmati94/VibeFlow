"""Background sync runner.

A single worker thread processes queued SyncRuns sequentially — serializing keeps us off
Tidal's rate limits and makes multi-playlist syncs predictable. Endpoints create the
SyncRun rows, then submit their ids here and return immediately; the UI polls run status.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from sqlmodel import select

from backend.common.db import new_session
from backend.common.logging_config import logger
from backend.core.sync_engine import run_sync
from backend.models.tables import SyncRun

# max_workers=1 → one sync at a time across the whole app.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sync")

# Non-terminal statuses: a run in one of these was mid-flight when the process stopped.
_INTERRUPTED = ("queued", "running")


def submit(run_ids: list[int]) -> None:
    for run_id in run_ids:
        _executor.submit(_safe_run, run_id)


def reconcile_interrupted_runs() -> int:
    """Fail any runs left mid-flight by a restart. The worker queue is in-memory, so a process
    restart strands queued/running SyncRun rows in a non-terminal state forever — the worker
    that would finish them is gone, yet the UI's /active poll keeps surfacing them. Mark them
    errored on startup so they reach a terminal state. Returns the count reconciled."""
    session = new_session()
    try:
        stuck = session.exec(select(SyncRun).where(SyncRun.status.in_(_INTERRUPTED))).all()
        for run in stuck:
            run.status = "error"
            run.error = "Interrupted by a server restart."
            run.finished_at = datetime.utcnow()
            session.add(run)
        if stuck:
            session.commit()
            logger.warning("Reconciled %d interrupted sync run(s) on startup.", len(stuck))
        return len(stuck)
    finally:
        session.close()


def _safe_run(run_id: int) -> None:
    try:
        run_sync(run_id)
    except Exception:  # noqa: BLE001
        logger.exception("Background sync %s failed", run_id)
