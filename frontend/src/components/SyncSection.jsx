import { useState } from 'react';
import { syncPlaylist } from '../api';

function SyncSection({ selectedPlaylist, onSyncComplete }) {
  const [playlistName, setPlaylistName] = useState(selectedPlaylist.name);
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSync = async () => {
    try {
      setSyncing(true);
      setError(null);
      setResult(null);

      const data = await syncPlaylist(selectedPlaylist.id, playlistName);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to sync playlist');
      console.error(err);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <section className="sync-section">
      <h2>Sync to Tidal</h2>
      <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>
        Selected: <strong>{selectedPlaylist.name}</strong> ({selectedPlaylist.trackCount} tracks)
      </p>

      <input
        type="text"
        placeholder="Tidal playlist name"
        value={playlistName}
        onChange={(e) => setPlaylistName(e.target.value)}
        disabled={syncing}
      />

      <div style={{ marginTop: '1rem' }}>
        <button
          className="btn"
          onClick={handleSync}
          disabled={syncing || !playlistName.trim()}
        >
          {syncing ? 'Syncing...' : 'Sync to Tidal'}
        </button>
      </div>

      {error && (
        <div className="sync-status error">
          <h3>Error</h3>
          <p>{error}</p>
        </div>
      )}

      {result && (
        <div className="sync-status success">
          <h3>✓ {result.message}</h3>
          
          {result.stats && (
            <div className="stats">
              <div className="stat">
                <div className="stat-value">{result.stats.totalTracks}</div>
                <div className="stat-label">Total Tracks</div>
              </div>
              <div className="stat">
                <div className="stat-value">{result.stats.matchedByISRC}</div>
                <div className="stat-label">Matched by ISRC</div>
              </div>
              <div className="stat">
                <div className="stat-value">{result.stats.matchedByMetadata}</div>
                <div className="stat-label">Matched by Search</div>
              </div>
              <div className="stat">
                <div className="stat-value">{result.stats.notFound}</div>
                <div className="stat-label">Not Found</div>
              </div>
              <div className="stat">
                <div className="stat-value">{result.stats.addedToTidal}</div>
                <div className="stat-label">Added to Tidal</div>
              </div>
            </div>
          )}

          {result.unmatchedTracks && result.unmatchedTracks.length > 0 && (
            <details style={{ marginTop: '1rem', textAlign: 'left' }}>
              <summary style={{ cursor: 'pointer', marginBottom: '0.5rem' }}>
                Unmatched tracks ({result.unmatchedTracks.length})
              </summary>
              <ul style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                {result.unmatchedTracks.map((track, index) => (
                  <li key={index}>
                    {track.name} - {track.artists.join(', ')}
                  </li>
                ))}
              </ul>
            </details>
          )}

          <button
            className="btn btn-secondary"
            onClick={onSyncComplete}
            style={{ marginTop: '1rem' }}
          >
            Sync Another Playlist
          </button>
        </div>
      )}
    </section>
  );
}

export default SyncSection;
