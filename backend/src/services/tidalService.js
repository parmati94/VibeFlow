import axios from 'axios';

const TIDAL_API_BASE = 'https://openapi.tidal.com';

/**
 * Get user's Tidal playlists
 */
export async function getTidalPlaylists(accessToken) {
  try {
    const response = await axios.get(`${TIDAL_API_BASE}/v2/playlists`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      params: { limit: 50 }
    });

    return response.data.data.map(playlist => ({
      id: playlist.id,
      name: playlist.name,
      description: playlist.description,
      trackCount: playlist.numberOfTracks
    }));
  } catch (error) {
    console.error('Tidal playlists error:', error.response?.data || error.message);
    throw error;
  }
}

/**
 * Create a new Tidal playlist
 */
export async function createTidalPlaylist(name, description, accessToken) {
  try {
    const response = await axios.post(
      `${TIDAL_API_BASE}/v2/playlists`,
      {
        name: name,
        description: description || 'Synced from Spotify via Vibeflow'
      },
      {
        headers: { 
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json'
        }
      }
    );

    return response.data.data.id;
  } catch (error) {
    console.error('Create Tidal playlist error:', error.response?.data || error.message);
    throw error;
  }
}

/**
 * Search for a track on Tidal by ISRC
 */
export async function searchTidalByISRC(isrc, accessToken) {
  try {
    const response = await axios.get(`${TIDAL_API_BASE}/v2/searchResults/${isrc}`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      params: { 
        type: 'TRACKS',
        limit: 1
      }
    });

    if (response.data.data?.tracks?.length > 0) {
      return response.data.data.tracks[0].id;
    }
    return null;
  } catch (error) {
    return null;
  }
}

/**
 * Search for a track on Tidal by title and artist
 */
export async function searchTidalByMetadata(trackName, artistNames, accessToken) {
  try {
    const query = `${trackName} ${artistNames.join(' ')}`;
    const response = await axios.get(`${TIDAL_API_BASE}/v2/search`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      params: { 
        query: query,
        type: 'TRACKS',
        limit: 5
      }
    });

    if (response.data.data?.tracks?.length > 0) {
      // Try to find best match
      const tracks = response.data.data.tracks;
      
      // Exact name match first
      const exactMatch = tracks.find(track => 
        track.title.toLowerCase() === trackName.toLowerCase()
      );
      
      if (exactMatch) return exactMatch.id;
      
      // Return first result if no exact match
      return tracks[0].id;
    }
    return null;
  } catch (error) {
    console.error('Tidal search error:', error.response?.data || error.message);
    return null;
  }
}

/**
 * Add tracks to a Tidal playlist
 */
export async function addTracksToTidalPlaylist(playlistId, trackIds, accessToken) {
  try {
    // Tidal API might have limits on batch size, so we'll chunk the requests
    const chunkSize = 100;
    for (let i = 0; i < trackIds.length; i += chunkSize) {
      const chunk = trackIds.slice(i, i + chunkSize);
      
      await axios.post(
        `${TIDAL_API_BASE}/v2/playlists/${playlistId}/items`,
        {
          trackIds: chunk
        },
        {
          headers: { 
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json'
          }
        }
      );
    }
  } catch (error) {
    console.error('Add tracks to Tidal playlist error:', error.response?.data || error.message);
    throw error;
  }
}
