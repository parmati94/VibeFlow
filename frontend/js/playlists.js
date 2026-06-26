import { api } from './api.js';

// Spotify playlist browsing + multi-select for sync.
export function playlists() {
  return {
    playlists: [],
    playlistsLoading: false,
    playlistError: null,
    selected: new Set(),
    filter: '',

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
