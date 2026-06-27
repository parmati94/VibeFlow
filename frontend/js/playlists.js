import { api } from './api.js';

// Spotify playlist browsing + multi-select for sync.
export function playlists() {
  return {
    playlists: [],
    playlistsLoading: false,
    playlistError: null,
    selected: new Set(),
    filter: '',

    // Sync-page sort (persisted on this device, like the theme picker).
    plSort: localStorage.getItem('vf-playlist-sort') || 'default',
    plSortOpts: [
      { value: 'default', label: 'Default order' },
      { value: 'name', label: 'Name (A–Z)' },
      { value: 'name_desc', label: 'Name (Z–A)' },
      { value: 'tracks', label: 'Tracks (most)' },
      { value: 'selected', label: 'Selected first' },
    ],
    setPlSort(v) {
      this.plSort = v;
      localStorage.setItem('vf-playlist-sort', v);
    },

    // Apply the chosen sort to an (already-filtered) list. Caller passes a copy.
    _sortPlaylists(list) {
      const byName = (a, b) =>
        (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' });
      switch (this.plSort) {
        case 'name':
          return list.sort(byName);
        case 'name_desc':
          return list.sort((a, b) => byName(b, a));
        case 'tracks':
          return list.sort((a, b) => (b.track_count || 0) - (a.track_count || 0));
        case 'selected':
          return list.sort((a, b) => (this.isSelected(b.id) - this.isSelected(a.id)) || byName(a, b));
        case 'default':
        default:
          return list;
      }
    },

    async loadPlaylists() {
      this.playlistsLoading = true;
      this.playlistError = null;
      try {
        this.playlists = await api.spotifyPlaylists();
      } catch (e) {
        this.playlistError = e.message;
      } finally {
        this.playlistsLoading = false;
      }
    },

    isSelected(id) {
      return this.selected.has(id);
    },

    toggleSelect(id) {
      // reassign so Alpine tracks the change
      const next = new Set(this.selected);
      next.has(id) ? next.delete(id) : next.add(id);
      this.selected = next;
    },

    selectAllVisible() {
      const next = new Set(this.selected);
      this.filteredPlaylists.forEach((p) => next.add(p.id));
      this.selected = next;
    },

    clearSelection() {
      this.selected = new Set();
    },
  };
}
