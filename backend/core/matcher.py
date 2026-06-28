"""Spotify→Tidal track matching, backed by the TrackMatch cache.

Two tiers:
  1. ISRC — exact recording identity (`GET /v2/tracks?filter[isrc]=`). Trusted, cached.
  2. Scored metadata search — pull ranked Tidal candidates and score each against the
     Spotify track by artist-set match (hard gate), title similarity, and duration. Accept
     the best only above a confidence cutoff; otherwise leave it unmatched rather than
     adding a wrong track.

Cache: ISRC/manual matches are authoritative and short-circuit forever (exact identity).
Metadata matches and misses are the expensive path (a per-track Tidal search), so they're
also served from cache — but only while "fresh": same matcher version and within `_CACHE_TTL`.
This keeps recurring syncs from re-searching every run, while still self-healing — a matcher
change (bump `MATCH_VERSION`) busts them immediately, and the TTL re-resolves periodically to
pick up catalog changes (a previously-missing track that became available).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from sqlmodel import Session

from backend.common.logging_config import logger
from backend.core.tidal_client import TidalClient
from backend.models.tables import TrackMatch

# All bracketed groups + a trailing " - ..." suffix → stripped to get the bare/base title.
# Tidal frequently lists "Beam Me Up" where Spotify has "Beam Me Up (Kill Mode) (Radio
# Edit)", so we also score on the base title and let artist + duration disambiguate version.
_BRACKETS = re.compile(r"[\(\[\{].*?[\)\]\}]")
_DASH_SUFFIX = re.compile(r"\s+-\s+.*$")
# Credits stripped from the *full* title before scoring (they belong to the artist).
_TITLE_CREDITS = re.compile(r"\s*[\(\[](feat|featuring|with)\b.*?[\)\]]", re.IGNORECASE)

# Scoring weights + thresholds.
_W_ARTIST, _W_TITLE, _W_DURATION = 0.5, 0.35, 0.15
_ARTIST_MATCH = 0.85   # per-artist fuzzy threshold to count as the same artist
_TITLE_GATE = 0.6      # below this title similarity, reject outright
_ACCEPT = 0.55         # minimum combined score to accept a candidate
_DURATION_WINDOW = 20  # seconds; |Δ| beyond this scores 0

# Cache freshness for metadata matches + misses (the expensive search path). Bump
# MATCH_VERSION whenever the scoring above changes, so previously-cached metadata/none results
# re-resolve and matcher improvements take effect; _CACHE_TTL re-resolves them periodically
# regardless, to catch Tidal catalog changes. ISRC/manual hits ignore both (exact identity).
MATCH_VERSION = 1
_CACHE_TTL = timedelta(days=7)


def _fold(text: str) -> str:
    """Lowercase, strip diacritics, normalize '&'→'and', drop punctuation, collapse space."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def normalize_title(name: str) -> str:
    """Bare title: drop all bracketed groups and any trailing ' - ...' suffix. Used for the
    search query and as the base-title comparison."""
    cleaned = _DASH_SUFFIX.sub("", _BRACKETS.sub("", name)).strip()
    return cleaned or name.strip()


def _title_score(spotify_title: str, candidate_title: str) -> float:
    """Best of two comparisons: the full titles (rewards an exact version match) and the
    base titles with brackets/suffix stripped (so 'Weapon (Radio Edit)' still matches Tidal's
    bare 'Weapon'). The base path is discounted slightly so an exact full match wins when
    Tidal actually has the specific version."""
    full = _ratio(
        _fold(_TITLE_CREDITS.sub("", spotify_title)),
        _fold(_TITLE_CREDITS.sub("", candidate_title)),
    )
    base = _ratio(_fold(normalize_title(spotify_title)), _fold(normalize_title(candidate_title)))
    return max(full, 0.95 * base)


def _artist_score(spotify_artists: list[str], candidate_artists: list[str]) -> float | None:
    """Set-based artist match in [0,1]. Rewards an exact set and penalizes extra/missing
    artists (so 'Pegboard Nerds' beats 'Pegboard Nerds, Desirée Dawson' for a solo track).
    Returns None when the candidate has no artist data (unknown — caller treats as neutral).
    A real candidate whose artists don't overlap at all scores 0 (a hard reject)."""
    if not candidate_artists or not spotify_artists:
        return None
    sn = [_fold(a) for a in spotify_artists if a]
    cn = [_fold(a) for a in candidate_artists if a]
    if not sn or not cn:
        return None
    matched = sum(
        1 for a in sn if any(_ratio(a, c) >= _ARTIST_MATCH or a in c or c in a for c in cn)
    )
    return matched / max(len(sn), len(cn))


def _duration_score(spotify_ms: int | None, candidate_sec: int | None) -> float:
    if not spotify_ms or not candidate_sec:
        return 0.5  # unknown — neutral
    diff = abs(round(spotify_ms / 1000) - candidate_sec)
    return max(0.0, 1.0 - diff / _DURATION_WINDOW)


def _best_candidate(track: dict, candidates: list[dict]) -> tuple[dict, float] | None:
    """Score candidates; return the highest-scoring (candidate, score) above the cutoff."""
    spotify_artists = track.get("artists", [])
    best: tuple[dict, float] | None = None
    for rank, cand in enumerate(candidates):
        title = _title_score(track["name"], cand["title"])
        if title < _TITLE_GATE:
            logger.debug(
                "  reject #%d %r — title %.2f < gate %.2f", rank, cand["title"], title, _TITLE_GATE
            )
            continue
        artist = _artist_score(spotify_artists, cand["artists"])
        if artist == 0.0:
            logger.debug("  reject #%d %r — no artist overlap %s", rank, cand["title"], cand["artists"])
            continue  # candidate has artists, none match → definitively wrong
        artist_val = 0.5 if artist is None else artist
        duration = _duration_score(track.get("duration_ms"), cand.get("duration"))
        score = _W_ARTIST * artist_val + _W_TITLE * title + _W_DURATION * duration
        # Tiny tiebreak toward Tidal's own ranking.
        score -= rank * 1e-4
        logger.debug(
            "  cand #%d %r — score %.3f (artist %.2f, title %.2f, dur %.2f)",
            rank, cand["title"], score, artist_val, title, duration,
        )
        if best is None or score > best[1]:
            best = (cand, score)
    if best and best[1] >= _ACCEPT:
        return best
    if best:
        logger.debug("  best %.3f < accept %.2f → unmatched", best[1], _ACCEPT)
    return None


def resolve(
    session: Session,
    track: dict,
    tidal: TidalClient,
    *,
    use_cache: bool = True,
    isrc_hits: dict[str, str] | None = None,
) -> tuple[str | None, str]:
    """Return (tidal_id_or_None, matched_by). matched_by ∈ isrc|metadata|cache|none.

    `isrc_hits` is an optional pre-resolved {isrc: tidal_id} map (from a batched lookup); when
    provided, ISRC resolution is a dict hit with no per-track request (a miss means Tidal has
    no track for that ISRC, so we skip the single lookup and fall to metadata)."""
    spotify_id = track["spotify_id"]

    cached = session.get(TrackMatch, spotify_id) if use_cache else None
    if cached:
        # ISRC/manual are exact identity — always authoritative. (Returning the original
        # matched_by keeps run stats counting the hit, not treating it as "uncounted".)
        if cached.tidal_id and cached.matched_by in ("isrc", "manual"):
            return cached.tidal_id, cached.matched_by
        # Metadata matches and confirmed misses cost a Tidal search to recompute and rarely
        # change — serve them from cache while fresh instead of re-searching every run.
        if cached.matched_by in ("metadata", "none") and _is_fresh(cached):
            return cached.tidal_id, cached.matched_by

    isrc = track.get("isrc")
    if isrc:
        tid = isrc_hits.get(isrc) if isrc_hits is not None else tidal.search_by_isrc(isrc)
        if tid:
            _cache(session, spotify_id, isrc, tid, "isrc")
            return tid, "isrc"

    query = f"{normalize_title(track['name'])} {' '.join(track.get('artists', []))}".strip()
    candidates = tidal.search_candidates(query)
    logger.debug(
        "resolve %r (isrc=%s) → no ISRC hit; metadata search %r returned %d candidate(s)",
        track["name"], isrc, query, len(candidates),
    )
    best = _best_candidate(track, candidates)
    if best:
        logger.debug("  matched → %s (score %.3f)", best[0]["id"], best[1])
        _cache(session, spotify_id, isrc, best[0]["id"], "metadata")
        return best[0]["id"], "metadata"

    logger.debug("  unmatched: %r by %s", track["name"], track.get("artists", []))
    _cache(session, spotify_id, isrc, None, "none")
    return None, "none"


def _is_fresh(cached: TrackMatch) -> bool:
    """Whether a cached metadata/none result can be trusted without re-resolving: resolved by
    the current matcher version and within the TTL window. Older rows (e.g. pre-upgrade, where
    matcher_version defaults to 0) fail this and get re-resolved once, then re-cached fresh."""
    if (cached.matcher_version or 0) != MATCH_VERSION:
        return False
    if cached.updated_at is None:
        return False
    return datetime.utcnow() - cached.updated_at < _CACHE_TTL


def _cache(
    session: Session, spotify_id: str, isrc: str | None, tidal_id: str | None, by: str
) -> None:
    row = session.get(TrackMatch, spotify_id) or TrackMatch(spotify_id=spotify_id)
    row.isrc = isrc
    row.tidal_id = tidal_id
    row.matched_by = by
    row.matcher_version = MATCH_VERSION
    row.updated_at = datetime.utcnow()
    session.add(row)
    session.commit()
