import { useState, useEffect } from 'react';
import { getSpotifyPlaylists } from '../api';

function PlaylistSelector({ selectedPlaylist, onSelectPlaylist }) {
  const [playlists, setPlaylists] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadPlaylists();
  }, []);

  const loadPlaylists = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getSpotifyPlaylists();
      setPlaylists(data);
    } catch (err) {
      setError('Failed to load playlists');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading your Spotify playlists...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  return (
    <section className="playlists-section">
      <h2>Select a Spotify Playlist to Sync</h2>
      <div className="playlists-grid">
        {playlists.map((playlist) => (
          <div
            key={playlist.id}
            className={`playlist-card ${selectedPlaylist?.id === playlist.id ? 'selected' : ''}`}
            onClick={() => onSelectPlaylist(playlist)}
          >
            {playlist.imageUrl && (
              <img src={playlist.imageUrl} alt={playlist.name} />
            )}
            {!playlist.imageUrl && (
              <div style={{
                width: '100%',
                aspectRatio: '1',
                background: 'var(--bg-dark)',
                borderRadius: '4px',
                marginBottom: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '3rem'
              }}>
                🎵
              </div>
            )}
            <h3>{playlist.name}</h3>
            <p>{playlist.trackCount} tracks</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default PlaylistSelector;
