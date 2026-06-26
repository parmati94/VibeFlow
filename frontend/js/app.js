import Alpine from 'alpinejs';
import { connection } from './connection.js';

document.addEventListener('alpine:init', () => {
  Alpine.data('app', () => ({
    // Feature modules spread in so the markup sees one flat component. Add future modules
    // (auth, sync, mappings, history) here the same way.
    ...connection(),

    async init() {
      await this.loadConnection();
    },
  }));
});

window.Alpine = Alpine;
Alpine.start();
