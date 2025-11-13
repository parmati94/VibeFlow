import { useState, useEffect } from 'react';
import AuthSection from './components/AuthSection';
import PlaylistSelector from './components/PlaylistSelector';
import SyncSection from './components/SyncSection';
import { checkAuthStatus } from './api';

function App() {
  const [spotifyAuth, setSpotifyAuth] = useState(false);
  const [tidalAuth, setTidalAuth] = useState(false);
  const [selectedPlaylist, setSelectedPlaylist] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuthentication();
    
    // Check for OAuth callback parameters
    const params = new URLSearchParams(window.location.search);
    if (params.get('spotify') === 'connected') {
      setSpotifyAuth(true);
      window.history.replaceState({}, '', '/');
    }
    if (params.get('tidal') === 'connected') {
      setTidalAuth(true);
      window.history.replaceState({}, '', '/');
    }
  }, []);

  const checkAuthentication = async () => {
    try {
      const [spotify, tidal] = await checkAuthStatus();
      setSpotifyAuth(spotify);
      setTidalAuth(tidal);
    } catch (error) {
      console.error('Auth check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div className="container">
      <header className="header">
        <h1>Vibeflow</h1>
        <p>Sync your playlists from Spotify to Tidal</p>
      </header>

      <AuthSection
        spotifyAuth={spotifyAuth}
        tidalAuth={tidalAuth}
        onAuthChange={checkAuthentication}
      />

      {spotifyAuth && tidalAuth && (
        <>
          <PlaylistSelector
            selectedPlaylist={selectedPlaylist}
            onSelectPlaylist={setSelectedPlaylist}
          />

          {selectedPlaylist && (
            <SyncSection
              selectedPlaylist={selectedPlaylist}
              onSyncComplete={() => {
                setSelectedPlaylist(null);
              }}
            />
          )}
        </>
      )}
    </div>
  );
}

export default App;
