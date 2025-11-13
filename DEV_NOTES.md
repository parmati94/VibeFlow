# Development Notes

## Architecture Overview

### Monorepo Structure
- Uses npm workspaces for managing frontend and backend together
- Single `package.json` at root for running both simultaneously
- Shared `.gitignore` and documentation

### Backend (Node.js + Express)
- **Port**: 3001
- **Session-based auth**: Stores OAuth tokens in Express sessions
- **Modular architecture**: Separate routes and services

#### Key Files:
- `src/index.js` - Server entry point, middleware setup
- `src/routes/spotifyAuth.js` - Spotify OAuth flow
- `src/routes/tidalAuth.js` - Tidal OAuth flow
- `src/routes/playlists.js` - Get playlists from both services
- `src/routes/sync.js` - Trigger playlist sync
- `src/services/spotifyService.js` - Spotify API interactions
- `src/services/tidalService.js` - Tidal API interactions
- `src/services/syncService.js` - Core sync logic with matching algorithm

### Frontend (React + Vite)
- **Port**: 5173
- **Build tool**: Vite for fast HMR and builds
- **State management**: React hooks (useState, useEffect)
- **API proxy**: Vite proxies `/auth` and `/api` to backend

#### Key Files:
- `src/App.jsx` - Main app component, auth state
- `src/components/AuthSection.jsx` - OAuth buttons for both services
- `src/components/PlaylistSelector.jsx` - Display and select playlists
- `src/components/SyncSection.jsx` - Sync UI and results
- `src/api.js` - Axios-based API client

## Track Matching Algorithm

The sync service uses a two-tier approach:

1. **ISRC Matching (Primary)**
   - ISRC = International Standard Recording Code
   - Unique identifier for each recording
   - Most accurate, but not always available
   - Direct lookup on Tidal

2. **Metadata Matching (Fallback)**
   - Search by: track name + artist names
   - Returns top 5 results, tries to find exact match
   - Falls back to first result if no exact match
   - Less accurate but better coverage

### Why this works:
- ISRC catches ~70-80% of tracks with perfect accuracy
- Metadata search catches most of the remaining ~15-20%
- Only ~5-10% typically can't be matched (regional differences, exclusives)

## API Endpoints

### Authentication Flow

**Spotify:**
1. `GET /auth/spotify/login` → Returns auth URL
2. User authorizes on Spotify
3. Spotify redirects to `GET /auth/spotify/callback`
4. Exchange code for tokens, store in session
5. Redirect to frontend with success param

**Tidal:** Same flow with tidal endpoints

### Session Management
- Sessions stored in memory (use Redis for production)
- Session includes:
  - `spotifyTokens`: { accessToken, refreshToken, expiresAt }
  - `tidalTokens`: { accessToken, refreshToken, expiresAt }
- Tokens auto-refresh when expired

## Environment Variables

Required in `backend/.env`:

```
# Server
PORT=3001
FRONTEND_URL=http://localhost:5173
SESSION_SECRET=random-secret-string

# Spotify (IMPORTANT: Must use 127.0.0.1, not localhost)
SPOTIFY_CLIENT_ID=xxx
SPOTIFY_CLIENT_SECRET=xxx
SPOTIFY_REDIRECT_URI=http://127.0.0.1:3001/auth/spotify/callback

# Tidal (localhost is fine)
TIDAL_CLIENT_ID=xxx
TIDAL_CLIENT_SECRET=xxx
TIDAL_REDIRECT_URI=http://localhost:3001/auth/tidal/callback
```

**Note**: Spotify enforces security requirements for redirect URIs:
- Must use explicit loopback address (`127.0.0.1` or `[::1]`)
- Cannot use `localhost` as redirect URI
- See `REDIRECT_URI_REFERENCE.md` for details

## Potential Improvements

### Short-term:
- [ ] Add loading states during track matching
- [ ] Persist sync history to database
- [ ] Add ability to sync multiple playlists at once
- [ ] Better error handling and retry logic
- [ ] Progress bar during sync

### Medium-term:
- [ ] Support for syncing in reverse (Tidal → Spotify)
- [ ] Scheduled automatic syncs
- [ ] Two-way sync support
- [ ] Support for Apple Music, YouTube Music
- [ ] User profiles and saved preferences

### Long-term:
- [ ] Deploy to production (suggest Vercel + Railway/Render)
- [ ] Database for user data and sync history
- [ ] Background job processing for large playlists
- [ ] Mobile app
- [ ] Playlist difference detection (only sync new tracks)

## Production Deployment Considerations

1. **Session Store**: Switch from memory to Redis
2. **Environment**: Set `NODE_ENV=production`
3. **HTTPS**: Required for OAuth in production
4. **CORS**: Update allowed origins
5. **Rate Limiting**: Add rate limiting middleware
6. **Logging**: Implement proper logging (Winston, Pino)
7. **Error Tracking**: Add Sentry or similar
8. **Database**: Consider PostgreSQL for user data

## Known Issues & Limitations

1. **Rate Limits**: Both APIs have rate limits
   - Solution: Add delays between requests (currently 100ms)
   - Could implement exponential backoff

2. **Session Persistence**: Sessions lost on server restart
   - Solution: Use Redis or database-backed sessions

3. **Large Playlists**: May timeout
   - Solution: Implement background jobs, websockets for progress

4. **Local Files**: Spotify local files can't be synced
   - Already filtered out in code

5. **Podcasts**: Not supported
   - Would need separate logic for episodes

## Testing Checklist

Before deployment:
- [ ] OAuth flow works for both services
- [ ] Token refresh works correctly
- [ ] Playlists load from both services
- [ ] Sync creates playlist on Tidal
- [ ] ISRC matching works
- [ ] Metadata fallback works
- [ ] Stats are accurate
- [ ] Unmatched tracks list is correct
- [ ] Error handling works gracefully
- [ ] Session persists across requests
- [ ] Logout clears session correctly

## Development Commands

```bash
# Install all dependencies
npm install

# Run both frontend and backend
npm run dev

# Run only backend
npm run dev:backend

# Run only frontend
npm run dev:frontend

# Build frontend for production
npm run build

# Start production server
npm start

# Run setup script
./setup.sh
```

## File Structure Summary

```
Vibeflow/
├── backend/
│   ├── src/
│   │   ├── routes/        # Express route handlers
│   │   ├── services/      # Business logic & API calls
│   │   └── index.js       # Server entry
│   ├── package.json
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── package.json           # Workspace root
├── .gitignore
├── README.md
├── QUICKSTART.md
├── DEV_NOTES.md          # This file
└── setup.sh
```
