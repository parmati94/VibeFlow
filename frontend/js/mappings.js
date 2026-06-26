import { api } from './api.js';

const _INTERVAL_LABELS = {
  15: 'every 15 min',
  60: 'hourly',
  360: 'every 6 hours',
  1440: 'daily',
  10080: 'weekly',
};

// Scheduled-sync mappings: list, create, toggle, change interval, delete, run-now.
export function mappings() {
  return {
    mappings: [],
    mappingsLoading: false,
    showAddMapping: false,
    newMapping: { spotify_playlist_id: '', interval_minutes: 1440 },
    intervalOptions: [
      { minutes: 15, label: 'Every 15 minutes' },
      { minutes: 60, label: 'Hourly' },
      { minutes: 360, label: 'Every 6 hours' },
      { minutes: 1440, label: 'Daily' },
      { minutes: 10080, label: 'Weekly' },
    ],

    async loadMappings() {
      this.mappingsLoading = true;
      try {
        this.mappings = await api.listMappings();
      } catch (e) {
        /* non-fatal */
      } finally {
        this.mappingsLoading = false;
      }
    },

    async createMapping() {
      if (!this.newMapping.spotify_playlist_id) {
        this._toast(false, 'Pick a playlist first.');
        return;
      }
      const pl = this.playlists.find((p) => p.id === this.newMapping.spotify_playlist_id);
      try {
        await api.createMapping({
          spotify_playlist_id: this.newMapping.spotify_playlist_id,
          spotify_name: pl ? pl.name : this.newMapping.spotify_playlist_id,
          interval_minutes: Number(this.newMapping.interval_minutes),
          enabled: true,
        });
        this.showAddMapping = false;
        this.newMapping = { spotify_playlist_id: '', interval_minutes: 1440 };
        await this.loadMappings();
        this._toast(true, 'Scheduled sync created.');
      } catch (e) {
        this._toast(false, e.message);
      }
    },

    async toggleMapping(m) {
      try {
        await api.updateMapping(m.id, { enabled: !m.enabled });
        await this.loadMappings();
      } catch (e) {
        this._toast(false, e.message);
      }
    },

    async changeInterval(m, minutes) {
      try {
        await api.updateMapping(m.id, { interval_minutes: Number(minutes) });
        await this.loadMappings();
      } catch (e) {
        this._toast(false, e.message);
      }
    },

    async deleteMapping(m) {
      try {
        await api.deleteMapping(m.id);
        await this.loadMappings();
        this._toast(true, 'Scheduled sync removed.');
      } catch (e) {
        this._toast(false, e.message);
      }
    },

    async runMappingNow(m) {
      try {
        await api.runMapping(m.id);
        this._toast(true, `Syncing ${m.spotify_name}…`);
        this._startPolling();
      } catch (e) {
        this._toast(false, e.message);
      }
    },

    intervalLabel(min) {
      return min ? _INTERVAL_LABELS[min] || `every ${min} min` : 'manual';
    },

    formatWhen(iso) {
      if (!iso) return '—';
      return new Date(iso).toLocaleString([], {
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
      });
    },
  };
}
