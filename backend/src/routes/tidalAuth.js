import express from 'express';
import axios from 'axios';
import querystring from 'querystring';
import crypto from 'crypto';

const router = express.Router();

const TIDAL_AUTH_URL = 'https://login.tidal.com/authorize';
const TIDAL_TOKEN_URL = 'https://auth.tidal.com/v1/oauth2/token';
// Use correct Tidal scope names
const TIDAL_SCOPES = 'user.read playlists.read playlists.write';

// Generate PKCE code verifier and challenge
function generatePKCE() {
  const codeVerifier = crypto.randomBytes(32).toString('base64url');
  const codeChallenge = crypto
    .createHash('sha256')
    .update(codeVerifier)
    .digest('base64url');
  
  return { codeVerifier, codeChallenge };
}

// Initiate Tidal OAuth
router.get('/login', (req, res) => {
  const state = Math.random().toString(36).substring(7);
  const { codeVerifier, codeChallenge } = generatePKCE();
  
  // Store state and code verifier in session
  req.session.tidalState = state;
  req.session.tidalCodeVerifier = codeVerifier;
  
  // Save session before redirecting
  req.session.save((err) => {
    if (err) {
      console.error('Session save error:', err);
      return res.status(500).json({ error: 'Failed to initialize session' });
    }

    // Build auth URL with PKCE
    const authUrl = `${TIDAL_AUTH_URL}?` + 
      `response_type=code` +
      `&client_id=${encodeURIComponent(process.env.TIDAL_CLIENT_ID)}` +
      `&redirect_uri=${encodeURIComponent(process.env.TIDAL_REDIRECT_URI)}` +
      `&scope=${encodeURIComponent(TIDAL_SCOPES)}` +
      `&state=${encodeURIComponent(state)}` +
      `&code_challenge=${encodeURIComponent(codeChallenge)}` +
      `&code_challenge_method=S256`;
    
    console.log('Tidal auth URL:', authUrl);
    res.json({ authUrl });
  });
});

// Tidal OAuth callback
router.get('/callback', async (req, res) => {
  const { code, state, error, error_description } = req.query;

  console.log('Tidal callback - Full query params:', req.query);
  console.log('Tidal callback - State from URL:', state);
  console.log('Tidal callback - State from session:', req.session.tidalState);
  console.log('Tidal callback - Session ID:', req.sessionID);
  console.log('Tidal callback - Error from Tidal:', error);
  console.log('Tidal callback - Error description:', error_description);

  if (error) {
    console.error('Tidal authorization error:', error, error_description);
    return res.redirect(`${process.env.FRONTEND_URL}?error=tidal_${error}`);
  }

  if (!code) {
    console.error('No code provided in callback');
    return res.redirect(`${process.env.FRONTEND_URL}?error=no_code`);
  }

  if (state !== req.session.tidalState) {
    console.error('State mismatch - URL:', state, 'Session:', req.session.tidalState);
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
        code_verifier: req.session.tidalCodeVerifier // PKCE code verifier
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

    // Clear the code verifier after use
    delete req.session.tidalCodeVerifier;

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
