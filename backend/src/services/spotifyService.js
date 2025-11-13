import axios from 'axios';

const SPOTIFY_API_BASE = 'https://api.spotify.com/v1';

/**
 * Get user's Spotify playlists
 */
export async function getSpotifyPlaylists(accessToken) {
  const response = await axios.get(`${SPOTIFY_API_BASE}/me/playlists`, {
    headers: { 'Authorization': `Bearer ${accessToken}` },
    params: { limit: 50 }
  });

  return response.data.items.map(playlist => ({
    id: playlist.id,
    name: playlist.name,
    description: playlist.description,
    trackCount: playlist.tracks.total,
    imageUrl: playlist.images?.[0]?.url
  }));
}

/**
 * Get tracks from a Spotify playlist
 */
export async function getSpotifyPlaylistTracks(playlistId, accessToken) {
  let allTracks = [];
  let url = `${SPOTIFY_API_BASE}/playlists/${playlistId}/tracks`;

  while (url) {
    const response = await axios.get(url, {
      headers: { 'Authorization': `Bearer ${accessToken}` },
      params: { limit: 100 }
    });

    const tracks = response.data.items
      .filter(item => item.track && !item.track.is_local)
      .map(item => ({
        name: item.track.name,
        artists: item.track.artists.map(a => a.name),
        album: item.track.album.name,
        isrc: item.track.external_ids?.isrc,
        durationMs: item.track.duration_ms,
        spotifyId: item.track.id
      }));

    allTracks = allTracks.concat(tracks);
    url = response.data.next;
  }

  return allTracks;
}

/**
 * Get Spotify playlist details
 */
export async function getSpotifyPlaylist(playlistId, accessToken) {
  const response = await axios.get(`${SPOTIFY_API_BASE}/playlists/${playlistId}`, {
    headers: { 'Authorization': `Bearer ${accessToken}` }
  });

  return {
    id: response.data.id,
    name: response.data.name,
    description: response.data.description,
    trackCount: response.data.tracks.total
  };
}
