import Alpine from 'alpinejs';
import { api } from './api.js';
import { connection } from './connection.js';
import { playlists } from './playlists.js';
import { sync } from './sync.js';
import { toast } from './toast.js';

document.addEventListener('alpine:init', () => {
  Alpine.data('app', () => ({
    // Feature modules spread in so the markup sees one flat component.
    ...toast(),
    ...connection(),
    ...playlists(),
    ...sync(),

    booting: true,

    // Computed properties must live on the root component (object spread copies a getter's
    // value, not the getter, so these can't sit in the spread-in feature modules).
    get bothConnected() {
      return this.session.spotify.connected && this.session.tidal.connected;
    },
    get filteredPlaylists() {
      const q = this.filter.trim().toLowerCase();
      if (!q) return this.playlists;
      return this.playlists.filter((p) => p.name.toLowerCase().includes(q));
    },
    get selectedCount() {
      return this.selected.size;
    },

    async init() {
      this.handleAuthRedirect();
      await this.loadConnection();
      if (this.bothConnected) {
        await Promise.all([this.loadPlaylists(), this.loadHistory()]);
        // Resume polling if a sync was already running when the page loaded.
        try {
          const active = await api.activeRuns();
          if (active.length) {
            this.activeRuns = active;
            this._startPolling();
          }
        } catch (e) {
          /* non-fatal */
        }
      }
      this.booting = false;
    },
  }));
});

window.Alpine = Alpine;
Alpine.start();
