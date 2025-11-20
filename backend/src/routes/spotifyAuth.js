import express from 'express';
import axios from 'axios';
import querystring from 'querystring';

const router = express.Router();

const SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/authorize';
const SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token';
const SPOTIFY_SCOPES = [
  'playlist-read-private',
  'playlist-read-collaborative',
  'user-library-read'
];

// Initiate Spotify OAuth
router.get('/login', (req, res) => {
  const state = Math.random().toString(36).substring(7);
  req.session.spotifyState = state;
  
  // Save session before redirecting
  req.session.save((err) => {
    if (err) {
      console.error('Session save error:', err);
      return res.status(500).json({ error: 'Failed to initialize session' });
    }

    const authUrl = `${SPOTIFY_AUTH_URL}?${querystring.stringify({
      response_type: 'code',
      client_id: process.env.SPOTIFY_CLIENT_ID,
      scope: SPOTIFY_SCOPES.join(' '),
      redirect_uri: process.env.SPOTIFY_REDIRECT_URI,
      state: state
    })}`;

    res.json({ authUrl });
  });
});

// Spotify OAuth callback
router.get('/callback', async (req, res) => {
  const { code, state } = req.query;

  console.log('Spotify callback - State from URL:', state);
  console.log('Spotify callback - State from session:', req.session.spotifyState);
  console.log('Spotify callback - Session ID:', req.sessionID);

  if (!code) {
    console.error('No code provided in callback');
    return res.redirect(`${process.env.FRONTEND_URL}?error=no_code`);
  }

  if (state !== req.session.spotifyState) {
    console.error('State mismatch - URL:', state, 'Session:', req.session.spotifyState);
    return res.redirect(`${process.env.FRONTEND_URL}?error=state_mismatch`);
  }

  try {
    const response = await axios.post(
      SPOTIFY_TOKEN_URL,
      querystring.stringify({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: process.env.SPOTIFY_REDIRECT_URI
      }),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': 'Basic ' + Buffer.from(
            `${process.env.SPOTIFY_CLIENT_ID}:${process.env.SPOTIFY_CLIENT_SECRET}`
          ).toString('base64')
        }
      }
    );

    req.session.spotifyTokens = {
      accessToken: response.data.access_token,
      refreshToken: response.data.refresh_token,
      expiresAt: Date.now() + (response.data.expires_in * 1000)
    };

    res.redirect(`${process.env.FRONTEND_URL}?spotify=connected`);
  } catch (error) {
    console.error('Spotify token exchange error:', error.response?.data || error.message);
    res.redirect(`${process.env.FRONTEND_URL}?error=auth_failed`);
  }
});

// Refresh Spotify token
router.post('/refresh', async (req, res) => {
  const refreshToken = req.session.spotifyTokens?.refreshToken;

  if (!refreshToken) {
    return res.status(401).json({ error: 'No refresh token available' });
  }

  try {
    const response = await axios.post(
      SPOTIFY_TOKEN_URL,
      querystring.stringify({
        grant_type: 'refresh_token',
        refresh_token: refreshToken
      }),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': 'Basic ' + Buffer.from(
            `${process.env.SPOTIFY_CLIENT_ID}:${process.env.SPOTIFY_CLIENT_SECRET}`
          ).toString('base64')
        }
      }
    );

    req.session.spotifyTokens = {
      ...req.session.spotifyTokens,
      accessToken: response.data.access_token,
      expiresAt: Date.now() + (response.data.expires_in * 1000)
    };

    res.json({ success: true });
  } catch (error) {
    console.error('Spotify token refresh error:', error.response?.data || error.message);
    res.status(500).json({ error: 'Failed to refresh token' });
  }
});

// Check authentication status
router.get('/status', (req, res) => {
  const isAuthenticated = !!(
    req.session.spotifyTokens?.accessToken &&
    req.session.spotifyTokens?.expiresAt > Date.now()
  );
  res.json({ authenticated: isAuthenticated });
});

// Logout
router.post('/logout', (req, res) => {
  req.session.spotifyTokens = null;
  res.json({ success: true });
});

export default router;
