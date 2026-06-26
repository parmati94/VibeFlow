# VibeFlow 🎵

Self-hosted web app that syncs your **Spotify playlists to Tidal** — on demand or on a
schedule — with high-accuracy track matching.

Runs as a single Docker container (nginx + FastAPI behind supervisord). Bring your own
Spotify and Tidal developer apps.

## Features

- 🔐 OAuth for both Spotify and Tidal; tokens persisted server-side, so scheduled syncs keep
  running without re-logging in.
- 🎯 **Accurate matching** — ISRC first, then a scored search on **artist + title + duration**
  (matches a remix vs. the original, the right artist among same-title tracks, and falls back
  to the base title when Tidal lacks Spotify's `(Radio Edit)`-style suffix). Low-confidence
  guesses are left unmatched rather than added wrong.
- ⏱ **Scheduled auto-sync** — keep a playlist in sync on an interval; only new tracks are
  added each run (diff detection).
- ⚡ **Match cache** — repeat syncs skip already-resolved tracks.
- 📊 Run history with per-run stats and an unmatched-tracks list.
- 🔒 Optional username/password **login gate** for public deployments.
- 🎨 Clean dark UI (Home / Sync once / Scheduled / History).

## Architecture

```
Browser ── nginx ──┬── /              static SPA (Alpine + Vite + Tailwind)
                   └── /api, /auth/*  → uvicorn (FastAPI)
                                         ├── core/     sync engine, matcher, scheduler
                                         ├── auth/     Spotify (spotipy) + Tidal (PKCE)
                                         └── SQLite    credentials, mappings, runs, match cache
```

One container, run by **supervisord** (nginx + uvicorn). State lives in a SQLite file on a
mounted volume.

## Quick start

```bash
git clone https://github.com/parmati94/VibeFlow.git && cd VibeFlow
cp .env.example .env        # then fill in your credentials (see below)
docker compose up -d        # serves on http://127.0.0.1:5570
```

Open `http://127.0.0.1:5570`, connect Spotify and Tidal, then sync.

## Configuration

Credentials go in `.env` (git-ignored); non-secret config is set in the compose file.

| Variable | Required | Notes |
|---|---|---|
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | yes | From the [Spotify dashboard](https://developer.spotify.com/dashboard). |
| `TIDAL_CLIENT_ID` | yes | From the [Tidal dashboard](https://developer.tidal.com/dashboard). PKCE — no secret needed for a public app. |
| `TIDAL_CLIENT_SECRET` | no | Only if your Tidal app is "confidential". |
| `SESSION_SECRET` | yes | Random string; signs the session cookie. |
| `SPOTIFY_REDIRECT_URI` / `TIDAL_REDIRECT_URI` | yes | Set in the compose file. Must exactly match the URIs registered on each app. |
| `ENABLE_LOGIN` / `USERNAME` / `PASSWORD` | recommended | Password-gate the app (see Security). |
| `TIDAL_COUNTRY_CODE` | no | Market for Tidal catalog calls (default `US`). |
| `LOG_LEVEL` | no | `INFO` / `DEBUG`. |

### Register the redirect URIs

Add these to your Spotify and Tidal apps, matching the origin you serve from:

- `<origin>/auth/spotify/callback`
- `<origin>/auth/tidal/callback`

Spotify rejects `localhost` and bare LAN IPs for `http` — use the loopback literal
(`http://127.0.0.1:5570/...`) for local use, or an **HTTPS** origin behind a reverse proxy.
Tidal requires HTTPS (no localhost / private IPs), so a real domain is needed to connect Tidal.

## Run modes

| File | Use |
|---|---|
| `docker-compose.yml` | Prod — pulls the prebuilt `parmati/vibeflow:latest` image. |
| `docker-compose.dev.yml` | Local dev — builds with hot reload (uvicorn `--reload`), bind-mounts source. |
| `docker-compose.local.yml` | Personal deploy (git-ignored). |

For dev, rebuild the frontend after UI edits: `cd frontend && npm install && npm run build`.

## Security

The app is **single-user**: anyone who can reach it controls the connected accounts. If you
expose it on a public origin, enable the login gate:

```env
ENABLE_LOGIN=true
USERNAME=you
PASSWORD=a-strong-password
```

(Multi-user — isolated per-visitor accounts — is on the roadmap; see `PLANNING.md`.)

## How matching works

1. **ISRC** — exact recording identity via Tidal's `filter[isrc]`. Most matches land here.
2. **Scored search** — pulls ranked Tidal candidates and scores each by artist-set match
   (a hard gate), title similarity (full vs. base title), and duration closeness. The best
   candidate above a confidence threshold wins; otherwise the track is reported as unmatched.

Results are cached per Spotify track. ISRC/manual matches are trusted on re-sync; metadata
matches and misses are re-checked, so matching improvements self-heal.

## Disclaimer

Not affiliated with Spotify or Tidal. Use at your own risk and follow each service's Terms.
