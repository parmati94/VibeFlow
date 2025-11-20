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
        data: {
          type: 'playlists',
          attributes: {
            name: name,
            description: description || 'Synced from Spotify via Vibeflow'
          }
        }
      },
      {
        headers: { 
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/vnd.api+json'
        },
        params: {
          countryCode: 'US' // Required parameter
        }
      }
    );

    return response.data.data.id;
  } catch (error) {
    console.error('Create Tidal playlist error:', JSON.stringify(error.response?.data, null, 2) || error.message);
    console.error('Request body sent:', JSON.stringify({
      data: {
        type: 'playlists',
        attributes: {
          name: name,
          description: description || 'Synced from Spotify via Vibeflow'
        }
      }
    }, null, 2));
    throw error;
  }
}

/**
 * Search for a track on Tidal by ISRC
 */
export async function searchTidalByISRC(isrc, accessToken) {
  try {
    const response = await axios.get(`${TIDAL_API_BASE}/v2/tracks`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      params: { 
        'filter[isrc]': isrc,
        countryCode: 'US'
      }
    });

    if (response.data.data && response.data.data.length > 0) {
      return response.data.data[0].id;
    }
    return null;
  } catch (error) {
    console.error('Tidal ISRC search error:', error.response?.status, error.response?.data);
    return null;
  }
}

/**
 * Search for a track on Tidal by title and artist
 */
export async function searchTidalByMetadata(trackName, artistNames, accessToken) {
  try {
    const query = `${trackName} ${artistNames.join(' ')}`;
    const response = await axios.get(`${TIDAL_API_BASE}/v2/searchResults/${encodeURIComponent(query)}`, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      params: { 
        countryCode: 'US',
        include: 'tracks'
      }
    });

    // Navigate the response structure: data.relationships.tracks.data
    const tracks = response.data.data?.relationships?.tracks?.data;
    
    if (tracks && tracks.length > 0) {
      // Try to find best match by looking at included track details
      const included = response.data.included || [];
      const trackDetails = included.filter(item => item.type === 'tracks');
      
      // Exact name match first
      const exactMatch = trackDetails.find(track => 
        track.attributes?.title?.toLowerCase() === trackName.toLowerCase()
      );
      
      if (exactMatch) return exactMatch.id;
      
      // Return first result if no exact match
      return tracks[0].id;
    }
    return null;
  } catch (error) {
    console.error('Tidal search error:', error.response?.status, error.response?.data);
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
      
      // Format tracks as JSON:API resource objects
      const trackData = chunk.map(trackId => ({
        id: trackId.toString(),
        type: 'tracks'
      }));
      
      await axios.post(
        `${TIDAL_API_BASE}/v2/playlists/${playlistId}/relationships/items`,
        {
          data: trackData
        },
        {
          headers: { 
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/vnd.api+json'
          },
          params: {
            countryCode: 'US'
          }
        }
      );
    }
  } catch (error) {
    console.error('Add tracks to Tidal playlist error:', error.response?.data || error.message);
    throw error;
  }
}
