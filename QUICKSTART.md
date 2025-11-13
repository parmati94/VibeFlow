# Vibeflow - Quick Start Guide

## Installation (5 minutes)

### 1. Run the setup script
```bash
./setup.sh
```

Or manually:
```bash
npm install
cp backend/.env.example backend/.env
```

### 2. Get API Credentials

#### Spotify:
1. Go to https://developer.spotify.com/dashboard
2. Create an app
3. Add redirect URI: `http://127.0.0.1:3001/auth/spotify/callback`
   - **Note**: Must use 127.0.0.1, not localhost (Spotify requirement)
4. Copy Client ID and Client Secret

#### Tidal:
1. Go to https://developer.tidal.com/dashboard
2. Create an app
3. Add redirect URI: `http://localhost:3001/auth/tidal/callback`
4. Copy Client ID and Client Secret

### 3. Configure Environment
Edit `backend/.env`:
```env
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
TIDAL_CLIENT_ID=your_tidal_client_id_here
TIDAL_CLIENT_SECRET=your_tidal_client_secret_here
SESSION_SECRET=change_this_to_random_string
```

### 4. Run the App
```bash
npm run dev
```

Open http://localhost:5173 in your browser!

## Usage Flow

1. Click "Connect Spotify" → Authorize
2. Click "Connect Tidal" → Authorize
3. Select a Spotify playlist
4. (Optional) Rename for Tidal
5. Click "Sync to Tidal"
6. Watch the magic happen! ✨

## Troubleshooting

**Port already in use?**
- Change PORT in `backend/.env`
- Change port in `frontend/vite.config.js`

**Authentication not working?**
- Check redirect URIs match exactly in developer dashboards
- Clear browser cookies and try again
- Make sure both services are running

**Tracks not matching?**
- This is normal - not all Spotify tracks are on Tidal
- Check the "Unmatched tracks" section after sync
- ISRC matching is most accurate but not always available

## Development

### Backend only:
```bash
npm run dev:backend
```

### Frontend only:
```bash
npm run dev:frontend
```

### Production build:
```bash
npm run build
npm start
```

Enjoy syncing your playlists! 🎶
