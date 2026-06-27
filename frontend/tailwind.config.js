/** @type {import('tailwindcss').Config} */
export default {
  content: ['./*.html', './partials/**/*.html', './js/**/*.js'],
  theme: {
    extend: {
      colors: {
        // accent-* resolve to CSS vars set in css/main.css (R G B triplets), so a single
        // data-theme swap on <html> recolors the whole UI.
        accent: {
          50: 'rgb(var(--accent-50) / <alpha-value>)',
          100: 'rgb(var(--accent-100) / <alpha-value>)',
          200: 'rgb(var(--accent-200) / <alpha-value>)',
          300: 'rgb(var(--accent-300) / <alpha-value>)',
          400: 'rgb(var(--accent-400) / <alpha-value>)',
          500: 'rgb(var(--accent-500) / <alpha-value>)',
          600: 'rgb(var(--accent-600) / <alpha-value>)',
          700: 'rgb(var(--accent-700) / <alpha-value>)',
          800: 'rgb(var(--accent-800) / <alpha-value>)',
          900: 'rgb(var(--accent-900) / <alpha-value>)',
        },
      },
    },
  },
  plugins: [],
};
