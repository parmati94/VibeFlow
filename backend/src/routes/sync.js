import express from 'express';
import { syncPlaylist } from '../services/syncService.js';

const router = express.Router();

// Sync a Spotify playlist to Tidal
router.post('/', async (req, res) => {
  try {
    const { spotifyPlaylistId, tidalPlaylistName } = req.body;
    
    const spotifyToken = req.session.spotifyTokens?.accessToken;
    const tidalToken = req.session.tidalTokens?.accessToken;

    if (!spotifyToken) {
      return res.status(401).json({ error: 'Not authenticated with Spotify' });
    }
    if (!tidalToken) {
      return res.status(401).json({ error: 'Not authenticated with Tidal' });
    }

    const result = await syncPlaylist({
      spotifyPlaylistId,
      tidalPlaylistName,
      spotifyToken,
      tidalToken
    });

    res.json(result);
  } catch (error) {
    console.error('Sync error:', error.message);
    res.status(500).json({ error: error.message || 'Failed to sync playlist' });
  }
});

export default router;
