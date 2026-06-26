import { api } from './api.js';

// Backend reachability + per-service (Spotify/Tidal) connection state. Spread into the
// root `app` component so the markup sees one flat object. Later phases add their own
// modules (auth actions, sync, mappings, history) composed the same way.
export function connection() {
  return {
    health: 'loading', // 'loading' | 'ok' | 'error'
    session: { spotify: {}, tidal: {} },

    async loadConnection() {
      try {
        await api.health();
        this.health = 'ok';
      } catch (e) {
        this.health = 'error';
      }
      try {
        this.session = await api.session();
      } catch (e) {
        // backend session route may not be wired yet; keep defaults
      }
    },
  };
}
