import { api } from './api.js';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

// Scheduled-sync mappings: list, create, edit schedule, toggle, delete, run-now.
// A schedule is { frequency, at_hour, at_minute, day_of_week, day_of_month }; the form
// edits it via a friendly { frequency, time:"HH:MM", minute, day_of_week, day_of_month }.
export function mappings() {
  return {
    mappings: [],
    mappingsLoading: false,
    showAddMapping: false,
    newMapping: _blankForm(),
    editingId: null,
    editForm: _blankForm(),

    frequencyOptions: [
      { id: 'hourly', label: 'Hourly' },
      { id: 'daily', label: 'Daily' },
      { id: 'weekly', label: 'Weekly' },
      { id: 'monthly', label: 'Monthly' },
    ],
    dayOptions: DAYS.map((l, v) => ({ v, l })),
    minuteOptions: [0, 15, 30, 45],
    monthDayOptions: Array.from({ length: 28 }, (_, i) => i + 1),

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
          enabled: true,
          ..._toSchedule(this.newMapping),
        });
        this.showAddMapping = false;
        this.newMapping = _blankForm();
        await this.loadMappings();
        this._toast(true, 'Scheduled sync created.');
      } catch (e) {
        this._toast(false, e.message);
      }
    },

    startEdit(m) {
      this.editingId = m.id;
      this.editForm = _formFromMapping(m);
    },
    cancelEdit() {
      this.editingId = null;
    },
    async saveEdit(m) {
      try {
        await api.updateMapping(m.id, _toSchedule(this.editForm));
        this.editingId = null;
        await this.loadMappings();
        this._toast(true, 'Schedule updated.');
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

    scheduleLabel(m) {
      if (!m.frequency) return m.interval_minutes ? `every ${m.interval_minutes} min` : 'manual';
      const t = _clock(m.at_hour ?? 0, m.at_minute ?? 0);
      if (m.frequency === 'hourly') return `Hourly at :${String(m.at_minute ?? 0).padStart(2, '0')}`;
      if (m.frequency === 'daily') return `Daily at ${t}`;
      if (m.frequency === 'weekly') return `Weekly · ${DAYS[m.day_of_week ?? 0]} at ${t}`;
      if (m.frequency === 'monthly') return `Monthly · ${_ordinal(m.day_of_month ?? 1)} at ${t}`;
      return '';
    },

    formatWhen(iso) {
      if (!iso) return '—';
      return new Date(iso).toLocaleString([], {
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
      });
    },
  };
}

function _blankForm() {
  return { spotify_playlist_id: '', frequency: 'daily', time: '03:00', minute: 0, day_of_week: 0, day_of_month: 1 };
}

function _formFromMapping(m) {
  return {
    frequency: m.frequency || 'daily',
    time: `${String(m.at_hour ?? 3).padStart(2, '0')}:${String(m.at_minute ?? 0).padStart(2, '0')}`,
    minute: m.at_minute ?? 0,
    day_of_week: m.day_of_week ?? 0,
    day_of_month: m.day_of_month ?? 1,
  };
}

function _toSchedule(f) {
  const [h, m] = (f.time || '00:00').split(':').map(Number);
  return {
    frequency: f.frequency,
    at_hour: f.frequency === 'hourly' ? null : h,
    at_minute: f.frequency === 'hourly' ? Number(f.minute) : m,
    day_of_week: f.frequency === 'weekly' ? Number(f.day_of_week) : null,
    day_of_month: f.frequency === 'monthly' ? Number(f.day_of_month) : null,
  };
}

function _clock(h, m) {
  const ap = h < 12 ? 'AM' : 'PM';
  const hh = h % 12 || 12;
  return `${hh}:${String(m).padStart(2, '0')} ${ap}`;
}

function _ordinal(n) {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}
