import Alpine from 'alpinejs';
import { api } from './api.js';
import { connection } from './connection.js';
import { mappings } from './mappings.js';
import { nav } from './nav.js';
import { playlists } from './playlists.js';
import { sync } from './sync.js';
import { theme } from './theme.js';
import { toast } from './toast.js';

document.addEventListener('alpine:init', () => {
  Alpine.data('app', () => ({
    // Feature modules spread in so the markup sees one flat component.
    ...toast(),
    ...theme(),
    ...nav(),
    ...connection(),
    ...playlists(),
    ...sync(),
    ...mappings(),

    booting: true,
    loginEnabled: false,

    // Computed props live on the root component — object spread copies a getter's value,
    // not the getter, so these can't sit in the spread-in feature modules.
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
    get activeScheduleCount() {
      return this.mappings.filter((m) => m.enabled).length;
    },

    async init() {
      this.initTheme();
      this.handleAuthRedirect();

      // App login gate: bounce to the login page if required and not signed in.
      try {
        const status = await api.authStatus();
        this.loginEnabled = status.enabled;
        if (status.enabled && !status.authenticated) {
          window.location.href = '/login.html';
          return;
        }
      } catch (e) {
        /* status is open; if it fails treat as no gate */
      }

      await this.loadConnection();
      if (this.bothConnected) {
        await Promise.all([this.loadPlaylists(), this.loadHistory(), this.loadMappings()]);
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

    async signOut() {
      try {
        await api.logout();
      } catch (e) {
        /* ignore */
      }
      window.location.href = '/login.html';
    },
  }));
});

window.Alpine = Alpine;
Alpine.start();
