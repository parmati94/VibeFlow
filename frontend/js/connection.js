import { api } from './api.js';

// Backend reachability + per-service (Spotify/Tidal) connection state, plus the
// connect/disconnect actions. Spread into the root `app` component.
export function connection() {
  return {
    health: 'loading', // 'loading' | 'ok' | 'error'
    session: { spotify: { configured: false, connected: false }, tidal: { configured: false, connected: false } },

    async loadConnection() {
      try {
        await api.health();
        this.health = 'ok';
      } catch (e) {
        this.health = 'error';
        return;
      }
      try {
        this.session = await api.session();
      } catch (e) {
        /* keep defaults */
      }
    },

    // OAuth login is a full-page redirect so the provider round-trip stays same-origin.
    connect(provider) {
      window.location.href = `/auth/${provider}/login`;
    },

    async disconnect(provider) {
      try {
        await api.disconnect(provider);
        await this.loadConnection();
        this._toast(true, `${this._label(provider)} disconnected.`);
      } catch (e) {
        this._toast(false, `Could not disconnect ${this._label(provider)}.`);
      }
    },

    _label(provider) {
      return provider === 'spotify' ? 'Spotify' : 'Tidal';
    },

    // Reflect the ?connected=… / ?error=… the OAuth callbacks bounce back with.
    handleAuthRedirect() {
      const params = new URLSearchParams(window.location.search);
      const connected = params.get('connected');
      const error = params.get('error');
      if (connected) this._toast(true, `${this._label(connected)} connected.`);
      if (error) this._toast(false, this._errorMessage(error));
      if (connected || error) window.history.replaceState({}, '', window.location.pathname);
    },

    _errorMessage(code) {
      if (code.endsWith('not_configured')) {
        return `${this._label(code.split('_')[0])} isn't configured on the server.`;
      }
      if (code.startsWith('tidal_')) return 'Tidal connection failed. Please try again.';
      if (code.startsWith('spotify_')) return 'Spotify connection failed. Please try again.';
      return 'Something went wrong. Please try again.';
    },
  };
}
