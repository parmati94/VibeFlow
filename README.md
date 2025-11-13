# Vibeflow 🎵

A modern web application to sync your playlists from Spotify to Tidal. Built with React and Node.js.

## Features

- 🔐 OAuth authentication for both Spotify and Tidal
- 🎼 Browse and select your Spotify playlists
- 🔄 Intelligent track matching using ISRC codes (most accurate)
- 🔍 Fallback to metadata matching (title + artist) when ISRC isn't available
- 📊 Detailed sync statistics and unmatched tracks report
- 🎨 Clean, modern UI with dark theme

## Tech Stack

### Frontend
- React 18
- Vite
- Axios for API calls
- Modern CSS with CSS variables

### Backend
- Node.js with Express
- Session-based authentication
- Axios for external API calls
- ES Modules

## Prerequisites

- Node.js 18+ and npm
- Spotify Developer Account ([Get one here](https://developer.spotify.com/dashboard))
- Tidal Developer Account ([Get one here](https://developer.tidal.com/dashboard))

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
cd Vibeflow
npm install
```

This will install dependencies for the root monorepo and both frontend and backend workspaces.

### 2. Configure Spotify API

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Add `http://127.0.0.1:3001/auth/spotify/callback` to Redirect URIs
   - **Important**: Spotify requires `127.0.0.1` (not `localhost`) for local development
4. Copy your Client ID and Client Secret

### 3. Configure Tidal API

1. Go to [Tidal Developer Dashboard](https://developer.tidal.com/dashboard)
2. Create a new app
3. Add `http://localhost:3001/auth/tidal/callback` to Redirect URIs
4. Copy your Client ID and Client Secret

### 4. Setup Environment Variables

Create a `.env` file in the `backend` directory:

```bash
cd backend
cp .env.example .env
```

Edit `.env` and add your API credentials:

```env
# Server Configuration
PORT=3001
NODE_ENV=development
FRONTEND_URL=http://localhost:5173
SESSION_SECRET=your-super-secret-session-key-change-this

# Spotify API Configuration
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
SPOTIFY_REDIRECT_URI=http://127.0.0.1:3001/auth/spotify/callback

# Tidal API Configuration
TIDAL_CLIENT_ID=your_tidal_client_id
TIDAL_CLIENT_SECRET=your_tidal_client_secret
TIDAL_REDIRECT_URI=http://localhost:3001/auth/tidal/callback
```

**Important:** Change the `SESSION_SECRET` to a random string for security.

### 5. Run the Application

From the root directory:

```bash
# Run both frontend and backend concurrently
npm run dev
```

Or run them separately:

```bash
# Terminal 1 - Backend
npm run dev:backend

# Terminal 2 - Frontend
npm run dev:frontend
```

The app will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:3001

## Usage

1. **Connect Your Accounts**
   - Click "Connect Spotify" and authorize the app
   - Click "Connect Tidal" and authorize the app

2. **Select a Playlist**
   - Browse your Spotify playlists
   - Click on the playlist you want to sync

3. **Sync to Tidal**
   - Optionally rename the playlist for Tidal
   - Click "Sync to Tidal"
   - Wait for the sync to complete (this may take a while for large playlists)

4. **Review Results**
   - See detailed statistics about the sync
   - Check which tracks were matched by ISRC vs. metadata
   - View any tracks that couldn't be found on Tidal

## How Track Matching Works

The app uses a two-tier matching strategy:

1. **ISRC Matching (Primary)**: ISRC (International Standard Recording Code) is a unique identifier for recordings. This provides the most accurate matches.

2. **Metadata Matching (Fallback)**: If ISRC isn't available or doesn't find a match, the app searches Tidal using the track name and artist names.

This approach balances accuracy with coverage, ensuring the best possible match rate.

## Project Structure

```
Vibeflow/
├── backend/
│   ├── src/
│   │   ├── routes/           # API route handlers
│   │   │   ├── spotifyAuth.js
│   │   │   ├── tidalAuth.js
│   │   │   ├── playlists.js
│   │   │   └── sync.js
│   │   ├── services/         # Business logic
│   │   │   ├── spotifyService.js
│   │   │   ├── tidalService.js
│   │   │   └── syncService.js
│   │   └── index.js          # Server entry point
│   ├── package.json
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── AuthSection.jsx
│   │   │   ├── PlaylistSelector.jsx
│   │   │   └── SyncSection.jsx
│   │   ├── App.jsx
│   │   ├── api.js           # API client
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── vite.config.js
│   └── package.json
├── package.json             # Root workspace config
└── README.md
```

## API Endpoints

### Authentication
- `GET /auth/spotify/login` - Initiate Spotify OAuth
- `GET /auth/spotify/callback` - Spotify OAuth callback
- `GET /auth/spotify/status` - Check Spotify auth status
- `POST /auth/spotify/logout` - Logout from Spotify
- `GET /auth/tidal/login` - Initiate Tidal OAuth
- `GET /auth/tidal/callback` - Tidal OAuth callback
- `GET /auth/tidal/status` - Check Tidal auth status
- `POST /auth/tidal/logout` - Logout from Tidal

### Playlists
- `GET /api/playlists/spotify` - Get user's Spotify playlists
- `GET /api/playlists/tidal` - Get user's Tidal playlists

### Sync
- `POST /api/sync` - Sync a Spotify playlist to Tidal

## Known Limitations

- Tidal's API has rate limits - large playlists may take a while to sync
- Some tracks may not be available on Tidal
- Local files from Spotify cannot be synced
- Podcast episodes are not supported

## Troubleshooting

### "Not authenticated" errors
- Make sure you've connected both Spotify and Tidal accounts
- Session cookies must be enabled in your browser
- Try logging out and logging back in

### Tracks not matching
- Some tracks may not be available on Tidal
- Different versions or remasters might not match perfectly
- Check the "Unmatched tracks" list for details

### API rate limiting
- If syncing fails, wait a few minutes and try again
- Consider syncing smaller playlists or batches

## Contributing

This is a personal project, but feel free to fork and modify for your own use!

## License

MIT License - feel free to use and modify as needed.

## Disclaimer

This project is not affiliated with Spotify or Tidal. Use at your own risk. Make sure to comply with both services' Terms of Service.
