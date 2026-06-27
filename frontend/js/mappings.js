import { api, parseTime } from './api.js';

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

    // Schedules-page sort (persisted on this device, like the theme picker).
    sortBy: localStorage.getItem('vf-schedule-sort') || 'recent',
    sortOpts: [
      { value: 'recent', label: 'Recently added' },
      { value: 'name', label: 'Name (A–Z)' },
      { value: 'name_desc', label: 'Name (Z–A)' },
      { value: 'next', label: 'Next run' },
    ],

    // Builder state (shared by create + edit)
    showForm: false,
    formMode: 'create', // 'create' | 'edit'
    editingId: null,
    sform: _blankForm(),

    // Bulk-schedule state (create mode, >1 playlist selected)
    bulkMode: false,
    bulkItems: [], // [{ id, name }]
    stagger: false,
    staggerStep: 5,
    staggerOpts: [5, 10, 15, 30].map((m) => ({ value: m, label: String(m) })),

    // Dropdown option lists ({ value, label })
    freqOpts: [
      { value: 'hourly', label: 'Hourly' },
      { value: 'daily', label: 'Daily' },
      { value: 'weekly', label: 'Weekly' },
      { value: 'monthly', label: 'Monthly' },
    ],
    modeOpts: [
      { value: 'add', label: 'Add new only' },
      { value: 'mirror', label: 'Mirror (match source)' },
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

    // Start scheduling the selected playlist(s) (from the Sync page). One opens the single
    // builder; many opens the same builder in bulk mode (one shared schedule applied to all).
    scheduleSelected() {
      if (this.selectedCount < 1) return;
      const items = [...this.selected]
        .map((id) => this.playlists.find((p) => p.id === id))
        .filter(Boolean);
      if (!items.length) return;
      this.formMode = 'create';
      this.editingId = null;
      this.stagger = false;
      this.staggerStep = 5;
      if (items.length === 1) {
        this.bulkMode = false;
        this.bulkItems = [];
        this.sform = { ..._blankForm(), spotify_playlist_id: items[0].id, spotify_name: items[0].name };
      } else {
        this.bulkMode = true;
        this.bulkItems = items.map((p) => ({ id: p.id, name: p.name }));
        this.sform = _blankForm();
      }
      this.showForm = true;
    },
    openEdit(m) {
      this.formMode = 'edit';
      this.bulkMode = false;
      this.editingId = m.id;
      this.sform = _formFromMapping(m);
      this.showForm = true;
    },
    closeForm() {
      this.showForm = false;
    },

    async saveForm() {
      try {
        if (this.formMode === 'create' && this.bulkMode) {
          const res = await api.bulkCreateMappings({
            playlists: this.bulkItems.map((p) => ({ spotify_playlist_id: p.id, spotify_name: p.name })),
            enabled: true,
            stagger_minutes: this.stagger ? Number(this.staggerStep) : 0,
            ..._toSchedule(this.sform),
          });
          const n = res.created.length;
          const s = res.skipped.length;
          let msg = `${n} schedule${n === 1 ? '' : 's'} created`;
          if (s) msg += `, ${s} skipped (already scheduled)`;
          this._toast(true, msg + '.');
          this.showForm = false;
          this.clearSelection();
          await this.loadMappings();
          this.setView('scheduled');
          return;
        }
        if (this.formMode === 'create') {
          if (!this.sform.spotify_playlist_id) {
            this._toast(false, 'Pick a playlist first.');
            return;
          }
          await api.createMapping({
            spotify_playlist_id: this.sform.spotify_playlist_id,
            spotify_name: this.sform.spotify_name || this.sform.spotify_playlist_id,
            enabled: true,
            ..._toSchedule(this.sform),
          });
          this._toast(true, 'Schedule created.');
          this.showForm = false;
          this.clearSelection();
          await this.loadMappings();
          this.setView('scheduled');
          return;
        }
        await api.updateMapping(this.editingId, _toSchedule(this.sform));
        this._toast(true, 'Schedule updated.');
        this.showForm = false;
        await this.loadMappings();
      } catch (e) {
        this._toast(false, e.message);
      }
    },

    async toggleMapping(m) {
      // Mutate the existing object in place so the list isn't replaced (a full reload re-renders
      // every row and flashes a ghost card). Reconcile fields like next_run_at from the response.
      const prev = m.enabled;
      m.enabled = !prev;
      try {
        const updated = await api.updateMapping(m.id, { enabled: m.enabled });
        Object.assign(m, updated);
      } catch (e) {
        m.enabled = prev;
        this._toast(false, e.message);
      }
    },

    async deleteMapping(m) {
      try {
        await api.deleteMapping(m.id);
        // Drop the row in place rather than reloading the whole list (which re-renders every
        // card and flashes a ghost). Keyed x-for removes just this one.
        const i = this.mappings.findIndex((x) => x.id === m.id);
        if (i !== -1) this.mappings.splice(i, 1);
        this._toast(true, 'Scheduled sync removed.');
      } catch (e) {
        this._toast(false, e.message);
      }
    },

    runConfirm: { open: false, mapping: null },
    askRunNow(m) {
      this.runConfirm = { open: true, mapping: m };
    },
    async confirmRunNow() {
      const m = this.runConfirm.mapping;
      this.runConfirm = { open: false, mapping: null };
      if (m) await this.runMappingNow(m);
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

    // Schedules sorted per the persisted choice. Copies first so the source order is untouched.
    // A method (not a getter): getters in a spread-in module get their value copied once, not
    // re-evaluated — Alpine still re-runs a method call reactively in the template.
    sortedMappings() {
      const list = [...this.mappings];
      const byName = (a, b) =>
        (a.spotify_name || '').localeCompare(b.spotify_name || '', undefined, { sensitivity: 'base' });
      switch (this.sortBy) {
        case 'name':
          return list.sort(byName);
        case 'name_desc':
          return list.sort((a, b) => byName(b, a));
        case 'next':
          return list.sort((a, b) => _nextRunKey(a) - _nextRunKey(b));
        case 'recent':
        default:
          return list.sort((a, b) => b.id - a.id);
      }
    },

    setSort(v) {
      this.sortBy = v;
      localStorage.setItem('vf-schedule-sort', v);
    },

    // One-line summary of what the bulk schedule will produce (reacts to time + stagger).
    // Method, not getter — see sortedMappings() for why.
    bulkPreview() {
      if (!this.bulkMode || !this.bulkItems.length) return '';
      const sched = _toSchedule(this.sform);
      if (!this.stagger) {
        return `All ${this.bulkItems.length} run at ${_staggeredClock(sched, 0, 0)}`;
      }
      const step = Number(this.staggerStep);
      const first = _staggeredClock(sched, 0, step);
      const last = _staggeredClock(sched, this.bulkItems.length - 1, step);
      return `Staggered ${first} → ${last}, every ${step}m`;
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
      const d = parseTime(iso);
      if (!d) return '—';
      return d.toLocaleString([], {
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
      });
    },

    // Future-relative time for "next run in …" (counterpart to formatRelative's "… ago").
    formatUntil(iso) {
      const d = parseTime(iso);
      if (!d) return '—';
      const secs = Math.round((d.getTime() - Date.now()) / 1000);
      if (secs <= 30) return 'now';
      const mins = Math.round(secs / 60);
      if (mins < 60) return `in ${mins}m`;
      const hrs = Math.round(mins / 60);
      if (hrs < 24) return `in ${hrs}h`;
      const days = Math.round(hrs / 24);
      if (days < 7) return `in ${days}d`;
      return `on ${d.toLocaleDateString([], { month: 'short', day: 'numeric' })}`;
    },
  };
}

// Sort key for "Next run": paused or never-scheduled rows sink to the bottom.
function _nextRunKey(m) {
  if (!m.enabled || !m.next_run_at) return Infinity;
  const d = parseTime(m.next_run_at);
  return d ? d.getTime() : Infinity;
}

function _blankForm() {
  return { spotify_playlist_id: '', spotify_name: '', mode: 'add', frequency: 'daily', hour12: 3, minute: 0, ampm: 'AM', day_of_week: 0, day_of_month: 1 };
}

function _formFromMapping(m) {
  const h = m.at_hour ?? 9;
  return {
    spotify_playlist_id: m.spotify_playlist_id,
    spotify_name: m.spotify_name,
    mode: m.mode || 'add',
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
    mode: f.mode,
    frequency: f.frequency,
    at_hour: f.frequency === 'hourly' ? null : to24,
    at_minute: Number(f.minute),
    day_of_week: f.frequency === 'weekly' ? Number(f.day_of_week) : null,
    day_of_month: f.frequency === 'monthly' ? Number(f.day_of_month) : null,
  };
}

// Clock label for the i-th playlist in a bulk schedule, offset by `step` minutes each.
// Minutes roll into the hour; the hour wraps at 24. Mirrors the backend's stagger math.
function _staggeredClock(sched, i, step) {
  const total = (sched.at_minute || 0) + i * step;
  const minute = ((total % 60) + 60) % 60;
  if (sched.frequency === 'hourly') return ':' + String(minute).padStart(2, '0');
  const hour = ((((sched.at_hour || 0) + Math.floor(total / 60)) % 24) + 24) % 24;
  return _clock(hour, minute);
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
