"""Background sync runner.

A single worker thread processes queued SyncRuns sequentially — serializing keeps us off
Tidal's rate limits and makes multi-playlist syncs predictable. Endpoints create the
SyncRun rows, then submit their ids here and return immediately; the UI polls run status.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from backend.common.logging_config import logger
from backend.core.sync_engine import run_sync

# max_workers=1 → one sync at a time across the whole app.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="sync")


def submit(run_ids: list[int]) -> None:
    for run_id in run_ids:
        _executor.submit(_safe_run, run_id)


def _safe_run(run_id: int) -> None:
    try:
        run_sync(run_id)
    except Exception:  # noqa: BLE001
        logger.exception("Background sync %s failed", run_id)
