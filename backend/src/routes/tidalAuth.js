import express from 'express';
import axios from 'axios';
import querystring from 'querystring';

const router = express.Router();

const TIDAL_AUTH_URL = 'https://login.tidal.com/authorize';
const TIDAL_TOKEN_URL = 'https://auth.tidal.com/v1/oauth2/token';
const TIDAL_SCOPES = ['r_usr', 'w_usr', 'w_sub'];

// Initiate Tidal OAuth
router.get('/login', (req, res) => {
  const state = Math.random().toString(36).substring(7);
  req.session.tidalState = state;

  const authUrl = `${TIDAL_AUTH_URL}?${querystring.stringify({
    response_type: 'code',
    client_id: process.env.TIDAL_CLIENT_ID,
    redirect_uri: process.env.TIDAL_REDIRECT_URI,
    scope: TIDAL_SCOPES.join(' '),
    state: state
  })}`;

  res.json({ authUrl });
});

// Tidal OAuth callback
router.get('/callback', async (req, res) => {
  const { code, state } = req.query;

  if (!code || state !== req.session.tidalState) {
    return res.redirect(`${process.env.FRONTEND_URL}?error=state_mismatch`);
  }

  try {
    const response = await axios.post(
      TIDAL_TOKEN_URL,
      querystring.stringify({
        grant_type: 'authorization_code',
        code: code,
        redirect_uri: process.env.TIDAL_REDIRECT_URI,
        client_id: process.env.TIDAL_CLIENT_ID,
        client_secret: process.env.TIDAL_CLIENT_SECRET
      }),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );

    req.session.tidalTokens = {
      accessToken: response.data.access_token,
      refreshToken: response.data.refresh_token,
      expiresAt: Date.now() + (response.data.expires_in * 1000)
    };

    res.redirect(`${process.env.FRONTEND_URL}?tidal=connected`);
  } catch (error) {
    console.error('Tidal token exchange error:', error.response?.data || error.message);
    res.redirect(`${process.env.FRONTEND_URL}?error=auth_failed`);
  }
});

// Refresh Tidal token
router.post('/refresh', async (req, res) => {
  const refreshToken = req.session.tidalTokens?.refreshToken;

  if (!refreshToken) {
    return res.status(401).json({ error: 'No refresh token available' });
  }

  try {
    const response = await axios.post(
      TIDAL_TOKEN_URL,
      querystring.stringify({
        grant_type: 'refresh_token',
        refresh_token: refreshToken,
        client_id: process.env.TIDAL_CLIENT_ID,
        client_secret: process.env.TIDAL_CLIENT_SECRET
      }),
      {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      }
    );

    req.session.tidalTokens = {
      ...req.session.tidalTokens,
      accessToken: response.data.access_token,
      expiresAt: Date.now() + (response.data.expires_in * 1000)
    };

    res.json({ success: true });
  } catch (error) {
    console.error('Tidal token refresh error:', error.response?.data || error.message);
    res.status(500).json({ error: 'Failed to refresh token' });
  }
});

// Check authentication status
router.get('/status', (req, res) => {
  const isAuthenticated = !!(
    req.session.tidalTokens?.accessToken &&
    req.session.tidalTokens?.expiresAt > Date.now()
  );
  res.json({ authenticated: isAuthenticated });
});

// Logout
router.post('/logout', (req, res) => {
  req.session.tidalTokens = null;
  res.json({ success: true });
});

export default router;
