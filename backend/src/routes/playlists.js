import express from 'express';
import { getSpotifyPlaylists } from '../services/spotifyService.js';
import { getTidalPlaylists } from '../services/tidalService.js';

const router = express.Router();

// Get Spotify playlists
router.get('/spotify', async (req, res) => {
  try {
    const accessToken = req.session.spotifyTokens?.accessToken;
    if (!accessToken) {
      return res.status(401).json({ error: 'Not authenticated with Spotify' });
    }

    const playlists = await getSpotifyPlaylists(accessToken);
    res.json(playlists);
  } catch (error) {
    console.error('Error fetching Spotify playlists:', error.message);
    res.status(500).json({ error: 'Failed to fetch Spotify playlists' });
  }
});

// Get Tidal playlists
router.get('/tidal', async (req, res) => {
  try {
    const accessToken = req.session.tidalTokens?.accessToken;
    if (!accessToken) {
      return res.status(401).json({ error: 'Not authenticated with Tidal' });
    }

    const playlists = await getTidalPlaylists(accessToken);
    res.json(playlists);
  } catch (error) {
    console.error('Error fetching Tidal playlists:', error.message);
    res.status(500).json({ error: 'Failed to fetch Tidal playlists' });
  }
});

export default router;
