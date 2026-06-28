import Alpine from 'alpinejs';
import './select.js'; // registers the reusable vfselect dropdown component
import { api } from './api.js';
import { connection } from './connection.js';
import { mappings } from './mappings.js';
import { nav } from './nav.js';
import { notifications } from './notifications.js';
import { playlists } from './playlists.js';
import { sync } from './sync.js';
import { theme } from './theme.js';
import { toast } from './toast.js';
import { users } from './users.js';

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
    ...users(),
    ...notifications(),

    booting: true,
    loginEnabled: false,
    historyTab: 'manual', // 'manual' | 'scheduled'

    // Computed props live on the root component — object spread copies a getter's value,
    // not the getter, so these can't sit in the spread-in feature modules.
    get bothConnected() {
      return this.session.spotify.connected && this.session.tidal.connected;
    },
    get filteredPlaylists() {
      const q = this.filter.trim().toLowerCase();
      const list = q
        ? this.playlists.filter((p) => p.name.toLowerCase().includes(q))
        : this.playlists.slice();
      return this._sortPlaylists(list);
    },
    get selectedCount() {
      return this.selected.size;
    },
    get activeScheduleCount() {
      return this.mappings.filter((m) => m.enabled).length;
    },
    get playlistOpts() {
      return this.playlists.map((p) => ({ value: p.id, label: `${p.name} (${p.track_count})` }));
    },
    get manualRuns() {
      return this.history.filter((r) => !r.scheduled);
    },
    get scheduledRuns() {
      return this.history.filter((r) => r.scheduled);
    },
    get visibleRuns() {
      return this.historyTab === 'scheduled' ? this.scheduledRuns : this.manualRuns;
    },

    // ── Home dashboard ──
    get upcomingSchedules() {
      return this.mappings
        .filter((m) => m.enabled && m.next_run_at)
        .sort((a, b) => new Date(a.next_run_at) - new Date(b.next_run_at))
        .slice(0, 3);
    },
    get recentActivity() {
      return this.history.slice(0, 3);
    },
    get totalTracksSynced() {
      return this.history.reduce((sum, r) => sum + (r.added || 0), 0);
    },
    get lastRun() {
      return this.history[0] || null;
    },

    async init() {
      this.initTheme();
      this.handleAuthRedirect();

      // App login gate: bounce to the login page if required and not signed in.
      try {
        const status = await api.authStatus();
        this.loginEnabled = status.enabled;
        if (status.enabled && status.needs_setup) {
          window.location.href = '/login.html';
          return;
        }
        if (status.enabled && !status.authenticated) {
          window.location.href = '/login.html';
          return;
        }
        this.currentUser = status.user;
        this.isAdmin = !!(status.user && status.user.is_admin);
        if (this.isAdmin) this.loadUsers();
        this.loadNotifications();
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
