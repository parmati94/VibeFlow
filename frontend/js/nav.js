// Client-side view switching (no router needed). The active `view` drives which section
// renders; switching to a data-backed view refreshes its data.
export function nav() {
  return {
    view: 'home', // 'home' | 'sync' | 'scheduled' | 'history'
    navItems: [
      { id: 'home', label: 'Home' },
      { id: 'sync', label: 'Sync' },
      { id: 'scheduled', label: 'Schedules' },
      { id: 'history', label: 'History' },
    ],

    setView(v) {
      this.view = v;
      if (v === 'scheduled') {
        this.loadMappings();
        if (!this.playlists.length) this.loadPlaylists();
      }
      if (v === 'history') this.loadHistory();
      if (v === 'sync' && !this.playlists.length) this.loadPlaylists();
    },
  };
}
