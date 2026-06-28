// Client-side view switching (no router needed). The active `view` drives which section
// renders; switching to a data-backed view refreshes its data.
export function nav() {
  return {
    view: 'home', // 'home' | 'sync' | 'scheduled' | 'history'
    mobileNav: false, // hamburger menu open state (mobile only)
    navItems: [
      { id: 'home', label: 'Home' },
      { id: 'sync', label: 'Sync' },
      { id: 'scheduled', label: 'Schedules' },
      { id: 'history', label: 'History' },
    ],

    setView(v) {
      this.view = v;
      this.mobileNav = false; // collapse the mobile menu after a selection
      if (v === 'scheduled') {
        this.loadMappings();
        if (!this.playlists.length) this.loadPlaylists();
      }
      if (v === 'history') this.openHistory();
      if (v === 'sync' && !this.playlists.length) this.loadPlaylists();
    },
  };
}
