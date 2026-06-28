import { api } from './api.js';

// Day-grouped, paginated history. Each tab (manual/scheduled) is its own paginated stream of
// day summaries; the runs inside a day are fetched lazily when the panel is expanded. The page
// load only ever pulls ~`histLimit` day-summary rows, never the full run list — and "Load
// older" pages back by day. Spread into the root `app` component (uses `historyTab`).
export function history() {
  return {
    // Days per "page" (load size) — user-configurable, remembered on this device.
    histLimit: Number(localStorage.getItem('vf_hist_limit')) || 30,
    histLimitOpts: [14, 30, 60, 90].map((n) => ({ value: n, label: `${n} / page` })),
    histJump: '', // selected month (YYYY-MM) from the month-picker, '' = none
    hist: {
      manual: { days: [], expanded: {}, cursor: null, done: false, loading: false, started: false, seeked: false },
      scheduled: { days: [], expanded: {}, cursor: null, done: false, loading: false, started: false, seeked: false },
    },

    // Open the history view: load the active tab's first page of days if not already started.
    openHistory() {
      if (!this.hist[this.historyTab].started) this.loadDays(true);
    },

    setHistoryTab(tab) {
      this.historyTab = tab;
      this.openHistory();
    },

    // Fetch the next page of day summaries for the active tab (or reset to newest).
    async loadDays(reset = false) {
      const tab = this.historyTab;
      const h = this.hist[tab];
      if (h.loading) return;
      if (reset) {
        Object.assign(h, { days: [], expanded: {}, cursor: null, done: false, seeked: false });
        this.histJump = '';
      } else if (h.done) {
        return;
      }
      h.loading = true;
      h.started = true;
      try {
        const page = await api.historyDays(tab === 'scheduled', h.cursor, this.histLimit);
        h.days = [...h.days, ...page];
        if (page.length) h.cursor = page[page.length - 1].day;
        if (page.length < this.histLimit) h.done = true;
      } catch (e) {
        this._toast(false, e.message || 'Could not load history.');
      } finally {
        h.loading = false;
      }
    },

    loadMoreDays() {
      this.loadDays(false);
    },

    // Change the load size (days per page), remember it, reload the active tab from newest.
    setHistLimit(n) {
      this.histLimit = Number(n) || 30;
      localStorage.setItem('vf_hist_limit', this.histLimit);
      this.loadDays(true);
    },

    // Random access: jump to a month (YYYY-MM). Seeks the cursor to just after that month
    // and reloads, so the list starts at that month and "Load older" continues backward.
    jumpToMonth(val) {
      if (!val) return;
      const [y, m] = val.split('-').map(Number);
      const next = new Date(y, m, 1); // first day of the month AFTER the selected one
      const before = `${next.getFullYear()}-${String(next.getMonth() + 1).padStart(2, '0')}-01`;
      this.seekTo(before);
    },

    // Reset back to the most recent days (clears an active jump).
    jumpToLatest() {
      this.loadDays(true);
    },

    // Load days strictly before `before` (a YYYY-MM-DD cursor), replacing the current list.
    async seekTo(before) {
      const h = this.hist[this.historyTab];
      Object.assign(h, { days: [], expanded: {}, cursor: before, done: false, seeked: true });
      await this.loadDays(false); // uses the seeded cursor
    },

    // Expand/collapse a day; lazy-fetch its runs the first time it opens.
    async toggleDay(day) {
      const h = this.hist[this.historyTab];
      const cur = h.expanded[day] || { open: false, runs: null, loading: false };
      const open = !cur.open;
      h.expanded = { ...h.expanded, [day]: { ...cur, open } };
      if (open && cur.runs === null && !cur.loading) this.loadDayRuns(day);
    },

    async loadDayRuns(day) {
      const tab = this.historyTab;
      const h = this.hist[tab];
      h.expanded = { ...h.expanded, [day]: { ...(h.expanded[day] || { open: true }), loading: true } };
      try {
        const runs = await api.historyDayRuns(tab === 'scheduled', day);
        h.expanded = { ...h.expanded, [day]: { open: true, runs, loading: false } };
      } catch (e) {
        h.expanded = { ...h.expanded, [day]: { ...(h.expanded[day] || {}), loading: false } };
        this._toast(false, e.message || 'Could not load that day.');
      }
    },

    // Called when a sync finishes while the history view is open: refresh page-1 day summaries
    // and re-fetch any open day's runs so today's panel updates live.
    async refreshHistory() {
      const h = this.hist[this.historyTab];
      if (!h.started) return;
      const openDays = Object.keys(h.expanded).filter((d) => h.expanded[d].open);
      await this.loadDays(true);
      for (const d of openDays) {
        if (h.days.some((x) => x.day === d)) await this.loadDayRuns(d);
      }
    },

    // "Today" / "Yesterday" / "Mon, Jun 27" from a YYYY-MM-DD local date.
    dayLabel(day) {
      const d = new Date(`${day}T00:00:00`);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const diff = Math.round((today - d) / 86400000);
      if (diff === 0) return 'Today';
      if (diff === 1) return 'Yesterday';
      return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
    },
  };
}
