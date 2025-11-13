import axios from 'axios';

const API_BASE = '';

export async function checkAuthStatus() {
  try {
    const [spotifyRes, tidalRes] = await Promise.all([
      axios.get(`${API_BASE}/auth/spotify/status`, { withCredentials: true }),
      axios.get(`${API_BASE}/auth/tidal/status`, { withCredentials: true })
    ]);
    
    return [
      spotifyRes.data.authenticated,
      tidalRes.data.authenticated
    ];
  } catch (error) {
    console.error('Auth status check failed:', error);
    return [false, false];
  }
}

export async function loginSpotify() {
  try {
    const response = await axios.get(`${API_BASE}/auth/spotify/login`, { 
      withCredentials: true 
    });
    window.location.href = response.data.authUrl;
  } catch (error) {
    console.error('Spotify login failed:', error);
    throw error;
  }
}

export async function loginTidal() {
  try {
    const response = await axios.get(`${API_BASE}/auth/tidal/login`, { 
      withCredentials: true 
    });
    window.location.href = response.data.authUrl;
  } catch (error) {
    console.error('Tidal login failed:', error);
    throw error;
  }
}

export async function logoutSpotify() {
  await axios.post(`${API_BASE}/auth/spotify/logout`, {}, { withCredentials: true });
}

export async function logoutTidal() {
  await axios.post(`${API_BASE}/auth/tidal/logout`, {}, { withCredentials: true });
}

export async function getSpotifyPlaylists() {
  const response = await axios.get(`${API_BASE}/api/playlists/spotify`, { 
    withCredentials: true 
  });
  return response.data;
}

export async function syncPlaylist(spotifyPlaylistId, tidalPlaylistName) {
  const response = await axios.post(
    `${API_BASE}/api/sync`,
    {
      spotifyPlaylistId,
      tidalPlaylistName
    },
    { withCredentials: true }
  );
  return response.data;
}
