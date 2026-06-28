import { api, parseTime } from './api.js';

// Kick off syncs and track their progress. While anything is queued/running we poll
// /api/sync/active on an interval; history refreshes alongside it.
export function sync() {
  return {
    activeRuns: [],
    history: [],
    syncing: false,
    showSyncDialog: false,
    syncMode: 'add',
    _pollTimer: null,

    openSyncDialog() {
      if (this.selectedCount === 0) return;
      this.syncMode = 'add';
      this.showSyncDialog = true;
    },
    async confirmSync() {
      this.showSyncDialog = false;
      await this.startSync(this.syncMode);
    },

    async startSync(mode = 'add') {
      if (this.selectedCount === 0 || this.syncing) return;
      this.syncing = true;
      try {
        const runs = await api.startSync([...this.selected], mode);
        this.activeRuns = runs;
        this.clearSelection();
        this._toast(true, `Syncing ${runs.length} playlist${runs.length > 1 ? 's' : ''}…`);
        this._startPolling();
      } catch (e) {
        this._toast(false, e.message);
      } finally {
        this.syncing = false;
      }
    },

    async loadHistory() {
      try {
        this.history = await api.recentRuns(50);
      } catch (e) {
        /* non-fatal */
      }
    },

    async _poll() {
      try {
        this.activeRuns = await api.activeRuns();
      } catch (e) {
        /* keep last */
      }
      await this.loadHistory();
      if (this.activeRuns.length === 0) {
        this._stopPolling();
        if (this.view === 'history') this.refreshHistory();
      }
    },

    _startPolling() {
      if (this._pollTimer) return;
      this._pollTimer = setInterval(() => this._poll(), 1500);
    },

    _stopPolling() {
      clearInterval(this._pollTimer);
      this._pollTimer = null;
    },

    runPercent(run) {
      if (!run.total) return run.status === 'running' ? 5 : 0;
      return Math.round((run.processed / run.total) * 100);
    },

    statusClass(status) {
      return {
        success: 'text-emerald-300 bg-emerald-500/15',
        partial: 'text-amber-300 bg-amber-500/15',
        error: 'text-red-300 bg-red-500/15',
        running: 'text-accent-300 bg-accent-500/15',
        queued: 'text-neutral-300 bg-neutral-700/40',
      }[status] || 'text-neutral-300 bg-neutral-700/40';
    },

    // "3m ago" / "2h ago" / "Jun 27" — compact relative time for the run rows.
    formatRelative(iso) {
      const d = parseTime(iso);
      if (!d) return '—';
      const secs = Math.round((Date.now() - d.getTime()) / 1000);
      if (secs < 45) return 'just now';
      if (secs < 90) return '1m ago';
      const mins = Math.round(secs / 60);
      if (mins < 60) return `${mins}m ago`;
      const hrs = Math.round(mins / 60);
      if (hrs < 24) return `${hrs}h ago`;
      const days = Math.round(hrs / 24);
      if (days < 7) return `${days}d ago`;
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    },

    // Wall-clock duration of a finished run, e.g. "1m 12s".
    runDuration(run) {
      if (!run.started_at || !run.finished_at) return '—';
      let secs = Math.round((parseTime(run.finished_at) - parseTime(run.started_at)) / 1000);
      if (secs < 0) secs = 0;
      if (secs < 60) return `${secs}s`;
      const mins = Math.floor(secs / 60);
      return `${mins}m ${secs % 60}s`;
    },

    // One-line outcome summary shown at the top of the expanded panel.
    runHeadline(run) {
      const matched = run.total - run.not_found;
      if (run.status === 'error') return 'Sync failed before completing.';
      if (run.status === 'success') {
        if (run.total === 0) return 'Nothing to sync — playlist was empty.';
        if (run.added === 0) return `Already up to date — all ${run.total} tracks present on Tidal.`;
        return `Added ${run.added} of ${matched} matched track${matched === 1 ? '' : 's'} to Tidal.`;
      }
      if (run.status === 'partial') return `Added ${run.added}, but ${run.not_found} track${run.not_found === 1 ? '' : 's'} weren't found on Tidal.`;
      if (run.status === 'running') return `Syncing… ${run.processed} of ${run.total} processed.`;
      return 'Queued.';
    },

    tidalPlaylistUrl(id) {
      return id ? `https://listen.tidal.com/playlist/${id}` : null;
    },
  };
}
