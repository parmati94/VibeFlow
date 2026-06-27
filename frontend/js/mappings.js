import { api } from './api.js';

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const MINUTES = Array.from({ length: 12 }, (_, i) => i * 5); // 0,5,…,55

// Scheduled-sync mappings. One builder (sform) drives both create and edit; a schedule is
// { frequency, at_hour, at_minute, day_of_week, day_of_month } and the form edits it via a
// friendly 12-hour { frequency, hour12, ampm, minute, day_of_week, day_of_month }.
export function mappings() {
  return {
    mappings: [],
    mappingsLoading: false,

    // Builder state (shared by create + edit)
    showForm: false,
    formMode: 'create', // 'create' | 'edit'
    editingId: null,
    sform: _blankForm(),

    // Dropdown option lists ({ value, label })
    freqOpts: [
      { value: 'hourly', label: 'Hourly' },
      { value: 'daily', label: 'Daily' },
      { value: 'weekly', label: 'Weekly' },
      { value: 'monthly', label: 'Monthly' },
    ],
    dayOpts: DAY_NAMES.map((label, value) => ({ value, label })),
    monthDayOpts: Array.from({ length: 28 }, (_, i) => ({ value: i + 1, label: String(i + 1) })),
    hourOpts: Array.from({ length: 12 }, (_, i) => ({ value: i + 1, label: String(i + 1) })),
    minuteOpts: MINUTES.map((m) => ({ value: m, label: String(m).padStart(2, '0') })),
    minPastHourOpts: MINUTES.map((m) => ({ value: m, label: ':' + String(m).padStart(2, '0') })),
    ampmOpts: [{ value: 'AM', label: 'AM' }, { value: 'PM', label: 'PM' }],

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

    openCreate() {
      this.formMode = 'create';
      this.editingId = null;
      this.sform = _blankForm();
      this.showForm = true;
    },
    openEdit(m) {
      this.formMode = 'edit';
      this.editingId = m.id;
      this.sform = _formFromMapping(m);
      this.showForm = true;
    },
    closeForm() {
      this.showForm = false;
    },

    async saveForm() {
      try {
        if (this.formMode === 'create') {
          if (!this.sform.spotify_playlist_id) {
            this._toast(false, 'Pick a playlist first.');
            return;
          }
          const pl = this.playlists.find((p) => p.id === this.sform.spotify_playlist_id);
          await api.createMapping({
            spotify_playlist_id: this.sform.spotify_playlist_id,
            spotify_name: pl ? pl.name : this.sform.spotify_playlist_id,
            enabled: true,
            ..._toSchedule(this.sform),
          });
          this._toast(true, 'Scheduled sync created.');
        } else {
          await api.updateMapping(this.editingId, _toSchedule(this.sform));
          this._toast(true, 'Schedule updated.');
        }
        this.showForm = false;
        await this.loadMappings();
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
  return { spotify_playlist_id: '', frequency: 'daily', hour12: 3, minute: 0, ampm: 'AM', day_of_week: 0, day_of_month: 1 };
}

function _formFromMapping(m) {
  const h = m.at_hour ?? 9;
  return {
    spotify_playlist_id: m.spotify_playlist_id,
    frequency: m.frequency || 'daily',
    hour12: h % 12 || 12,
    ampm: h >= 12 ? 'PM' : 'AM',
    minute: m.at_minute ?? 0,
    day_of_week: m.day_of_week ?? 0,
    day_of_month: m.day_of_month ?? 1,
  };
}

function _toSchedule(f) {
  const to24 = (Number(f.hour12) % 12) + (f.ampm === 'PM' ? 12 : 0);
  return {
    frequency: f.frequency,
    at_hour: f.frequency === 'hourly' ? null : to24,
    at_minute: Number(f.minute),
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
