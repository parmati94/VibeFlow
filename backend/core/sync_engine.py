"""Execute one SyncRun: Spotify playlist → Tidal playlist.

Reuses the Tidal playlist from a Mapping when present (and only adds new tracks via diff
detection); otherwise creates a fresh Tidal playlist. Progress is written to the SyncRun
row as it goes so the UI can poll a live progress bar. Runs in a background thread with its
own DB session.
"""

from __future__ import annotations

import json
from datetime import datetime

from backend.auth import store
from backend.common.db import new_session
from backend.common.logging_config import logger
from backend.core import matcher
from backend.core.spotify_client import SpotifyClient
from backend.core.tidal_client import TidalClient
from backend.models.tables import Mapping, SyncRun


def run_sync(run_id: int) -> None:
    session = new_session()
    try:
        run = session.get(SyncRun, run_id)
        if run is None:
            return
        run.status = "running"
        run.started_at = datetime.utcnow()
        session.add(run)
        session.commit()

        spotify_token = store.valid_spotify_token(session, run.user_id)
        tidal_token = store.valid_tidal_token(session, run.user_id)
        if not spotify_token or not tidal_token:
            _fail(session, run, "Both Spotify and Tidal must be connected.")
            return

        spotify = SpotifyClient(spotify_token)
        tidal = TidalClient(tidal_token)
        try:
            _execute(session, run, spotify, tidal)
        finally:
            tidal.close()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Sync run %s crashed", run_id)
        run = session.get(SyncRun, run_id)
        if run:
            _fail(session, run, str(exc))
    finally:
        session.close()


def _execute(session, run: SyncRun, spotify: SpotifyClient, tidal: TidalClient) -> None:
    mapping = session.get(Mapping, run.mapping_id) if run.mapping_id else None

    details = spotify.get_playlist(run.spotify_playlist_id)
    tracks = spotify.get_tracks(run.spotify_playlist_id)
    run.total = len(tracks)
    run.playlist_name = details["name"]
    session.add(run)
    session.commit()

    # Target Tidal playlist: reuse the mapping's if it still exists (diff against its
    # current tracks), otherwise create a fresh one. Re-checking existence handles a
    # playlist that was deleted in the Tidal app since the last run.
    existing: set[str] = set()
    items: list[dict] = []  # {track_id, item_id} of the reused playlist (for mirror removal)
    reuse = bool(
        mapping
        and mapping.tidal_playlist_id
        and tidal.playlist_exists(mapping.tidal_playlist_id)
    )
    if reuse:
        tidal_playlist_id = mapping.tidal_playlist_id
        items = tidal.playlist_items(tidal_playlist_id)
        existing = {it["track_id"] for it in items}
    else:
        tidal_playlist_id = tidal.create_playlist(
            details["name"], details.get("description")
        )
        if mapping:
            mapping.tidal_playlist_id = tidal_playlist_id
            mapping.tidal_name = details["name"]
            session.add(mapping)
    run.tidal_playlist_id = tidal_playlist_id
    session.add(run)
    session.commit()

    # Resolve every ISRC in one batched pass (one request per ~20 tracks) instead of a
    # lookup per track — keeps us well under Tidal's rate limit. Only ISRC-misses then
    # need a per-track metadata search.
    isrc_hits = tidal.tracks_by_isrc([t["isrc"] for t in tracks if t.get("isrc")])

    desired: set[str] = set()        # every source track's Tidal id (the target set)
    to_add: list[str] = []           # new ids to append, in source order
    queued: set[str] = set()         # dedupe adds within this run
    unmatched: list[dict] = []
    for idx, track in enumerate(tracks, start=1):
        tidal_id, matched_by = matcher.resolve(session, track, tidal, isrc_hits=isrc_hits)
        if matched_by == "isrc":
            run.matched_isrc += 1
        elif matched_by == "metadata":
            run.matched_meta += 1

        if tidal_id:
            desired.add(tidal_id)
            if tidal_id not in existing and tidal_id not in queued:
                to_add.append(tidal_id)
                queued.add(tidal_id)
        else:
            run.not_found += 1
            unmatched.append({"name": track["name"], "artists": track.get("artists", [])})

        run.processed = idx
        if idx % 5 == 0 or idx == run.total:
            session.add(run)
            session.commit()

    if to_add:
        tidal.add_tracks(tidal_playlist_id, to_add)
    run.added = len(to_add)

    # Mirror mode: drop tracks no longer in the source (only meaningful when reusing a
    # playlist that already had tracks). Add-only mode leaves existing tracks alone.
    if run.mode == "mirror" and reuse:
        to_remove = [it for it in items if it["track_id"] not in desired]
        if to_remove:
            tidal.remove_items(tidal_playlist_id, to_remove)
            logger.info("Mirror: removed %d track(s) no longer in source", len(to_remove))

    run.unmatched = json.dumps(unmatched)
    run.status = "partial" if run.not_found else "success"
    run.finished_at = datetime.utcnow()
    session.add(run)

    if mapping:
        mapping.last_run_at = datetime.utcnow()
        session.add(mapping)
    session.commit()
    logger.info(
        "Sync run %s done: %d added, %d unmatched of %d",
        run.id, run.added, run.not_found, run.total,
    )


def _fail(session, run: SyncRun, message: str) -> None:
    run.status = "error"
    run.error = message
    run.finished_at = datetime.utcnow()
    session.add(run)
    session.commit()
