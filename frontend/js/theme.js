// Accent theme + settings panel. Each theme id maps to a [data-theme] palette in main.css;
// applyTheme swaps it on <html> and persists the choice on this device.
const THEMES = [
  { id: 'vibe', label: 'Cyan', swatch: '#06b6d4' },
  { id: 'violet', label: 'Violet', swatch: '#8b5cf6' },
  { id: 'blue', label: 'Blue', swatch: '#3b82f6' },
  { id: 'emerald', label: 'Emerald', swatch: '#10b981' },
  { id: 'amber', label: 'Amber', swatch: '#f59e0b' },
  { id: 'rose', label: 'Rose', swatch: '#f43f5e' },
];

export function theme() {
  return {
    showSettings: false,
    theme: 'vibe',
    themes: THEMES,

    initTheme() {
      this.applyTheme(localStorage.getItem('vf-theme') || 'vibe');
    },

    applyTheme(id) {
      if (!THEMES.some((t) => t.id === id)) id = 'vibe';
      this.theme = id;
      document.documentElement.setAttribute('data-theme', id);
      localStorage.setItem('vf-theme', id);
    },
  };
}
