import { loginSpotify, loginTidal, logoutSpotify, logoutTidal } from '../api';

function AuthSection({ spotifyAuth, tidalAuth, onAuthChange }) {
  const handleSpotifyAuth = async () => {
    if (spotifyAuth) {
      await logoutSpotify();
      onAuthChange();
    } else {
      await loginSpotify();
    }
  };

  const handleTidalAuth = async () => {
    if (tidalAuth) {
      await logoutTidal();
      onAuthChange();
    } else {
      await loginTidal();
    }
  };

  return (
    <section className="auth-section">
      <div className={`auth-card ${spotifyAuth ? 'connected' : ''}`}>
        <h2>Spotify</h2>
        <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
          {spotifyAuth ? 'Connected' : 'Connect your Spotify account'}
        </p>
        <button className="btn" onClick={handleSpotifyAuth}>
          {spotifyAuth ? 'Disconnect' : 'Connect Spotify'}
        </button>
      </div>

      <div className={`auth-card ${tidalAuth ? 'connected' : ''}`}>
        <h2>Tidal</h2>
        <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
          {tidalAuth ? 'Connected' : 'Connect your Tidal account'}
        </p>
        <button className="btn" onClick={handleTidalAuth}>
          {tidalAuth ? 'Disconnect' : 'Connect Tidal'}
        </button>
      </div>
    </section>
  );
}

export default AuthSection;
