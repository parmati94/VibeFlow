import { api } from './api.js';

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
      if (this.activeRuns.length === 0) this._stopPolling();
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
  };
}
